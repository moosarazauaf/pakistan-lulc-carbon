"""Pakistan LULC and Carbon, 1993-2023: interactive analysis.

Run locally:   streamlit run app.py
Deploy:        Hugging Face Spaces, SDK = streamlit (see docs/DEPLOY.md)

Architecture
------------
All arithmetic lives in src/analysis.py and operates on cache/*.json, which was
built once from Earth Engine at native 30 m. The app therefore starts instantly
and every number is reproducible offline. Earth Engine is contacted only to
render map tiles, and the app degrades to a numbers-only mode if that fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import analysis as A  # noqa: E402
import classes as C  # noqa: E402
import views  # noqa: E402

st.set_page_config(page_title="Pakistan LULC and Carbon 1993-2023",
                   page_icon="🌍", layout="wide",
                   initial_sidebar_state="expanded")

CSS = """
<style>
  .block-container {padding-top: 2.2rem; padding-bottom: 3rem;}
  [data-testid="stMetricValue"] {font-size: 1.55rem;}
  [data-testid="stMetricLabel"] {opacity: .78;}
  h3 {margin-top: .4rem;}
  .lead {font-size: 1.02rem; opacity: .85; max-width: 70ch; line-height: 1.55;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def earth_engine_status() -> tuple[bool, str]:
    """Return (ready, reason). The reason has to come back as a value.

    An earlier version stashed the failure in st.session_state from inside this
    cached function. That loses it: the cache means the body runs once for the
    whole server, while session_state is per visitor, so every later session saw
    an empty reason and the banner said only that Earth Engine was unavailable.
    A deployment failing for a missing secret and one failing for a rejected key
    looked identical, which is useless when the logs are not to hand.
    """
    try:
        import gee
        gee.init()
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:400]}"


