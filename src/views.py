"""The app's tabs. Each one renders numbers that analysis.py already computed.

The design rule throughout: no figure appears without the reader being able to
reach the arithmetic behind it. That is what the "Show the arithmetic" tab is
for, and why several panels carry an expander with the actual multiplication
rather than a citation to one.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import analysis as A
import charts
import classes as C

TG = 1e6  # Mg -> Tg


def _tg(x: float) -> str:
    return f"{x / TG:,.2f}"


def _fmt_signed(x: float, unit: str = "Tg C") -> str:
    return f"{x / TG:+,.2f} {unit}"


def sign_note(low: float, high: float, what: str) -> None:
    """Say so when an uncertainty band straddles zero.

    A point estimate printed next to a band that crosses zero invites the reader
    to believe a direction the data does not support. Where that happens the app
    says it in words rather than leaving the reader to compare two numbers in
    different places on the page.
    """
    if low <= 0 <= high:
        st.warning(
            f"**The sign of {what} is not established.** The uncertainty band "
            f"runs from {low / TG:,.1f} to {high / TG:,.1f} Tg C, which spans "
            "zero, so these data cannot say whether this was a net source or a "
            "net sink. The point estimate is the centre of that range, not a "
            "finding. Narrowing it needs measured carbon densities, not a "
            "better land-cover map."
        )


# ==================================================================== map tab
def render_map(region: str, year: int, mode: str, gee_ok: bool) -> None:
    st.subheader("Land cover map")
    if not gee_ok:
        st.warning(
            "Map tiles need a live Earth Engine connection, which is not "
            "available right now. Every number in the other tabs comes from the "
            "cached tables and is unaffected."
        )
        return

    import gee as G
    from streamlit_folium import st_folium

    @st.cache_data(ttl=3600, show_spinner=False)
    def tiles(year: int, mode: str) -> str:
        img = G.land_cover(year, G.pakistan().geometry())
        if mode == "Four-class aggregate":
            return G.tile_url(G.aggregated(img).clip(G.pakistan()), G.agg_vis())
        return G.tile_url(G.lccs_for_display(img).clip(G.pakistan()), G.lccs_vis())

    @st.cache_data(ttl=3600, show_spinner=False)
    def boundary(region: str) -> dict:
        """Region outline as GeoJSON folium can actually walk.

        Two things have to be handled. Earth Engine returns GAUL outlines as a
        GeometryCollection, and folium's iter_coords assumes every geometry has
        a 'coordinates' key, so it raises KeyError on one. And the unsimplified
        national polygon is a multi-megabyte payload that slows the first render
        badly. So: dissolve, simplify to a 1 km tolerance, then flatten any
        GeometryCollection into individual features.
        """
        pmap = A.load()["meta"]["province_of"]
        if region == A.NATIONAL:
            fc = G.pakistan()
        elif region in set(pmap.values()):
            # AJK and Gilgit-Baltistan are both a territory and their own unit,
            # so the territory branch has to be tested first.
            fc = G.province(region)
        else:
            fc = G.district(region)

        geom = fc.geometry().simplify(maxError=1000).getInfo()
        return {"type": "FeatureCollection", "features": _flatten(geom)}

    def _flatten(geom: dict) -> list[dict]:
        """Reduce an Earth Engine geometry to polygons Leaflet will accept.

        Simplifying the GAUL outline returns a GeometryCollection which, for
        Pakistan, holds 126 Polygons plus 121 Points, 340 LineStrings and one
        LinearRing. The points and linestrings are zero-area slivers thrown off
        by the simplification, and LinearRing is not a GeoJSON type at all, so
        Leaflet rejects the whole payload with "Invalid GeoJSON object" and the
        map silently collapses to zero height. Keep the polygons, promote the
        LinearRing to one, drop the rest.
        """
        t = geom.get("type")
        if t == "GeometryCollection":
            out = []
            for g in geom.get("geometries", []):
                out.extend(_flatten(g))
            return out
        if t == "LinearRing":
            geom = {"type": "Polygon", "coordinates": [geom["coordinates"]]}
        elif t not in ("Polygon", "MultiPolygon"):
            return []
        if "coordinates" not in geom:
            return []
        return [{"type": "Feature", "properties": {}, "geometry": geom}]

    with st.spinner("Rendering Earth Engine tiles..."):
        try:
            url = tiles(year, mode)
            bnd = boundary(region)
        except Exception as e:
            st.error(f"Earth Engine could not render tiles: {str(e)[:200]}")
            return

    m = charts.build_map([(f"GLC-FCS30D {year}", url)], bnd)
    st_folium(m, height=560, use_container_width=True,
              returned_objects=[], key=f"map-{year}-{mode}-{region}")

    present = sorted(A.areas(A.NATIONAL, year).keys()) if year in C.ACTUAL_YEARS \
        else sorted(C.LCCS)
    st.markdown("**Legend**", help="Classes actually present in the national extent.")
    st.markdown(
        charts.legend_html(present, aggregate=(mode == "Four-class aggregate")),
        unsafe_allow_html=True,
    )
    st.caption(
        "Tiles are rendered live from GLC-FCS30D at 30 m through Earth Engine. "
        "The slider covers every year the archive holds (1985, 1990, 1995, then "
        "2000-2022), not only the four study epochs."
    )


# ========================================================= change and carbon tab
def seam_warning(y0: int, y1: int) -> None:
    """Say plainly when a comparison crosses the two production lines."""
    if not C.spans_seam(y0, y1):
        return
    st.error(
        f"**This {y0}-{y1} comparison crosses a product seam and overstates "
        f"change.** GLC-FCS30D stitches two production lines together: "
        f"five-yearly maps to 1995, annual maps from 2000. Measured on Lahore "
        f"District, built-up area jumps **+66% between 1995 and 2000** against "
        f"a smooth 6-9% per interval through the annual years, and the 1985 and "
        f"1990 maps are identical to the pixel. Much of the change reported here "
        f"is that seam, not land conversion. Use **2000 → {C.ACTUAL_YEARS[-1]}** "
        f"in the sidebar for a seam-free comparison."
    )


def snow_note(region: str, y0: int, y1: int) -> None:
    """Flag flux that is really interannual snow cover rather than land change."""
    sf = A.snow_flux(region, y0, y1)
    if abs(sf["share_of_gross_loss"]) < 0.02:
        return
    st.info(
        f"**About {abs(sf['share_of_gross_loss']) * 100:.0f}% of the gross loss "
        f"here is the permanent-ice class changing, which is mostly snow, not "
        f"land.** GLC-FCS30D class 220 records what the imagery saw as snow or "
        f"ice on the day it was classified. Nationally it reads 16,105 km² in "
        f"2000, 19,875 in 2013 and 16,912 in 2022 — a 14% swing in nine years, "
        f"which permanent ice cannot do. Grassland scored as turning to ice "
        f"registers as a total carbon loss, and the reverse as a gain, so "
        f"{sf['ice_area_ha'] / 100:,.0f} km² of this comparison is seasonal "
        f"timing. Net flux excluding it is "
        f"{sf['net_excluding_ice_Mg_C'] / TG:+,.1f} Tg C against "
        f"{(sf['net_excluding_ice_Mg_C'] + sf['ice_net_Mg_C']) / TG:+,.1f} with "
        "it. Neither is a glacier measurement."
    )


def render_change(region: str, y0: int, y1: int) -> None:
    st.subheader(f"{region}: {y0} to {y1}")
    seam_warning(y0, y1)

    fs = A.flux_summary(region, y0, y1)
    a0, a1 = A.agg_areas(region, y0), A.agg_areas(region, y1)
    s0, s1 = A.stock(region, y0), A.stock(region, y1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Built-up area", f"{a1[C.BUILTUP] / 100:,.0f} km²",
              f"{(a1[C.BUILTUP] - a0[C.BUILTUP]) / 100:+,.0f} km²")
    c2.metric("Vegetation area", f"{a1[C.VEGETATION] / 100:,.0f} km²",
              f"{(a1[C.VEGETATION] - a0[C.VEGETATION]) / 100:+,.0f} km²")
    c3.metric("Carbon stock", f"{_tg(s1[1])} Tg C",
              f"{(s1[1] - s0[1]) / TG:+,.2f} Tg C")
    c4.metric("Net carbon flux", _fmt_signed(fs["net_Mg_C"]),
              f"{fs['net_CO2e_Mg'] / TG:+,.1f} Tg CO₂e", delta_color="off")

    st.caption(
        f"Uncertainty on the net flux runs from {_tg(fs['net_low_Mg_C'])} to "
        f"{_tg(fs['net_high_Mg_C'])} Tg C. Gross loss {_tg(fs['gross_loss_Mg_C'])} Tg C, "
        f"gross gain {_tg(fs['gross_gain_Mg_C'])} Tg C. A net figure alone would hide "
        "that both are happening at once."
    )
    sign_note(fs["net_low_Mg_C"], fs["net_high_Mg_C"], "the net carbon flux")
    snow_note(region, y0, y1)

    st.divider()
    st.markdown("#### Carbon lost to built-up expansion")
    b1, b2 = st.columns([1, 1])
    with b1:
        st.metric("Vegetated land converted to built-up",
                  f"{fs['vegetation_to_builtup_ha'] / 100:,.0f} km²")
        st.metric("Carbon released by that conversion",
                  f"{abs(fs['vegetation_to_builtup_Mg_C']) / TG:,.2f} Tg C")
        st.caption(
            f"Range {abs(fs['vegetation_to_builtup_high_Mg_C']) / TG:,.2f} to "
            f"{abs(fs['vegetation_to_builtup_low_Mg_C']) / TG:,.2f} Tg C, equivalent to "
            f"{abs(fs['vegetation_to_builtup_Mg_C']) * C.CO2_PER_C / TG:,.1f} Tg CO₂."
        )
        sign_note(fs["vegetation_to_builtup_low_Mg_C"],
                  fs["vegetation_to_builtup_high_Mg_C"],
                  "carbon released by built-up expansion")
    with b2:
        st.metric("All vegetated land lost to any non-vegetated class",
                  f"{fs['vegetation_lost_ha'] / 100:,.0f} km²")
        st.metric("Carbon change from all vegetation loss",
                  f"{abs(fs['vegetation_lost_Mg_C']) / TG:,.2f} Tg C")
        st.caption(
            "Wider than the built-up figure: it also counts vegetation that "
            "became bare ground or open water."
        )

    st.divider()
    agg_t = A.agg_transitions(region, y0, y1)
    changed = sum(ha for (f, t), ha in agg_t.items() if f != t)
    total = sum(agg_t.values()) or 1.0
    st.plotly_chart(charts.sankey(agg_t, y0, y1), width="stretch")
    st.caption(
        f"{changed / 100:,.0f} km² changed class between {y0} and {y1}, which is "
        f"{100 * changed / total:.1f}% of {region}. The other "
        f"{100 * (total - changed) / total:.1f}% persisted and is excluded from "
        "the diagram, because at this scale it would be one band wide enough to "
        "hide every conversion beside it."
    )
    st.plotly_chart(charts.flux_waterfall(fs["rows"]), width="stretch")


# ================================================================ trajectory tab
def render_trajectory(region: str) -> None:
    st.subheader(f"{region}: the whole record")
    groups_series = {y: A.group_areas(region, y) for y in C.ACTUAL_YEARS}
    agg_series = {y: A.agg_areas(region, y) for y in C.ACTUAL_YEARS}
    carbon_series = {y: A.stock(region, y) for y in C.ACTUAL_YEARS}

    present = [g for g in C.GROUPS
               if any(groups_series[y].get(g, 0) > 0 for y in C.ACTUAL_YEARS)]
    st.plotly_chart(charts.area_trajectory(groups_series, present),
                    width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.agg_bars(agg_series), width="stretch")
    with c2:
        st.plotly_chart(charts.carbon_trajectory(carbon_series),
                        width="stretch")

    st.plotly_chart(charts.pool_bars(A.stock_by_pool(region, C.ACTUAL_YEARS[-1])),
                    width="stretch")

    rows = []
    for y in C.ACTUAL_YEARS:
        a = A.agg_areas(region, y)
        s = A.stock(region, y)
        tot = sum(a.values()) or 1
        rows.append({
            "Epoch": y,
            "Built-up km²": a[C.BUILTUP] / 100,
            "Built-up %": 100 * a[C.BUILTUP] / tot,
            "Vegetation km²": a[C.VEGETATION] / 100,
            "Vegetation %": 100 * a[C.VEGETATION] / tot,
            "Water km²": a[C.WATER] / 100,
            "Bare km²": a[C.BARE] / 100,
            "Carbon low Tg C": s[0] / TG,
            "Carbon best Tg C": s[1] / TG,
            "Carbon high Tg C": s[2] / TG,
        })
    st.dataframe(pd.DataFrame(rows).set_index("Epoch").round(2),
                 width="stretch")


# =============================================================== arithmetic tab
def render_arithmetic(region: str, y0: int, y1: int) -> None:
    st.subheader("Show the arithmetic")
    seam_warning(y0, y1)
    st.markdown(
        "Nothing in this app is a black box. Every headline number is a sum of "
        "products, and each step is laid out below with the actual values used."
    )

    # ---- step 1
    st.markdown("### Step 1. Pixel areas, counted at native resolution")
    st.markdown(
        "Earth Engine sums `ee.Image.pixelArea()` grouped by class code, per "
        "district, at **30 m** — the product's native resolution. Districts are "
        "then summed to provinces and to the country, which is exact."
    )
    st.code(
        "ee.Image.pixelArea()\n"
        "  .addBands(land_cover_image)\n"
        "  .reduceRegion(\n"
        "      reducer  = ee.Reducer.sum().group(groupField=1, groupName='lc'),\n"
        "      geometry = district_geometry,\n"
        "      scale    = 30,\n"
        "      maxPixels= 1e13, tileScale = 16)",
        language="python")
    with st.expander("Why not reduce the whole country in one request?"):
        st.markdown(
            "It is about 877 million pixels per epoch and will not return inside "
            "Earth Engine's interactive limits. Reducing at 300 m does return, but "
            "a scale check against native resolution measured the built-up share "
            "shifting **+3.4 percentage points** in Islamabad and **−1.0** in "
            "Punjab. Built-up is the class the entire carbon result depends on, so "
            "that bias was not acceptable. Splitting by district keeps every "
            "request small enough to run at 30 m."
        )

    # ---- step 2
    st.markdown("### Step 2. Carbon density per class")
    st.markdown(
        "Each class carries four IPCC pools, each as a low / best / high triple, "
        "so the uncertainty band is carried through the calculation rather than "
        "attached at the end."
    )
    present = sorted(A.areas(region, y1), key=lambda c: -A.areas(region, y1)[c])
    dens = []
    for c in present:
        p = C.CARBON_POOLS[c]
        t = C.total_density(c)
        dens.append({
            "Code": c, "Class": C.LCCS.get(c, "?"), "Group": C.GROUP_OF.get(c, ""),
            "Above": p["above"][1], "Below": p["below"][1],
            "Soil": p["soil"][1], "Dead": p["dead"][1],
            "Total low": t[0], "Total best": t[1], "Total high": t[2],
        })
    st.dataframe(pd.DataFrame(dens).set_index("Code").round(1),
                 width="stretch", height=320)
    st.caption("Mg C per hectare. Classes ordered by how much of the region they cover.")

    st.error(
        "**These densities are Tier 1 placeholders.** They are order-of-magnitude "
        "defaults chosen to be defensible for Pakistan's climate zones. They are "
        "not transcribed from a specific IPCC table and must be checked against "
        "IPCC 2006 Volume 4 and Pakistani literature before any thesis or "
        "manuscript use. Every carbon figure in this app inherits that caveat."
    )

    # ---- step 3
    st.markdown("### Step 3. Stock is area times density, summed over classes")
    a1 = A.areas(region, y1)
    lines, tot = [], 0.0
    for c in present[:10]:
        d = C.total_density(c)[1]
        contrib = a1[c] * d
        tot += contrib
        lines.append(f"{C.LCCS.get(c,'?')[:34]:<34} {a1[c]:>13,.0f} ha × "
                     f"{d:>6.1f} Mg C/ha = {contrib / TG:>9,.3f} Tg C")
    rest = sum(a1[c] * C.total_density(c)[1] for c in present[10:])
    lines.append(f"{'... ' + str(max(0, len(present) - 10)) + ' further classes':<34} "
                 f"{'':>13}   {'':>6}   = {rest / TG:>9,.3f} Tg C")
    lines.append("-" * 78)
    lines.append(f"{f'Total stock, {region} {y1}':<34} {'':>13}   {'':>6}   "
                 f"= {(tot + rest) / TG:>9,.3f} Tg C")
    st.code("\n".join(lines), language="text")

    # ---- step 4
    st.markdown("### Step 4. Flux is a from-to crosstab, never a subtraction")
    st.markdown(
        "Class codes are nominal labels, not quantities. `lc_2022 − lc_1995` is "
        "meaningless: a difference of 2 could be built-up becoming water or "
        "cropland becoming bare land, and the two render identically. So change "
        "is computed as a crosstab, and carbon flux per conversion is"
    )
    st.latex(r"\Delta C_{f\rightarrow t} = A_{f\rightarrow t}\;"
             r"\bigl(\rho_{t} - \rho_{f}\bigr)")
    st.markdown(
        "where $A$ is converted area in hectares and $\\rho$ is total carbon "
        "density in Mg C/ha. The low bound pairs the poorest destination against "
        "the richest origin, because the two are independent estimates and the "
        "loss is largest in exactly that pairing."
    )

    fs = A.flux_summary(region, y0, y1)
    work = []
    for r in fs["rows"][:12]:
        df, dt = C.total_density(r["from"])[1], C.total_density(r["to"])[1]
        work.append(f"{r['from_name'][:24]:<24} → {r['to_name'][:24]:<24} "
                    f"{r['area_ha']:>11,.0f} ha × ({dt:>6.1f} − {df:>6.1f}) = "
                    f"{r['best_Mg_C'] / TG:>8,.3f} Tg C")
    work.append("-" * 100)
    work.append(f"{'Gross loss':<51} {'':>11}    {'':>17}   "
                f"{fs['gross_loss_Mg_C'] / TG:>8,.3f} Tg C")
    work.append(f"{'Gross gain':<51} {'':>11}    {'':>17}   "
                f"{fs['gross_gain_Mg_C'] / TG:>8,.3f} Tg C")
    work.append(f"{'Net':<51} {'':>11}    {'':>17}   "
                f"{fs['net_Mg_C'] / TG:>8,.3f} Tg C")
    st.code("\n".join(work), language="text")
    st.caption("The twelve largest losses. Persistence cells contribute nothing by "
               "construction and are excluded.")

    # ---- step 5
    st.markdown("### Step 5. What the uncorrected carbon table would have said")
    lc = A.legacy_comparison(region, y0, y1)
    st.markdown(
        "The original Earth Engine script for the Lahore work gave the whole "
        "Vegetation class 150 Mg C/ha, a closed-forest value. Most of Pakistan's "
        "vegetated area is annually harvested irrigated cropland, which stores "
        "very little standing biomass. Applying one forest number nationally "
        "repeats that error at national scale, so here is the size of it, measured."
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Uncorrected single-value table", _fmt_signed(lc["legacy_Mg_C"]))
    m2.metric("Per-class corrected", _fmt_signed(lc["corrected_Mg_C"]))
    m3.metric("Overstatement factor", f"{lc['ratio']:.2f}×")
    st.caption(
        "Reported as a measured ratio rather than an assertion. The Lahore "
        "district-level equivalent of this correction was 5.9×."
    )

    with st.expander("Full conversion table (every non-persistence cell)"):
        df = pd.DataFrame([{
            "From": r["from_name"], "To": r["to_name"],
            "Area km²": r["area_ha"] / 100,
            "Low Tg C": r["low_Mg_C"] / TG,
            "Best Tg C": r["best_Mg_C"] / TG,
            "High Tg C": r["high_Mg_C"] / TG,
        } for r in fs["rows"]])
        st.dataframe(df.round(3), width="stretch", height=420)
        st.download_button("Download as CSV", df.to_csv(index=False),
                           f"flux_{region}_{y0}_{y1}.csv", "text/csv")


# ================================================================= districts tab
def render_districts(y0: int, y1: int) -> None:
    st.subheader(f"All districts, {y0} to {y1}")
    rows = A.district_table(y0, y1)
    if not rows:
        st.warning("No district rows in the cache yet.")
        return

    st.plotly_chart(charts.district_scatter(rows), width="stretch")

    df = pd.DataFrame([{
        "District": r["district"], "Province": r["province"],
        "Area km²": r["area_ha"] / 100,
        f"Built-up {y0} km²": r["builtup_from_ha"] / 100,
        f"Built-up {y1} km²": r["builtup_to_ha"] / 100,
        "Built-up gain km²": r["builtup_gain_ha"] / 100,
        f"Built-up {y1} %": r["builtup_pct_to"],
        "Vegetation change km²": r["veg_change_ha"] / 100,
        "Net carbon Tg C": r["net_Mg_C"] / TG,
        "Net carbon Mg C/ha": r["net_Mg_C_per_ha"],
    } for r in rows]).round(3)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Largest built-up expansion**")
        st.dataframe(df.nlargest(10, "Built-up gain km²")
                     [["District", "Province", "Built-up gain km²", "Net carbon Tg C"]],
                     width="stretch", hide_index=True)
    with c2:
        st.markdown("**Largest carbon loss**")
        st.dataframe(df.nsmallest(10, "Net carbon Tg C")
                     [["District", "Province", "Net carbon Tg C", "Built-up gain km²"]],
                     width="stretch", hide_index=True)

    st.markdown("**Every district**")
    st.dataframe(df.sort_values("Net carbon Tg C"), width="stretch",
                 height=420, hide_index=True)
    st.download_button("Download district table as CSV", df.to_csv(index=False),
                       f"districts_{y0}_{y1}.csv", "text/csv")
