# Pakistan LULC and Carbon, 1993-2023

An interactive analysis of thirty years of land-cover change across Pakistan at
30 m, and the terrestrial carbon that change implies. Built from GLC-FCS30D
through Google Earth Engine, accounted district by district at native
resolution, and presented so that every headline number can be traced back to
the multiplication that produced it.

This is the national counterpart to the Lahore District CA-Markov and carbon
projection work in `../lahore-lulc-carbon`, and it inherits that project's two
methodological corrections.

## What it does

- **Map.** Live Earth Engine tiles for any year the archive holds (1985, 1990,
  1995, then every year 2000-2022), in the full 36-class LCCS legend or a
  four-class aggregate that lines up with the Lahore maps.
- **Change and carbon.** Built-up and vegetation area change, carbon stock,
  gross loss, gross gain and net flux, with the specific figure for carbon
  released by vegetated land converting to built-up.
- **Full record.** Area and carbon trajectories across the four epochs, with
  the uncertainty band drawn rather than footnoted, and a per-pool breakdown.
- **Show the arithmetic.** The Earth Engine reduction, the density table, the
  area-times-density sum, the from-to flux formula with real values, and a
  measurement of how far the uncorrected carbon table would have been out.
- **Districts.** All 133 accounting units (131 districts plus Azad Kashmir
  and Gilgit-Baltistan as whole territories) ranked by built-up expansion and
  carbon loss, with CSV export.
- **Method and limits.** Every caveat that could mislead a reader, stated up
  front.

## Six things to know before reading any number

**1. The 1995 and 2000 maps are not continuous, and the gap is large.**
GLC-FCS30D stitches two production lines together: five-yearly maps to 1995,
annual maps from 2000. Measured on Lahore District, built-up area jumps **+66%
between 1995 and 2000** against a smooth 6-9% per interval through the annual
years, and the 1985 and 1990 maps are identical to the pixel. Nationally, a
1995-2022 comparison reports **+223%** built-up growth against **+23%** for
seam-free 2000-2022, so roughly three quarters of the apparent growth is a
product artefact. The app defaults to the seam-free comparison and labels every
seam-crossing one. Full detail in [`docs/RESULTS.md`](docs/RESULTS.md).

**2. The national net carbon change is not distinguishable from zero.**
Seam-free, the net is +52.5 Tg C against a band of −471 to +580. The band is
ten times the point estimate and spans zero. The limiting factor is the carbon
densities, not the land-cover map. The app states this wherever it applies
rather than printing a confident number beside a range.

**3. The years are not exactly 1993 and 2023.** GLC-FCS30D, the only 30 m
land-cover archive reaching back that far, has five-yearly maps for 1985, 1990
and 1995, then annual maps for 2000-2022. There is no 1993 map and no 2023 map.
The epochs actually used are **1995, 2003, 2013, 2022**; two land exactly and
the endpoints shift by +2 and -1 years. The 1993 endpoint is the weak one,
since a 1995 map misses two years of early-1990s change.

**4. The extent includes Azad Kashmir and Gilgit-Baltistan.** The boundary is
**geoBoundaries CGAZ** (`shapeGroup == PAK`): 865,243 km², 8 territories, 133
accounting units. Both Pakistan-administered territories are included and shown
as separate regions rather than folded silently into the national total; their
sovereignty is disputed with India.

This replaced FAO GAUL, which cannot support the analysis at all: GAUL files
both territories under a separate `Jammu and Kashmir` ADM0 whose sub-units are
every one of them named *"Administrative unit not available"*. GAUL also still
carries pre-2018 'North-West Frontier' naming.

They are not a rounding difference. Gilgit-Baltistan is **22% permanent ice and
snow** and Azad Kashmir is **67% closed forest** — the densest carbon in the
country. Two caveats: geoBoundaries gives neither territory ADM2 children, so
each is one whole unit with no district drill-down; and its district layer does
not nest inside its own ADM1 layer, overshooting by ~5,800 km² and overlapping
the territories by 585 km², so districts are intersected with the mainland
before accounting. That leaves a 0.16% sliver gap, preferred to double-counting.