def method_tab() -> None:
    st.subheader("Method, data and limits")
    st.markdown(
        '<p class="lead">Everything on this page that could mislead a reader is '
        'stated here rather than buried. The first two are material enough to '
        'change how the headline numbers should be read.</p>',
        unsafe_allow_html=True)

    st.markdown("### The 1995 and 2000 maps are not continuous")
    st.markdown(
        "GLC-FCS30D stitches two production lines together: five-yearly maps "
        "for 1985-1995 and annual maps from 2000 onward. They do not join "
        "smoothly. Measured on Lahore District at 30 m:"
    )
    st.table({
        "Year": ["1985", "1990", "1995", "2000", "2001", "2003", "2013", "2022"],
        "Source": ["five-yearly"] * 3 + ["annual"] * 5,
        "Built-up km2": [202, 202, 234, 389, 425, 451, 551, 587],
        "Change": ["-", "+0%", "+16%", "+66%", "+9%", "+7%", "+8%", "+6%"],
    })
    st.markdown(
        "The annual series grows steadily at 6 to 9 percent per interval. The "
        "66 percent step falls exactly on the seam, and the 1985 and 1990 maps "
        "are identical pixel for pixel, which shows the five-yearly half does "
        "not resolve change at all. **Any comparison spanning 1995 to 2000 "
        "books that seam as land conversion.** The app labels every such "
        "comparison and offers 2000 as a seam-free baseline, which is the "
        "default. The cost is losing the first seven years of the study period."
    )

    st.markdown("### The years are not exactly 1993 and 2023")
    st.markdown(
        "The study design asks for 1993, 2003, 2013 and 2023. GLC-FCS30D, the "
        "only 30 m land-cover archive reaching back that far, holds five-yearly "
        "maps for 1985, 1990 and 1995, then annual maps for 2000 to 2022. "
        "**There is no 1993 map and no 2023 map.** The nearest available epochs "
        "are used, and the offset is shown next to every year label in the app."
    )
    st.table({
        "Requested": [str(y) for y in C.REQUESTED_YEARS],
        "Actually used": [str(y) for y in C.ACTUAL_YEARS],
        "Offset (years)": [f"{C.YEAR_OFFSET[y]:+d}" for y in C.REQUESTED_YEARS],
    })
    st.caption(
        "The 1993 endpoint is the weak one. A 1995 map misses two years of the "
        "early-1990s change, so growth over the full period is slightly "
        "understated relative to a true 1993 baseline."
    )

    st.markdown("### The extent includes Azad Kashmir and Gilgit-Baltistan")
    st.markdown(
        "The boundary is **geoBoundaries CGAZ** (`shapeGroup == PAK`): "
        "**865,243 km² across 8 territories and 133 accounting units.** That "
        "includes Azad Kashmir and Gilgit-Baltistan, which are administered by "
        "Pakistan and whose sovereignty is disputed with India. They are shown "
        "as separate territories in the region selector rather than folded "
        "silently into the national total."
    )
    st.markdown(
        "This replaced FAO GAUL, which could not support the analysis: GAUL "
        "files both territories under a separate `Jammu and Kashmir` ADM0 whose "
        "sub-units are every one of them literally named *\"Administrative unit "
        "not available\"*, so neither can be selected from it. GAUL also still "
        "carries the pre-2018 'North-West Frontier' naming."
    )
    st.markdown(
        "The two territories are not a rounding difference. Gilgit-Baltistan is "
        "**22% permanent ice and snow** and Azad Kashmir is **67% closed "
        "forest**, the densest carbon in the country, so excluding them "
        "distorted both the land-cover mix and the carbon stock."
    )
    st.caption(
        "Two accounting caveats. geoBoundaries gives neither territory any ADM2 "
        "children, so each is carried as one whole unit with no district "
        "drill-down. And its district layer does not nest cleanly inside its own "
        "ADM1 layer, overshooting by about 5,800 km² and overlapping the two "
        "territories by 585 km², so every district is intersected with the "
        "mainland before accounting. That leaves a 0.16% sliver gap against the "
        "ADM1 union, which is preferred to double-counting. geoBoundaries also "
        "still lists FATA separately from Khyber Pakhtunkhwa despite the 2018 "
        "merger."
    )

    st.markdown("### The permanent-ice class is snow cover, not glaciers")
    st.markdown(
        "Including Gilgit-Baltistan brought GLC-FCS30D class 220 into the "
        "national picture, and it needs a health warning. It records what the "
        "imagery saw as snow or ice on the day it was classified, not glacier "
        "extent."
    )
    st.table({
        "Year": ["1995", "2000", "2003", "2013", "2022"],
        "Ice and snow km2": ["16,506", "16,105", "17,683", "19,875", "16,912"],
    })
    st.markdown(
        "A **14% swing in nine years** is not something permanent ice can do; it "
        "is interannual snowpack and scene timing. This matters for carbon "
        "because grassland scored as turning to ice registers as a total loss of "
        "that grassland's carbon, and the reverse as a gain. Nationally that is "
        "about **5% of gross loss** over 2000-2022. The app states the figure "
        "with and without it on the change tab. **Nothing here should be read as "
        "a glacier measurement**, in either direction."
    )

    st.markdown("### Carbon densities are Tier 1 placeholders")
    st.markdown(
        "Densities are order-of-magnitude defaults, per class, with a low / best "
        "/ high band on every value. They are **not** transcribed from a specific "
        "IPCC table and must be checked against IPCC 2006 Volume 4 and Pakistani "
        "literature before thesis or manuscript use. The band is carried through "
        "every calculation, so no figure in this app is presented as a single "
        "precise number."
    )

    st.markdown("### What this is not")
    st.markdown(
        "- **Not a deep-learning product.** With four epochs, a temporal neural "
        "network would be fitting noise. The method is a from-to crosstab over a "
        "published 30 m classification, with per-class carbon accounting. The "
        "machine learning that exists is the Random Forest inside GLC-FCS30D "
        "itself, and the Random Forest transition potential in the companion "
        "Lahore projection work.\n"
        "- **Not an independently validated classification.** GLC-FCS30D's own "
        "reported accuracy is roughly 80% globally for its level-1 classes and "
        "lower for the fine legend. Classification error propagates into the "
        "transition matrix as fictitious change, which is the dominant "
        "uncertainty in every change figure here, larger than the carbon band.\n"
        "- **Not a carbon inventory.** It is an area-times-density estimate. It "
        "has no field measurements, no soil sampling and no biomass plots."
    )

    st.markdown("### Provenance")
    try:
        meta = A.load()["meta"]
        cov = A.coverage()
        st.json({
            "land cover": "GLC-FCS30D, 30 m, projects/sat-io/open-datasets",
            "boundaries": meta.get("boundary"),
            "includes": meta.get("includes"),
            "accounting scale": f"{meta.get('scale_m')} m (native)",
            "accounting units cached": cov["n_districts"],
            "coverage per epoch": {str(y): f"{h}/{n} districts"
                                   for y, (h, n) in cov["years"].items()},
            "excluded": meta.get("excludes"),
        })
    except Exception as e:  # noqa: BLE001
        st.warning(f"Cache metadata unavailable: {e}")


