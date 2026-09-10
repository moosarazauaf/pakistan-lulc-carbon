"""Turn the cached district tables into areas, carbon stocks and carbon flux.

No Earth Engine here. Every number the app reports comes out of this module
operating on cache/*.json, which means the whole result set can be recomputed,
diffed and unit-tested offline. The map tiles are the only part of the app that
needs a live Earth Engine connection.

Carbon convention
-----------------
A stock is Mg C held in a region at one epoch. A flux is the difference in stock
attributable to a specific from-to conversion, computed as

    area_converted_ha * (density_of_destination - density_of_origin)

so a cropland-to-built-up conversion yields a negative number (a loss) and a
bare-to-cropland conversion yields a positive one. Losses and gains are reported
separately as well as netted, because a net figure alone hides the fact that
Pakistan is doing both at once.

The low/best/high band is carried through every calculation rather than being
attached at the end. For a flux the band is deliberately widened by pairing the
low destination density against the high origin density, because the two
densities are independent estimates and the loss is largest when the origin was
carbon-rich and the destination is carbon-poor.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import classes as C

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

NATIONAL = "Pakistan"


# ------------------------------------------------------------------- cache I/O
@lru_cache(maxsize=1)
def load() -> dict:
    """Read the cache once. Raises with a useful message if it is not built."""
    missing = [p.name for p in (CACHE / "meta.json", CACHE / "areas.json")
               if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Cache not built: missing " + ", ".join(missing)
            + ". Run  python scripts/build_cache.py  first."
        )
    meta = json.loads((CACHE / "meta.json").read_text())
    areas = json.loads((CACHE / "areas.json").read_text())

    # Transitions are the second half of the build. Treat them as optional so a
    # partially built cache still renders areas and stocks, with the UI saying
    # so, instead of failing outright.
    tpath = CACHE / "transitions.json"
    trans = json.loads(tpath.read_text()) if tpath.exists() else {}

    # Normalise the string keys the JSON round-trip forces on us.
    areas_n = {
        d: {int(y): {int(c): v for c, v in cy.items()} for y, cy in years.items()}
        for d, years in areas.items()
    }
    trans_n = {}
    for d, pairs in trans.items():
        trans_n[d] = {}
        for pair, cells in pairs.items():
            a, b = (int(x) for x in pair.split("_"))
            trans_n[d][(a, b)] = {
                tuple(int(x) for x in k.split("_")): v for k, v in cells.items()
            }
    return {"meta": meta, "areas": areas_n, "trans": trans_n}


def provinces() -> list[str]:
    m = load()["meta"]["province_of"]
    return sorted(set(m.values()))


def districts(province: str | None = None) -> list[str]:
    m = load()["meta"]["province_of"]
    if province is None:
        return sorted(m)
    return sorted(d for d, p in m.items() if p == province)


def regions() -> list[str]:
    """Every selectable region, national first."""
    return [NATIONAL] + provinces()


def _members(region: str) -> list[str]:
    """Which districts make up a region."""
    pmap = load()["meta"]["province_of"]
    if region == NATIONAL:
        return list(pmap)
    if region in set(pmap.values()):
        return [d for d, p in pmap.items() if p == region]
    if region in pmap:
        return [region]
    raise KeyError(f"Unknown region: {region!r}")


def coverage(region: str = NATIONAL) -> dict:
    """How complete the cache is for a region, so the UI never implies false totals."""
    data = load()
    names = _members(region)
    per_year = {}
    for y in C.cache_years():
        have = [n for n in names if y in data["areas"].get(n, {})]
        per_year[y] = (len(have), len(names))

    per_pair = {}
    for p in C.cache_pairs():
        have = [n for n in names if p in data["trans"].get(n, {})]
        per_pair[p] = (len(have), len(names))

    return {"years": per_year, "pairs": per_pair, "n_districts": len(names)}


# --------------------------------------------------------------------- areas
def areas(region: str, actual_year: int, include_nodata: bool = False) -> dict[int, float]:
    """LCCS class -> hectares, summed over the districts of a region.

    Nodata codes are dropped by default. They are a coastal edge artefact
    totalling about 5 km2 nationally, and leaving them in would both break the
    carbon lookup and quietly dilute every percentage. Use nodata_ha() to report
    how much was excluded.
    """
    data = load()["areas"]
    out: dict[int, float] = {}
    for name in _members(region):
        for code, ha in data.get(name, {}).get(actual_year, {}).items():
            if not include_nodata and code in C.NODATA_CODES:
                continue
            out[code] = out.get(code, 0.0) + ha
    return out


def nodata_ha(region: str, actual_year: int) -> float:
    """Hectares excluded as nodata, so the omission is visible rather than silent."""
    data = load()["areas"]
    return sum(ha
               for name in _members(region)
               for code, ha in data.get(name, {}).get(actual_year, {}).items()
               if code in C.NODATA_CODES)


def agg_areas(region: str, actual_year: int) -> dict[int, float]:
    """Four-class aggregate areas, for comparability with the Lahore maps."""
    out = {k: 0.0 for k in C.AGG_NAMES}
    for code, ha in areas(region, actual_year).items():
        out[C.AGGREGATE.get(code, C.BARE)] += ha
    return out


def group_areas(region: str, actual_year: int) -> dict[str, float]:
    out = {g: 0.0 for g in C.GROUPS}
    for code, ha in areas(region, actual_year).items():
        out[C.GROUP_OF.get(code, "No data")] += ha
    return out


# --------------------------------------------------------------------- carbon
def stock(region: str, actual_year: int) -> tuple[float, float, float]:
    """Total (low, best, high) Mg C stored in a region at one epoch."""
    lo = be = hi = 0.0
    for code, ha in areas(region, actual_year).items():
        d = C.total_density(code)
        lo += ha * d[0]
        be += ha * d[1]
        hi += ha * d[2]
    return lo, be, hi


def stock_by_pool(region: str, actual_year: int) -> dict[str, tuple[float, float, float]]:
    out = {p: [0.0, 0.0, 0.0] for p in C.POOL_NAMES}
    for code, ha in areas(region, actual_year).items():
        pools = C.CARBON_POOLS[code]
        for p in C.POOL_NAMES:
            for i in range(3):
                out[p][i] += ha * pools[p][i]
    return {p: tuple(v) for p, v in out.items()}


def stock_by_group(region: str, actual_year: int) -> dict[str, tuple[float, float, float]]:
    out = {g: [0.0, 0.0, 0.0] for g in C.GROUPS}
    for code, ha in areas(region, actual_year).items():
        g = C.GROUP_OF.get(code, "No data")
        d = C.total_density(code)
        for i in range(3):
            out[g][i] += ha * d[i]
    return {g: tuple(v) for g, v in out.items()}


# ----------------------------------------------------------------- transitions
def transitions(region: str, year_from: int, year_to: int) -> dict[tuple[int, int], float]:
    data = load()["trans"]
    key = (year_from, year_to)
    out: dict[tuple[int, int], float] = {}
    for name in _members(region):
        for cell, ha in data.get(name, {}).get(key, {}).items():
            # A cell touching nodata at either end is not a real conversion.
            # Counting it would invent carbon flux out of a coastline artefact.
            if cell[0] in C.NODATA_CODES or cell[1] in C.NODATA_CODES:
                continue
            out[cell] = out.get(cell, 0.0) + ha
    return out


def agg_transitions(region: str, year_from: int, year_to: int) -> dict[tuple[int, int], float]:
    out: dict[tuple[int, int], float] = {}
    for (f, t), ha in transitions(region, year_from, year_to).items():
        k = (C.AGGREGATE.get(f, C.BARE), C.AGGREGATE.get(t, C.BARE))
        out[k] = out.get(k, 0.0) + ha
    return out


def flux(region: str, year_from: int, year_to: int) -> list[dict]:
    """Per-conversion carbon change, largest loss first.

    Persistence cells (from == to) are dropped: they contribute no flux by
    construction and would otherwise dominate the table, since most of Pakistan
    does not change class in a decade.
    """
    rows = []
    for (f, t), ha in transitions(region, year_from, year_to).items():
        if f == t or ha <= 0:
            continue
        df, dt = C.total_density(f), C.total_density(t)
        rows.append({
            "from": f,
            "to": t,
            "from_name": C.LCCS.get(f, str(f)),
            "to_name": C.LCCS.get(t, str(t)),
            "from_group": C.GROUP_OF.get(f, "No data"),
            "to_group": C.GROUP_OF.get(t, "No data"),
            "area_ha": ha,
            # Widest defensible band: worst case pairs a carbon-rich origin
            # against a carbon-poor destination.
            "low_Mg_C": ha * (dt[0] - df[2]),
            "best_Mg_C": ha * (dt[1] - df[1]),
            "high_Mg_C": ha * (dt[2] - df[0]),
        })
    rows.sort(key=lambda r: r["best_Mg_C"])
    return rows


def flux_summary(region: str, year_from: int, year_to: int) -> dict:
    """Gross loss, gross gain and net, plus the specific answer the user asked for."""
    rows = flux(region, year_from, year_to)
    loss = sum(r["best_Mg_C"] for r in rows if r["best_Mg_C"] < 0)
    gain = sum(r["best_Mg_C"] for r in rows if r["best_Mg_C"] > 0)
    lo = sum(r["low_Mg_C"] for r in rows)
    hi = sum(r["high_Mg_C"] for r in rows)

    veg_groups = {"Cropland", "Forest", "Shrubland", "Grassland",
                  "Wetland / mangrove"}
    to_builtup = [r for r in rows if r["to"] == 190 and r["from_group"] in veg_groups]
    veg_lost = [r for r in rows
                if r["from_group"] in veg_groups and r["to_group"] not in veg_groups]

    return {
        "rows": rows,
        "gross_loss_Mg_C": loss,
        "gross_gain_Mg_C": gain,
        "net_Mg_C": loss + gain,
        "net_low_Mg_C": lo,
        "net_high_Mg_C": hi,
        "net_CO2e_Mg": (loss + gain) * C.CO2_PER_C,
        # "carbon lost to built-up expansion", the headline question
        "vegetation_to_builtup_ha": sum(r["area_ha"] for r in to_builtup),
        "vegetation_to_builtup_Mg_C": sum(r["best_Mg_C"] for r in to_builtup),
        "vegetation_to_builtup_low_Mg_C": sum(r["low_Mg_C"] for r in to_builtup),
        "vegetation_to_builtup_high_Mg_C": sum(r["high_Mg_C"] for r in to_builtup),
        # all vegetation loss, not only that which became built-up
        "vegetation_lost_ha": sum(r["area_ha"] for r in veg_lost),
        "vegetation_lost_Mg_C": sum(r["best_Mg_C"] for r in veg_lost),
    }


ICE = 220


def snow_flux(region: str, year_from: int, year_to: int) -> dict:
    """How much of the flux comes from the permanent-ice class changing.

    Including Gilgit-Baltistan brought this class into the national picture, and
    it needs a health warning. GLC-FCS30D class 220 is what the imagery saw as
    snow or ice at classification time, not glacier extent. Nationally it reads
    16,105 km2 in 2000, 19,875 in 2013 and 16,912 in 2022 - a 14% swing in nine
    years, which permanent ice cannot physically do. It is interannual snow
    cover.

    That matters for carbon because grassland turning to "ice" is scored as a
    total loss of the grassland's carbon, and the reverse as a gain. Those are
    artefacts of when the scene was imaged. This reports their size so the
    reader can subtract them.
    """
    rows = flux(region, year_from, year_to)
    ice_rows = [r for r in rows if ICE in (r["from"], r["to"])]
    gross_loss = sum(r["best_Mg_C"] for r in rows if r["best_Mg_C"] < 0)
    ice_loss = sum(r["best_Mg_C"] for r in ice_rows if r["best_Mg_C"] < 0)
    ice_net = sum(r["best_Mg_C"] for r in ice_rows)
    net = sum(r["best_Mg_C"] for r in rows)
    return {
        "ice_net_Mg_C": ice_net,
        "net_excluding_ice_Mg_C": net - ice_net,
        "ice_area_ha": sum(r["area_ha"] for r in ice_rows),
        "share_of_gross_loss": (ice_loss / gross_loss) if gross_loss else 0.0,
    }


# ------------------------------------------------- the correction, quantified
def legacy_comparison(region: str, year_from: int, year_to: int) -> dict:
    """What the original single-value carbon table would have reported.

    The Lahore project found that giving the whole Vegetation class a
    closed-forest 150 Mg C/ha overstated the district's 1993-2023 carbon loss by
    a factor of 5.9. This recomputes the same national result both ways so the
    size of the correction is a measured number rather than an assertion.
    """
    corrected = flux_summary(region, year_from, year_to)["net_Mg_C"]

    legacy = 0.0
    for (f, t), ha in transitions(region, year_from, year_to).items():
        if f == t:
            continue
        af, at = C.AGGREGATE.get(f, C.BARE), C.AGGREGATE.get(t, C.BARE)
        legacy += ha * (C.LEGACY_TOTAL_CARBON[at] - C.LEGACY_TOTAL_CARBON[af])

    ratio = (legacy / corrected) if corrected else float("nan")
    return {"legacy_Mg_C": legacy, "corrected_Mg_C": corrected, "ratio": ratio}


# ------------------------------------------------------------------ district view
def district_table(year_from: int, year_to: int) -> list[dict]:
    """Per-district built-up gain and carbon flux, for ranking and choropleth."""
    data = load()
    pmap = data["meta"]["province_of"]
    rows = []
    for name in districts():
        a0 = agg_areas(name, year_from)
        a1 = agg_areas(name, year_to)
        if not any(a0.values()) or not any(a1.values()):
            continue
        fs = flux_summary(name, year_from, year_to)
        total = sum(a1.values()) or 1.0
        rows.append({
            "district": name,
            "province": pmap.get(name, ""),
            "area_ha": total,
            "builtup_from_ha": a0[C.BUILTUP],
            "builtup_to_ha": a1[C.BUILTUP],
            "builtup_gain_ha": a1[C.BUILTUP] - a0[C.BUILTUP],
            "builtup_pct_to": 100 * a1[C.BUILTUP] / total,
            "veg_from_ha": a0[C.VEGETATION],
            "veg_to_ha": a1[C.VEGETATION],
            "veg_change_ha": a1[C.VEGETATION] - a0[C.VEGETATION],
            "net_Mg_C": fs["net_Mg_C"],
            "net_Mg_C_per_ha": fs["net_Mg_C"] / total,
        })
    return rows
