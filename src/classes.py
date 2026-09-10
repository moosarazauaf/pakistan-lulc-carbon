"""GLC-FCS30D land-cover legend, aggregation, and carbon densities for Pakistan.

Why this file is not a copy of the Lahore project's config
---------------------------------------------------------
The Lahore work used four classes (Built-up / Vegetation / Water / Bare land)
because a single district of irrigated rice-wheat cropland genuinely has only
one vegetation type worth separating. Pakistan does not. It has closed
needle-leaved forest in the north, mangrove on the Indus delta, shrubland
across Balochistan and irrigated cropland in Punjab, and those differ in carbon
density by more than an order of magnitude.

Collapsing them into one "Vegetation" class and applying a single density is
exactly the error the Lahore README documents and corrects: the original Earth
Engine script gave Vegetation a closed-forest value of 150 Mg C/ha and thereby
overstated the 1993-2023 carbon loss by a factor of 5.9. Applying one number
nationally would repeat that error at national scale. So carbon is computed per
LCCS class here, and the four-class aggregate exists only for visual
comparability with the Lahore maps.

Year availability (verified against the live asset, not assumed)
---------------------------------------------------------------
GLC-FCS30D five-years-map has 3 bands: 1985, 1990, 1995.
GLC-FCS30D annual      has 23 bands: 2000 through 2022.
There is no 1993 and no 2023. The nearest epochs to the study design are
1995, 2003, 2013, 2022, and the app states that offset wherever it shows a
year label.
"""
from __future__ import annotations

# --------------------------------------------------------------- year mapping
FIVE_YEAR_BANDS = {1985: "b1", 1990: "b2", 1995: "b3"}
ANNUAL_BASE = 2000  # annual b1 == 2000
ANNUAL_LAST = 2022  # annual b23 == 2022

EPOCHS = [
    # requested, available, collection, band
    (1993, 1995, "five-years-map", "b3"),
    (2003, 2003, "annual", "b4"),
    (2013, 2013, "annual", "b14"),
    (2023, 2022, "annual", "b23"),
]
REQUESTED_YEARS = [e[0] for e in EPOCHS]
ACTUAL_YEARS = [e[1] for e in EPOCHS]
YEAR_OFFSET = {e[0]: e[1] - e[0] for e in EPOCHS}


def band_for(actual_year: int) -> tuple[str, str]:
    """Return (collection_name, band) for an available year."""
    if actual_year in FIVE_YEAR_BANDS:
        return "five-years-map", FIVE_YEAR_BANDS[actual_year]
    if ANNUAL_BASE <= actual_year <= ANNUAL_LAST:
        return "annual", "b%d" % (actual_year - ANNUAL_BASE + 1)
    raise ValueError("GLC-FCS30D has no map for %s" % actual_year)


def available_years() -> list[int]:
    """Every year the archive can render, for the free-roam map slider."""
    return sorted(FIVE_YEAR_BANDS) + list(range(ANNUAL_BASE, ANNUAL_LAST + 1))


# ---------------------------------------------------------------- product seam
# GLC-FCS30D is two production lines stitched together: five-yearly maps for
# 1985-1995 and annual maps from 2000. They are NOT continuous, and the
# discontinuity is large enough to invalidate any change figure that spans it.
#
# Measured on Lahore District at 30 m, built-up area by year:
#     1985  202 km2      1990  202 km2  (+0%, byte-identical)
#     1995  234 km2      2000  389 km2  (+66% in five years)
#     2001  425          2003  451      (+9%, +7%)
#     2013  551          2022  587      (+8%, +6%)
#
# The annual series grows smoothly at 6-9% per interval. The 66% step lands
# exactly on the seam, and 1985 equalling 1990 exactly shows the five-yearly
# half does not resolve change at all. So a 1995 -> 2022 comparison books a
# product artefact as land conversion.
#
# The app still offers the 1993-mapped epoch, because that is the study design,
# but it labels every seam-spanning comparison and offers 2000 as a seam-free
# alternative baseline.
SEAM_YEAR = ANNUAL_BASE  # first year of the annual production line
SEAM_FREE_BASELINE = 2000

# Years cached beyond the four study epochs, to support the seam-free option.
SUPPLEMENTARY_YEARS = [2000]


def spans_seam(year_from: int, year_to: int) -> bool:
    """True if a comparison crosses the five-yearly / annual production boundary."""
    return min(year_from, year_to) < SEAM_YEAR <= max(year_from, year_to)


def cache_years() -> list[int]:
    return sorted(set(ACTUAL_YEARS) | set(SUPPLEMENTARY_YEARS))