def main() -> None:
    try:
        A.load()
    except FileNotFoundError as e:
        st.title("Pakistan LULC and Carbon, 1993-2023")
        st.error(str(e))
        st.stop()

    cov = A.coverage()
    incomplete = [y for y, (h, n) in cov["years"].items() if h < n]
    incomplete += [f"{a}-{b}" for (a, b), (h, n) in cov["pairs"].items() if h < n]

    st.title("Pakistan land cover and carbon, 1993-2023")
    st.markdown(
        '<p class="lead">Thirty years of land-cover change across Pakistan at '
        '30 m, and the terrestrial carbon that change implies. Built from '
        'GLC-FCS30D through Google Earth Engine, accounted district by district '
        'at native resolution. Every number is reproducible and every step of '
        'the calculation is shown.</p>',
        unsafe_allow_html=True)

    if incomplete:
        st.warning(
            "Cache is still building: epochs "
            + ", ".join(str(y) for y in incomplete)
            + ". Figures shown are partial until it finishes."
        )

    # ------------------------------------------------------------- sidebar
    with st.sidebar:
        st.header("Controls")
        region = st.selectbox("Region", A.regions(), index=0)
        if region != A.NATIONAL:
            kids = A.districts(region)
            # Azad Kashmir and Gilgit-Baltistan have no districts in
            # geoBoundaries, so each is its own only member. Offering a
            # one-item "district" list there would just repeat the territory.
            if kids == [region]:
                st.caption(
                    f"{region} is Pakistan-administered and disputed with India. "
                    "geoBoundaries gives it no districts, so it is accounted as "
                    "one whole territory."
                )
            elif kids:
                pick = st.selectbox("District", ["(whole territory)"] + kids, index=0)
                if pick != "(whole territory)":
                    region = pick

        st.divider()
        # Only offer comparisons the cache actually holds, so no selection can
        # produce an empty transition matrix.
        requested_of = dict(zip(C.ACTUAL_YEARS, C.REQUESTED_YEARS))

        def _label(pair: tuple[int, int]) -> str:
            a, b = pair
            ra, rb = requested_of.get(a, a), requested_of.get(b, b)
            base = f"{ra} to {rb}"
            maps = f" (maps {a}-{b})" if (ra, rb) != (a, b) else ""
            if C.spans_seam(a, b):
                return f"{base}{maps} — crosses seam"
            if a == C.SEAM_FREE_BASELINE:
                return f"{base}{maps} — seam-free"
            return f"{base}{maps}"

        pairs = [p for p in C.cache_pairs()
                 if cov["pairs"].get(p, (0, 1))[0] > 0]
        if not pairs:
            pairs = C.cache_pairs()
        default = next((i for i, p in enumerate(pairs)
                        if p[0] == C.SEAM_FREE_BASELINE), len(pairs) - 1)
        y0, y1 = pairs[st.selectbox("Comparison", range(len(pairs)),
                                    format_func=lambda i: _label(pairs[i]),
                                    index=default)]
        if C.spans_seam(y0, y1):
            st.caption("⚠ This comparison crosses the 1995/2000 product seam.")

        st.divider()
        st.caption("Map")
        map_year = st.select_slider("Map year", C.available_years(),
                                    value=C.ACTUAL_YEARS[-1])
        map_mode = st.radio("Map classes",
                            ["Full LCCS legend", "Four-class aggregate"], index=0)

        st.divider()
        st.caption(
            f"Region area {sum(A.agg_areas(region, C.ACTUAL_YEARS[-1]).values())/100:,.0f} km² · "
            f"accounted at 30 m · GLC-FCS30D"
        )

    ee_ok, ee_reason = earth_engine_status()
    if not ee_ok:
        st.info(
            "Running from cache only — Earth Engine is unavailable, so the map "
            "tab is disabled. Every other figure is unaffected."
        )
        with st.expander("Why is Earth Engine unavailable?"):
            st.code(ee_reason or "no reason captured", language="text")
            st.markdown(
                "**No credentials found** means the `GEE_SERVICE_ACCOUNT` secret "
                "is missing or is not valid JSON. On Streamlit Community Cloud "
                "set it under *Settings → Secrets* as a triple-quoted TOML "
                "string holding the whole service-account file.\n\n"
                "**An `EEException` or a permission error** means the secret "
                "arrived but Earth Engine rejected it: the service account is "
                "not registered for Earth Engine, or its Cloud project does not "
                "have the Earth Engine API enabled."
            )

    tabs = st.tabs(["Map", "Change and carbon", "Full record",
                    "Show the arithmetic", "Districts", "Method and limits"])
    with tabs[0]:
        views.render_map(region, map_year, map_mode, ee_ok)
    with tabs[1]:
        views.render_change(region, y0, y1)
    with tabs[2]:
        views.render_trajectory(region)
    with tabs[3]:
        views.render_arithmetic(region, y0, y1)
    with tabs[4]:
        views.render_districts(y0, y1)
    with tabs[5]:
        method_tab()


if __name__ == "__main__":
    main()
