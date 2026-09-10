"""Build the offline cache the app reads: per-district areas and transitions.

Why per district, at native 30 m
--------------------------------
A single national reduceRegion at 30 m is ~877 million pixels and will not
return inside Earth Engine's interactive limits. Reducing at 300 m does return,
but a scale check against native resolution showed it shifts the built-up share
by +3.4 percentage points in Islamabad and -1.0 in Punjab. Built-up is the class
the entire carbon-loss result hinges on, so that bias is not acceptable.

Splitting by district makes each request small enough to succeed at 30 m, and
running the districts concurrently brings a full national epoch down to about
five minutes. Provinces and the national total are then sums of districts, which
is exact. District granularity also gives the app its drill-down for free.

The cache is written incrementally and the script is resumable: rerunning it
skips whatever is already present, so a dropped connection costs one district
rather than the whole build.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import ee  # noqa: E402

import classes as C  # noqa: E402
import gee  # noqa: E402

CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)
AREAS = CACHE / "areas.json"
TRANS = CACHE / "transitions.json"
META = CACHE / "meta.json"

scale_notes: dict[str, int] = {}

WORKERS = 12
SCALE = 30


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            print(f"  ! {path.name} was corrupt, starting it over")
    return {}


def _save(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj))
    tmp.replace(path)


# Escalation ladder, tried in order until one returns.
#
# tileScale must stay within Earth Engine's documented 0.1-16 range; going above
# it raises "Valid tileScales are 0.1 to 16" on every attempt, which silently
# cost the whole of Thatta District on the first build. A higher tileScale trades
# speed for memory headroom, so the ladder exhausts tileScale at native
# resolution before it gives up any resolution. The scale that actually
# succeeded is recorded, so a district accounted more coarsely is visible in the
# cache rather than hidden.
RETRY_LADDER = [(30, 16), (30, 8), (30, 4), (60, 16), (100, 16)]


def _with_retry(fn, label):
    """Try progressively cheaper reductions; return (result, scale_used)."""
    last = ""
    for scale, tile in RETRY_LADDER:
        try:
            return fn(scale, tile), scale
        except Exception as e:
            last = str(e).split("\n")[0][:110]
            time.sleep(1.5)
    print(f"  FAILED {label}: {last}")
    return None, None


def build_meta() -> dict:
    """Enumerate the accounting units: clipped districts plus AJK and GB.

    Azad Kashmir and Gilgit-Baltistan have no ADM2 children in geoBoundaries, so
    they are carried as whole-territory units. Their geometry areas are recorded
    post-clipping, so the reconciliation test compares against the geometry the
    reduction actually used rather than the unclipped one.
    """
    meta = _load(META)
    if meta.get("districts"):
        return meta
    print("Fetching unit list, province mapping and clipped areas...")

    a1 = gee.pakistan()
    id2name = dict(zip(a1.aggregate_array("shapeID").getInfo(),
                       a1.aggregate_array("shapeName").getInfo()))
    rows = gee.districts().reduceColumns(
        ee.Reducer.toList(2), ["shapeName", "ADM1_shape"]).getInfo()["list"]

    names = [r[0] for r in rows]
    province_of = {r[0]: id2name.get(r[1], "Unknown") for r in rows}
    for special in gee.NO_DISTRICTS:
        names.append(special)
        province_of[special] = special

    print(f"  {len(names)} units across "
          f"{len(set(province_of.values()))} ADM1 territories")
    print("  measuring clipped geometry areas...")

    def area_of(name):
        try:
            return name, gee.unit_geometry(name).area(maxError=2000).getInfo() / 1e6
        except Exception as e:  # noqa: BLE001
            print(f"  ! area failed for {name}: {str(e).splitlines()[0][:80]}")
            return name, None

    geom_km2 = {}
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for name, km2 in ex.map(area_of, names):
            if km2 is not None:
                geom_km2[name] = km2

    meta = {
        "districts": names,
        "province_of": province_of,
        "geom_km2": geom_km2,
        "scale_m": SCALE,
        "epochs": C.EPOCHS,
        "source": "GLC-FCS30D via projects/sat-io/open-datasets",
        "boundary": ("geoBoundaries CGAZ ADM1/ADM2, shapeGroup == PAK. Districts "
                     "are intersected with the non-AJK/GB mainland so units tile "
                     "without double-counting."),
        "includes": ("Azad Kashmir and Gilgit-Baltistan, administered by Pakistan "
                     "and disputed with India, carried as whole territories "
                     "because geoBoundaries gives them no ADM2 children"),
    }
    _save(META, meta)
    print(f"  total unit area {sum(geom_km2.values()):,.0f} km2")
    return meta


def build_areas(names: list[str]) -> dict:
    store = _load(AREAS)
    years = C.cache_years()
    todo = [(n, y) for n in names for y in years
            if str(y) not in store.get(n, {})]
    if not todo:
        print("Areas: already complete")
        return store
    print(f"Areas: {len(todo)} district-years to fetch at {SCALE} m")

    def one(job):
        name, year = job
        geom = gee.unit_geometry(name)
        res, used = _with_retry(
            lambda sc, ts: gee.class_areas_ha(year, geom, scale=sc, tile_scale=ts),
            f"areas {name} {year}")
        return name, year, res, used

    done = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for name, year, res, used in ex.map(one, todo):
            done += 1
            if res is not None:
                store.setdefault(name, {})[str(year)] = {str(k): v for k, v in res.items()}
                if used != SCALE:
                    scale_notes[f"areas {name} {year}"] = used
                    print(f"  note: {name} {year} accounted at {used} m, not {SCALE} m")
            if done % 20 == 0 or done == len(todo):
                _save(AREAS, store)
                el = time.time() - t0
                print(f"  {done}/{len(todo)}  {el/60:.1f} min elapsed, "
                      f"~{el/done*(len(todo)-done)/60:.1f} min left")
    _save(AREAS, store)
    return store


def build_transitions(names: list[str]) -> dict:
    store = _load(TRANS)
    pairs = C.cache_pairs()
    todo = [(n, a, b) for n in names for a, b in pairs
            if f"{a}_{b}" not in store.get(n, {})]
    if not todo:
        print("Transitions: already complete")
        return store
    print(f"Transitions: {len(todo)} district-pairs to fetch at {SCALE} m")

    def one(job):
        name, a, b = job
        geom = gee.unit_geometry(name)
        res, used = _with_retry(
            lambda sc, ts: gee.transition_areas_ha(a, b, geom, scale=sc, tile_scale=ts),
            f"trans {name} {a}->{b}")
        return name, a, b, res, used

    done = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for name, a, b, res, used in ex.map(one, todo):
            done += 1
            if res is not None:
                store.setdefault(name, {})[f"{a}_{b}"] = {
                    f"{f}_{t}": v for (f, t), v in res.items()}
                if used != SCALE:
                    scale_notes[f"trans {name} {a}_{b}"] = used
                    print(f"  note: {name} {a}->{b} accounted at {used} m, not {SCALE} m")
            if done % 20 == 0 or done == len(todo):
                _save(TRANS, store)
                el = time.time() - t0
                print(f"  {done}/{len(todo)}  {el/60:.1f} min elapsed, "
                      f"~{el/done*(len(todo)-done)/60:.1f} min left")
    _save(TRANS, store)
    return store


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    gee.init()
    print("Earth Engine ready\n")
    meta = build_meta()
    names = meta["districts"]

    t0 = time.time()
    areas = build_areas(names)
    build_transitions(names)

    if scale_notes:
        meta["coarser_than_native"] = scale_notes
        _save(META, meta)
        print(f"\n{len(scale_notes)} entries needed a coarser scale than "
              f"{SCALE} m; recorded in meta.json so the app can show it")
    print(f"\nDone in {(time.time()-t0)/60:.1f} min")

    # A sanity line, so a bad build is obvious immediately rather than in the app.
    for y in C.cache_years():
        tot = sum(v for n in names for v in areas.get(n, {}).get(str(y), {}).values())
        got = sum(1 for n in names if str(y) in areas.get(n, {}))
        print(f"  {y}: {got}/{len(names)} districts, {tot/100:,.0f} km2")


if __name__ == "__main__":
    main()