def cache_pairs() -> list[tuple[int, int]]:
    """Consecutive epoch pairs, the full span, and the seam-free span."""
    ys = ACTUAL_YEARS
    pairs = list(zip(ys[:-1], ys[1:])) + [(ys[0], ys[-1])]
    pairs.append((SEAM_FREE_BASELINE, ys[-1]))
    return list(dict.fromkeys(pairs))


# ------------------------------------------------------------------ LCCS legend
# Codes that carry no land-cover information. 250 is the product's documented
# fill value; 0 is undocumented but appears along the Indus delta coastline,
# where it totals about 5 km2 nationally (0.001% of the extent). Both are
# excluded from areas and percentages rather than silently counted as bare
# ground, and the excluded fraction is reported in the UI.
NODATA_CODES = frozenset({0, 250})

LCCS = {
    0: "No data (outside product)",
    10: "Rainfed cropland",
    11: "Herbaceous cover cropland",
    12: "Tree/shrub cover cropland",
    20: "Irrigated cropland",
    51: "Open evergreen broadleaved forest",
    52: "Closed evergreen broadleaved forest",
    61: "Open deciduous broadleaved forest",
    62: "Closed deciduous broadleaved forest",
    71: "Open evergreen needleleaved forest",
    72: "Closed evergreen needleleaved forest",
    81: "Open deciduous needleleaved forest",
    82: "Closed deciduous needleleaved forest",
    91: "Open mixed-leaf forest",
    92: "Closed mixed-leaf forest",
    120: "Shrubland",
    121: "Evergreen shrubland",
    122: "Deciduous shrubland",
    130: "Grassland",
    140: "Lichens and mosses",
    150: "Sparse vegetation",
    152: "Sparse shrubland",
    153: "Sparse herbaceous",
    181: "Swamp",
    182: "Marsh",
    183: "Flooded flat",
    184: "Saline wetland",
    185: "Mangrove",
    186: "Salt marsh",
    187: "Tidal flat",
    190: "Impervious surface (built-up)",
    200: "Bare areas",
    201: "Consolidated bare areas",
    202: "Unconsolidated bare areas",
    210: "Water body",
    220: "Permanent ice and snow",
    250: "Filled / no data",
}

# Rendering colours, roughly following the published GLC-FCS30D style so a
# reader who knows the product recognises the map.
LCCS_COLOURS = {
    0: "#c8c8c8",
    10: "#ffff64", 11: "#ffff9a", 12: "#d2cc64", 20: "#aaf0f0",
    51: "#4c7300", 52: "#006400", 61: "#a8c800", 62: "#00a000",
    71: "#005000", 72: "#003c00", 81: "#286400", 82: "#285000",
    91: "#a0b432", 92: "#788200", 120: "#966400", 121: "#964b00",
    122: "#966400", 130: "#ffb432", 140: "#ffdcd2", 150: "#ffebaf",
    152: "#ffd278", 153: "#ffebaf", 181: "#00a884", 182: "#00ccaa",
    183: "#00cf75", 184: "#bbdcff", 185: "#009678", 186: "#00dc82",
    187: "#00ffa0", 190: "#c31400", 200: "#fff5d7", 201: "#dcdcdc",
    202: "#fff5d7", 210: "#0046c8", 220: "#ffffff", 250: "#c8c8c8",
}

# -------------------------------- four-class aggregate (Lahore-comparable view)
BUILTUP, VEGETATION, WATER, BARE = 0, 1, 2, 3
AGG_NAMES = {BUILTUP: "Built-up", VEGETATION: "Vegetation",
             WATER: "Water", BARE: "Bare / sparse"}
AGG_COLOURS = {BUILTUP: "#c0392b", VEGETATION: "#27ae60",
               WATER: "#2874a6", BARE: "#d4ac0d"}

_WATER_CODES = {210, 220, 181, 182, 183, 186, 187}
_BARE_CODES = {200, 201, 202, 150, 152, 153, 140, 184}

AGGREGATE = {}
for _c in LCCS:
    if _c == 190:
        AGGREGATE[_c] = BUILTUP
    elif _c in _WATER_CODES:
        AGGREGATE[_c] = WATER
    elif _c in _BARE_CODES:
        AGGREGATE[_c] = BARE
    else:
        AGGREGATE[_c] = VEGETATION