**5. The permanent-ice class is snow, not glaciers.** Including
Gilgit-Baltistan brought GLC-FCS30D class 220 into the national picture. It
reads 16,105 km² in 2000, 19,875 in 2013 and 16,912 in 2022 — a 14% swing in
nine years, which permanent ice cannot do. It is interannual snowpack and scene
timing, and it accounts for about 5% of gross carbon loss over 2000-2022.
Nothing here is a glacier measurement.

**6. Carbon densities are Tier 1 placeholders.** Per-class, four IPCC pools,
low/best/high on every value, and **not** transcribed from a specific IPCC
table. They must be checked against IPCC 2006 Volume 4 and Pakistani literature
before any thesis or manuscript use. The app says so on screen.

## Two corrections inherited from the Lahore work

**Carbon density is per class, not per aggregate.** The original Earth Engine
script gave the whole Vegetation class 150 Mg C/ha, a closed-forest value, which
overstated Lahore's carbon loss by a factor of 5.9. Pakistan spans closed
needle-leaved forest, Indus delta mangrove, Balochistan shrubland and Punjab
irrigated cropland, which differ in carbon density by more than an order of
magnitude, so one national number would repeat that error at national scale.
The app computes carbon per LCCS class and reports the measured size of the
correction rather than asserting it.

**Change is a from-to crosstab, not a subtraction.** `lc_2022 - lc_1995` is not
interpretable, because class codes are nominal labels rather than quantities: a
difference of 2 could be built-up becoming water or cropland becoming bare land,
and the two render identically.

## Accounting scale, and why it is 30 m

A single national reduction at 30 m is about 877 million pixels per epoch and
will not return inside Earth Engine's interactive limits. Reducing at 300 m does
return, but a scale check against native resolution measured the built-up share
shifting **+3.4 percentage points** in Islamabad and **-1.0** in Punjab.
Built-up is the class the whole carbon result depends on, so that bias was not
acceptable. Splitting by district keeps every request small enough to run at
30 m, and running districts concurrently brings a national epoch down to about
five minutes. Provinces and the national total are sums of districts, which is
exact.

Any district that still needed a coarser scale is recorded in
`cache/meta.json` under `coarser_than_native` and surfaced in the app, rather
than being hidden.

## What this is not

- **Not a deep-learning product.** With four epochs, a temporal neural network
  would be fitting noise. The machine learning here is the Random Forest inside
  GLC-FCS30D itself and the Random Forest transition potential in the companion
  Lahore projection.
- **Not an independently validated classification.** GLC-FCS30D's own reported
  accuracy is roughly 80% globally for level-1 classes and lower for the fine
  legend. Classification error propagates into the transition matrix as
  fictitious change, and that is the dominant uncertainty in every change figure
  here, larger than the carbon band.
- **Not a carbon inventory.** It is an area-times-density estimate, with no
  field measurements, no soil sampling and no biomass plots.

## Layout

```
app.py                    Streamlit shell, sidebar, tab routing
src/classes.py            LCCS legend, aggregation, carbon densities, year mapping
src/gee.py                Earth Engine auth, mosaic, area and transition reducers
src/analysis.py           All arithmetic. Reads cache/, never touches Earth Engine
src/charts.py             Plotly figures and the folium map
src/views.py              Tab renderers
scripts/build_cache.py    One-off national cache build (~60 min)
scripts/probe_*.py        Dataset and boundary probes used to verify assumptions
cache/                    areas.json, transitions.json, meta.json
```

All arithmetic lives in `src/analysis.py` and runs off `cache/*.json`, so the
whole result set is reproducible offline and Earth Engine is needed only for map
tiles. The app degrades to a numbers-only mode if Earth Engine is unavailable.

## Running it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
# put a GEE service-account key at service_account.json
.venv/Scripts/python scripts/build_cache.py     # once, ~60 min
.venv/Scripts/python -m streamlit run app.py
```

The cache build is resumable: rerunning it skips whatever is already present.

See [`docs/RESULTS.md`](docs/RESULTS.md) for the findings and what they will
and will not support, and [`docs/DEPLOY.md`](docs/DEPLOY.md) for Hugging Face
Spaces deployment.
