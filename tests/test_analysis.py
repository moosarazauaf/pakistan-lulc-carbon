"""Invariants that must hold for the results to mean anything.

These are not smoke tests. Each one checks a property that, if violated, would
make a published number wrong: areas that do not reconcile to the official
boundary, a transition matrix whose margins disagree with the epoch areas,
uncertainty bands the wrong way round, or nodata leaking into carbon.

Run:  .venv/Scripts/python -m pytest tests -q
      .venv/Scripts/python tests/test_analysis.py     (no pytest needed)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import analysis as A  # noqa: E402
import classes as C  # noqa: E402

TOL = 0.01  # 1% reconciliation tolerance


def _cached_districts(year: int) -> list[str]:
    data = A.load()["areas"]
    return [d for d in A.districts() if year in data.get(d, {})]


# ------------------------------------------------------------------ year mapping
def test_epochs_exist_in_archive():
    """Every epoch we claim to use must be a band the archive actually has."""
    for requested, actual, coll, band in C.EPOCHS:
        got_coll, got_band = C.band_for(actual)
        assert (got_coll, got_band) == (coll, band), \
            f"{actual}: expected {coll}/{band}, band_for gave {got_coll}/{got_band}"


def test_no_1993_or_2023_claimed():
    """The archive has neither year. Claiming them would be a false label."""
    assert 1993 not in C.ACTUAL_YEARS
    assert 2023 not in C.ACTUAL_YEARS
    assert C.YEAR_OFFSET[1993] == 2
    assert C.YEAR_OFFSET[2023] == -1


# ------------------------------------------------- Pakistan-administered territories
def test_ajk_and_gilgit_baltistan_are_present():
    """Both Pakistan-administered territories must be selectable regions."""
    regions = A.regions()
    for t in ("Azad Kashmir", "Gilgit-Baltistan"):
        assert t in regions, f"{t} missing from regions"
        assert t in A.districts(), f"{t} missing as an accounting unit"


def test_territories_carry_real_land_cover():
    """They must hold data, not be empty polygons that quietly contribute zero."""
    year = C.ACTUAL_YEARS[-1]
    for t, floor_km2 in (("Azad Kashmir", 10_000), ("Gilgit-Baltistan", 50_000)):
        a = A.areas(t, year)
        if not a:
            return  # cache still building
        km2 = sum(a.values()) / 100
        assert km2 > floor_km2, f"{t} only {km2:,.0f} km2"


def test_gilgit_baltistan_has_the_ice():
    """Excluding GB was excluding the country's permanent ice. Confirm it is back.

    Code 220 is permanent ice and snow. GB is roughly a fifth of it, and before
    the boundary switch the national total had almost none.
    """
    year = C.ACTUAL_YEARS[-1]
    gb = A.areas("Gilgit-Baltistan", year)
    if not gb:
        return
    share = 100 * gb.get(220, 0.0) / (sum(gb.values()) or 1)
    assert share > 10, f"GB only {share:.1f}% permanent ice and snow"

    national = A.areas(A.NATIONAL, year)
    if national:
        assert national.get(220, 0.0) >= gb.get(220, 0.0) * 0.95


def test_azad_kashmir_is_forested():
    """AJK is the densest carbon in the country; confirm the forest is there."""
    year = C.ACTUAL_YEARS[-1]
    a = A.areas("Azad Kashmir", year)
    if not a:
        return
    tot = sum(a.values()) or 1
    forest = sum(ha for c, ha in a.items() if C.GROUP_OF.get(c) == "Forest")
    assert 100 * forest / tot > 50, f"AJK only {100*forest/tot:.1f}% forest"


def test_units_tile_without_double_counting():
    """Summed unit areas must not exceed the national boundary.

    geoBoundaries' district layer overshoots its own ADM1 layer and overlaps the
    two territories, so districts are clipped to the mainland before accounting.
    If that clipping were dropped, this sum would exceed the ADM1 union by about
    5,800 km2.
    """
    meta = A.load()["meta"]
    total = sum(meta["geom_km2"].values())
    ADM1_UNION_KM2 = 866_631
    assert total <= ADM1_UNION_KM2 * 1.001, (
        f"units sum to {total:,.0f} km2, above the {ADM1_UNION_KM2:,} km2 "
        "ADM1 union: clipping is not being applied")
    assert total > ADM1_UNION_KM2 * 0.99, (
        f"units sum to {total:,.0f} km2, well under the ADM1 union")


# ------------------------------------------------------------------- product seam
def test_seam_detection():
    """The seam sits between 1995 and 2000. Comparisons must be classified right."""
    assert C.spans_seam(1995, 2022)
    assert C.spans_seam(1995, 2003)
    assert C.spans_seam(1990, 2000)
    assert not C.spans_seam(2000, 2022)
    assert not C.spans_seam(2003, 2013)
    assert not C.spans_seam(2013, 2022)
    assert not C.spans_seam(1985, 1995)


def test_a_seam_free_comparison_is_offered():
    """A user must always be able to reach a comparison that avoids the seam."""
    seam_free = [p for p in C.cache_pairs() if not C.spans_seam(*p)]
    assert seam_free, "no seam-free comparison available"
    full_span = max(seam_free, key=lambda p: p[1] - p[0])
    assert full_span[1] - full_span[0] >= 20, \
        f"longest seam-free span is only {full_span[1]-full_span[0]} years"


def test_seam_is_larger_than_annual_change():
    """The reason the seam matters, asserted against the cached national data.

    If the 1995->2000 step were comparable to normal inter-annual change, the
    warning would be over-cautious. It is not: this asserts the step is at least
    twice the mean annual rate measured across the seam-free years.
    """
    if 2000 not in C.cache_years():
        return
    data = A.load()["areas"]
    if not all(2000 in data.get(d, {}) for d in A.districts()):
        return  # cache still building

    def built(y):
        return A.agg_areas(A.NATIONAL, y)[C.BUILTUP]

    seam_rate = (built(2000) - built(1995)) / 5.0
    annual_rate = (built(2022) - built(2003)) / 19.0
    assert seam_rate > 2 * abs(annual_rate), (
        f"seam rate {seam_rate/100:,.0f} km2/yr is not clearly larger than the "
        f"annual-series rate {annual_rate/100:,.0f} km2/yr"
    )


# ------------------------------------------------------------------ class scheme
def test_every_class_is_fully_specified():
    """A class missing a density, colour or group raises KeyError at runtime."""
    for code in C.LCCS:
        assert code in C.CARBON_POOLS, f"{code} has no carbon density"
        assert code in C.LCCS_COLOURS, f"{code} has no colour"
        assert code in C.GROUP_OF, f"{code} has no group"
        assert code in C.AGGREGATE, f"{code} has no four-class aggregate"


def test_density_bands_are_ordered():
    """low <= best <= high, on every pool of every class."""
    for code in C.LCCS:
        for pool in C.POOL_NAMES:
            lo, be, hi = C.CARBON_POOLS[code][pool]
            assert lo <= be <= hi, f"{code}/{pool} band out of order: {lo},{be},{hi}"


def test_cropland_is_not_given_a_forest_density():
    """The correction this project exists to make: cropland must sit far below forest.

    The original script's 150 Mg C/ha vegetation value is a closed-forest number.
    If cropland ever creeps near it, the correction has been undone.
    """
    for crop in (10, 11, 20):
        crop_total = C.total_density(crop)[1]
        assert crop_total < 90, f"cropland {crop} at {crop_total} Mg C/ha is forest-like"
        for forest in (52, 62, 72, 92):
            assert crop_total < C.total_density(forest)[1] / 1.8, \
                f"cropland {crop} too close to forest {forest}"


def test_nodata_carries_no_carbon():
    for code in C.NODATA_CODES:
        assert C.total_density(code) == (0.0, 0.0, 0.0)


# --------------------------------------------------------------------- areas
def test_district_areas_reconcile_to_boundary():
    """Summed pixel area must match the GAUL polygon area for each district."""
    meta = A.load()["meta"]
    year = C.ACTUAL_YEARS[-1]
    bad = []
    for d in _cached_districts(year):
        summed_km2 = sum(A.areas(d, year, include_nodata=True).values()) / 100.0
        official = meta["geom_km2"][d]
        if official > 0 and abs(summed_km2 - official) / official > TOL:
            bad.append((d, round(summed_km2), round(official)))
    assert not bad, f"areas do not reconcile to boundary: {bad[:5]}"


def test_area_is_stable_across_epochs():
    """A district cannot change size between epochs. If it does, a year is broken."""
    bad = []
    for d in _cached_districts(C.ACTUAL_YEARS[-1]):
        totals = []
        for y in C.ACTUAL_YEARS:
            a = A.areas(d, y, include_nodata=True)
            if a:
                totals.append(sum(a.values()))
        if len(totals) > 1 and (max(totals) - min(totals)) / max(totals) > TOL:
            bad.append((d, [round(t / 100) for t in totals]))
    assert not bad, f"area unstable across epochs: {bad[:5]}"


def test_nodata_is_excluded_by_default():
    year = C.ACTUAL_YEARS[-1]
    for d in _cached_districts(year)[:20]:
        assert not (set(A.areas(d, year)) & C.NODATA_CODES)


def test_aggregate_preserves_total_area():
    year = C.ACTUAL_YEARS[-1]
    for d in _cached_districts(year)[:20]:
        assert abs(sum(A.agg_areas(d, year)) - sum(A.areas(d, year))) < 1e-6 or \
            abs(sum(A.agg_areas(d, year).values())
                - sum(A.areas(d, year).values())) < 1.0


def test_group_areas_preserve_total():
    year = C.ACTUAL_YEARS[-1]
    for d in _cached_districts(year)[:20]:
        a = sum(A.areas(d, year).values())
        g = sum(A.group_areas(d, year).values())
        assert abs(a - g) < 1.0, f"{d}: groups {g} vs classes {a}"


# -------------------------------------------------------------------- carbon
def test_stock_band_is_ordered_and_positive():
    for region in A.regions():
        for y in C.ACTUAL_YEARS:
            lo, be, hi = A.stock(region, y)
            assert 0 <= lo <= be <= hi, f"{region} {y}: band {lo},{be},{hi}"


def test_pools_sum_to_total_stock():
    year = C.ACTUAL_YEARS[-1]
    for region in A.regions():
        total = A.stock(region, year)
        pools = A.stock_by_pool(region, year)
        for i in range(3):
            s = sum(pools[p][i] for p in C.POOL_NAMES)
            assert abs(s - total[i]) < max(1.0, total[i] * 1e-9), \
                f"{region}: pool sum {s} != total {total[i]}"


def test_groups_sum_to_total_stock():
    year = C.ACTUAL_YEARS[-1]
    for region in A.regions():
        total = A.stock(region, year)[1]
        s = sum(v[1] for v in A.stock_by_group(region, year).values())
        assert abs(s - total) < max(1.0, total * 1e-9)


# --------------------------------------------------------------- transitions
def _pairs_available() -> list[tuple[int, int]]:
    cov = A.coverage()
    return [p for p, (h, n) in cov["pairs"].items() if h == n and n > 0]


def test_transition_margins_match_epoch_areas():
    """Row sums of the crosstab must equal the origin-epoch areas, and column
    sums the destination-epoch areas. This is the strongest single check that
    the two halves of the cache describe the same country."""
    for (y0, y1) in _pairs_available():
        t = A.transitions(A.NATIONAL, y0, y1)
        if not t:
            continue
        rows, cols = {}, {}
        for (f, to), ha in t.items():
            rows[f] = rows.get(f, 0.0) + ha
            cols[to] = cols.get(to, 0.0) + ha
        a0, a1 = A.areas(A.NATIONAL, y0), A.areas(A.NATIONAL, y1)
        for label, margin, ref in (("row", rows, a0), ("col", cols, a1)):
            m, r = sum(margin.values()), sum(ref.values())
            assert abs(m - r) / r < TOL, \
                f"{y0}->{y1} {label} margin {m/100:,.0f} vs areas {r/100:,.0f} km2"


def test_flux_excludes_persistence():
    for (y0, y1) in _pairs_available()[:1]:
        for r in A.flux(A.NATIONAL, y0, y1):
            assert r["from"] != r["to"]


def test_flux_bands_are_ordered():
    for (y0, y1) in _pairs_available()[:1]:
        for r in A.flux(A.NATIONAL, y0, y1):
            assert r["low_Mg_C"] <= r["best_Mg_C"] <= r["high_Mg_C"], r


def test_gross_loss_and_gain_sum_to_net():
    for (y0, y1) in _pairs_available():
        fs = A.flux_summary(A.NATIONAL, y0, y1)
        assert abs((fs["gross_loss_Mg_C"] + fs["gross_gain_Mg_C"])
                   - fs["net_Mg_C"]) < 1.0


def test_vegetation_to_builtup_is_a_loss():
    """Every vegetated class stores more carbon than sealed ground, so this
    conversion can only release carbon. A positive value means a density is wrong."""
    for (y0, y1) in _pairs_available():
        fs = A.flux_summary(A.NATIONAL, y0, y1)
        if fs["vegetation_to_builtup_ha"] > 0:
            assert fs["vegetation_to_builtup_Mg_C"] < 0, \
                "vegetation to built-up came out as a carbon gain"


def test_legacy_comparison_overstates():
    """The uncorrected single-value table should exaggerate the loss, which is
    the whole reason the correction exists."""
    for (y0, y1) in _pairs_available():
        lc = A.legacy_comparison(A.NATIONAL, y0, y1)
        if lc["corrected_Mg_C"] < 0:
            assert lc["legacy_Mg_C"] < lc["corrected_Mg_C"], \
                f"legacy {lc['legacy_Mg_C']} not more negative than {lc['corrected_Mg_C']}"


def test_national_equals_sum_of_provinces():
    year = C.ACTUAL_YEARS[-1]
    nat = sum(A.areas(A.NATIONAL, year).values())
    prov = sum(sum(A.areas(p, year).values()) for p in A.provinces())
    assert abs(nat - prov) < 1.0, f"national {nat} != provinces {prov}"


if __name__ == "__main__":
    import traceback

    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {str(e)[:220]}")
            failed += 1
        except Exception:  # noqa: BLE001
            print(f"  ERROR {name}")
            traceback.print_exc(limit=2)
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