# Finer thematic grouping, used for the carbon breakdown charts where
# "Vegetation" is far too coarse to be informative.
GROUPS = {
    "Cropland": [10, 11, 12, 20],
    "Forest": [51, 52, 61, 62, 71, 72, 81, 82, 91, 92],
    "Shrubland": [120, 121, 122],
    "Grassland": [130],
    "Sparse / lichen": [140, 150, 152, 153],
    "Wetland / mangrove": [181, 182, 183, 184, 185, 186, 187],
    "Built-up": [190],
    "Bare": [200, 201, 202],
    "Water": [210],
    "Ice and snow": [220],
    "No data": [0, 250],
}
GROUP_OF = {c: g for g, codes in GROUPS.items() for c in codes}
GROUP_COLOURS = {
    "Cropland": "#c9d95b", "Forest": "#1d7a3e", "Shrubland": "#9c6b2f",
    "Grassland": "#e0b03c", "Sparse / lichen": "#e6d8a8",
    "Wetland / mangrove": "#12a882", "Built-up": "#c0392b",
    "Bare": "#d9cba3", "Water": "#2874a6", "Ice and snow": "#e8f2f7",
    "No data": "#bbbbbb",
}

# --------------------------------------------------------------- carbon density
# Mg C/ha per IPCC pool, as (low, best, high) so every reported figure carries an
# uncertainty band instead of a single false-precision number.
#
# PROVENANCE / ACTION REQUIRED
# ---------------------------
# These are Tier 1 order-of-magnitude defaults, chosen per class to be
# defensible for Pakistan's climate zones. They are NOT transcribed from a
# specific IPCC table and MUST be checked against IPCC 2006 Vol.4 (Ch.4 Forest
# Land, Ch.5 Cropland, Ch.6 Grassland, Ch.8 Settlements) and against Pakistani
# literature before any thesis or manuscript use. The app states this in the UI
# rather than hiding it in a source comment.
#
# The cropland values are inherited directly from the Lahore correction: annual
# irrigated cropland is harvested every year and stores very little standing
# biomass, so it must never carry a forest above-ground value.


def _pools(above, below, soil, dead):
    return {"above": above, "below": below, "soil": soil, "dead": dead}


CARBON_POOLS = {
    # --- cropland: Lahore-corrected values, low standing biomass
    10:  _pools((2.0, 4.0, 8.0), (0.7, 1.4, 2.8), (25.0, 35.0, 48.0), (0.4, 1.0, 2.0)),
    11:  _pools((1.5, 3.0, 6.0), (0.5, 1.0, 2.0), (24.0, 33.0, 45.0), (0.3, 0.8, 1.6)),
    12:  _pools((8.0, 16.0, 28.0), (2.5, 5.0, 9.0), (30.0, 42.0, 58.0), (1.0, 2.5, 5.0)),
    20:  _pools((3.0, 6.0, 14.0), (1.0, 2.0, 4.0), (30.0, 42.0, 55.0), (0.5, 1.5, 3.0)),
    # --- forest: open canopy (fc 0.15-0.4) carries roughly 40% of closed biomass
    51:  _pools((30.0, 55.0, 85.0), (8.0, 14.0, 22.0), (45.0, 65.0, 90.0), (2.0, 5.0, 9.0)),
    52:  _pools((70.0, 120.0, 180.0), (18.0, 30.0, 47.0), (55.0, 80.0, 110.0), (4.0, 9.0, 16.0)),
    61:  _pools((25.0, 45.0, 70.0), (7.0, 12.0, 18.0), (40.0, 58.0, 80.0), (2.0, 4.5, 8.0)),
    62:  _pools((55.0, 95.0, 145.0), (14.0, 25.0, 38.0), (50.0, 72.0, 100.0), (3.5, 8.0, 14.0)),
    71:  _pools((28.0, 50.0, 78.0), (7.0, 13.0, 20.0), (55.0, 80.0, 110.0), (2.5, 6.0, 11.0)),
    72:  _pools((65.0, 110.0, 165.0), (17.0, 29.0, 43.0), (70.0, 100.0, 140.0), (5.0, 11.0, 20.0)),
    81:  _pools((25.0, 45.0, 70.0), (6.0, 12.0, 18.0), (50.0, 72.0, 100.0), (2.0, 5.0, 9.0)),
    82:  _pools((55.0, 95.0, 145.0), (14.0, 25.0, 38.0), (60.0, 88.0, 120.0), (4.0, 9.0, 16.0)),
    91:  _pools((27.0, 48.0, 75.0), (7.0, 13.0, 19.0), (48.0, 68.0, 95.0), (2.0, 5.0, 9.0)),
    92:  _pools((60.0, 105.0, 160.0), (15.0, 27.0, 41.0), (58.0, 84.0, 115.0), (4.0, 9.5, 17.0)),
    # --- shrub / grass
    120: _pools((6.0, 12.0, 22.0), (2.5, 5.0, 9.0), (25.0, 38.0, 55.0), (0.5, 1.5, 3.0)),
    121: _pools((7.0, 14.0, 25.0), (3.0, 6.0, 10.0), (26.0, 40.0, 57.0), (0.5, 1.5, 3.0)),
    122: _pools((5.0, 10.0, 19.0), (2.0, 4.0, 8.0), (24.0, 36.0, 52.0), (0.5, 1.4, 2.8)),
    130: _pools((1.5, 3.5, 7.0), (2.0, 4.5, 9.0), (28.0, 42.0, 60.0), (0.2, 0.8, 1.8)),
    140: _pools((0.2, 0.6, 1.5), (0.1, 0.3, 0.8), (10.0, 20.0, 35.0), (0.0, 0.2, 0.6)),
    150: _pools((0.5, 1.5, 3.5), (0.3, 0.8, 1.8), (10.0, 17.0, 27.0), (0.0, 0.3, 0.8)),
    152: _pools((1.0, 2.5, 5.0), (0.5, 1.2, 2.5), (12.0, 19.0, 30.0), (0.1, 0.4, 1.0)),
    153: _pools((0.4, 1.2, 3.0), (0.4, 1.0, 2.2), (11.0, 18.0, 28.0), (0.0, 0.3, 0.8)),
    # --- wetland: high soil carbon, mangrove highest of all
    181: _pools((10.0, 22.0, 40.0), (4.0, 9.0, 16.0), (80.0, 130.0, 200.0), (1.0, 3.0, 6.0)),
    182: _pools((3.0, 8.0, 16.0), (2.0, 5.0, 10.0), (70.0, 115.0, 180.0), (0.5, 2.0, 4.0)),
    183: _pools((1.0, 3.0, 7.0), (0.5, 1.5, 3.5), (30.0, 50.0, 80.0), (0.2, 0.8, 2.0)),
    184: _pools((0.3, 1.0, 2.5), (0.2, 0.6, 1.5), (12.0, 22.0, 38.0), (0.0, 0.3, 0.8)),
    185: _pools((45.0, 80.0, 130.0), (25.0, 45.0, 75.0), (150.0, 250.0, 400.0), (2.0, 6.0, 12.0)),
    186: _pools((2.0, 6.0, 12.0), (2.0, 5.0, 10.0), (60.0, 100.0, 160.0), (0.3, 1.2, 3.0)),
    187: _pools((0.2, 0.8, 2.0), (0.1, 0.4, 1.0), (15.0, 28.0, 48.0), (0.0, 0.2, 0.6)),
    # --- built-up: Lahore-corrected. Street/garden trees over largely sealed soil.
    190: _pools((2.0, 5.0, 9.0), (0.5, 1.5, 3.0), (10.0, 18.0, 30.0), (0.0, 0.5, 1.5)),
    # --- bare / water / ice
    200: _pools((0.1, 0.4, 1.2), (0.05, 0.2, 0.6), (5.0, 10.0, 18.0), (0.0, 0.1, 0.4)),
    201: _pools((0.0, 0.2, 0.7), (0.0, 0.1, 0.4), (3.0, 7.0, 13.0), (0.0, 0.05, 0.2)),
    202: _pools((0.1, 0.5, 1.5), (0.05, 0.3, 0.8), (6.0, 12.0, 20.0), (0.0, 0.1, 0.5)),
    210: _pools((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (2.0, 5.0, 10.0), (0.0, 0.0, 0.0)),
    220: _pools((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    250: _pools((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    0:   _pools((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
}

POOL_NAMES = ("above", "below", "soil", "dead")
POOL_LABELS = {"above": "Above-ground biomass", "below": "Below-ground biomass",
               "soil": "Soil organic carbon", "dead": "Dead organic matter"}

# Conversion used whenever a carbon stock is expressed as CO2-equivalent.
CO2_PER_C = 44.0 / 12.0


def total_density(code: int) -> tuple[float, float, float]:
    """Total (low, best, high) Mg C/ha for one LCCS class, summed over pools."""
    p = CARBON_POOLS[code]
    return tuple(sum(p[pool][i] for pool in POOL_NAMES) for i in range(3))


# The single-value table the original Earth Engine script used, kept so the
# thesis can quantify exactly how large the correction is rather than assert it.
LEGACY_TOTAL_CARBON = {BUILTUP: 28.0, VEGETATION: 150.0, WATER: 5.0, BARE: 18.0}
