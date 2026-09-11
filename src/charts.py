"""Plotly figures and the folium map. Presentation only, no arithmetic.

Every number these functions draw arrives already computed by analysis.py, so a
chart can never disagree with the table beside it.
"""
from __future__ import annotations

import folium
import plotly.graph_objects as go

import classes as C

PLOT_BG = "rgba(0,0,0,0)"
GRID = "rgba(128,128,128,0.18)"


def _shell(fig: go.Figure, height: int = 380, ytitle: str = "") -> go.Figure:
    # Top margin has to clear both the title and the horizontal legend that sits
    # above the plot area, or the two overlap and the title becomes unreadable.
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=72, b=10),
        title=dict(y=0.97, yanchor="top", x=0, xanchor="left"),
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=ytitle)
    return fig


# ------------------------------------------------------------------- area charts
def area_trajectory(series: dict[int, dict[str, float]], groups: list[str]) -> go.Figure:
    """Stacked group areas across the four epochs."""
    years = sorted(series)
    fig = go.Figure()
    for g in groups:
        fig.add_trace(go.Scatter(
            x=years,
            y=[series[y].get(g, 0.0) / 100.0 for y in years],  # ha -> km2
            name=g, mode="lines+markers", stackgroup="one",
            line=dict(width=0.5, color=C.GROUP_COLOURS.get(g, "#888")),
            fillcolor=C.GROUP_COLOURS.get(g, "#888"),
        ))
    fig.update_layout(title="Land-cover area by class group")
    fig = _shell(fig, 430, "km²")
    # Four irregularly spaced epochs. Left numeric, plotly invents evenly spaced
    # ticks (1995, 2003, 2011, 2019) that are not the years we actually have.
    fig.update_xaxes(type="category")
    return fig


def agg_bars(series: dict[int, dict[int, float]]) -> go.Figure:
    """The four-class view, as grouped bars so epoch-to-epoch change is readable."""
    years = sorted(series)
    fig = go.Figure()
    for cid, label in C.AGG_NAMES.items():
        fig.add_trace(go.Bar(
            x=[str(y) for y in years],
            y=[series[y].get(cid, 0.0) / 100.0 for y in years],
            name=label, marker_color=C.AGG_COLOURS[cid],
        ))
    fig.update_layout(barmode="group",
                      title="Four-class aggregate (Lahore-comparable)")
    fig = _shell(fig, 400, "km²")
    fig.update_xaxes(type="category")
    return fig


def carbon_trajectory(series: dict[int, tuple[float, float, float]]) -> go.Figure:
    """Carbon stock with its uncertainty band drawn, not appended as a footnote."""
    years = sorted(series)
    lo = [series[y][0] / 1e6 for y in years]
    be = [series[y][1] / 1e6 for y in years]
    hi = [series[y][2] / 1e6 for y in years]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years + years[::-1], y=hi + lo[::-1],
                             fill="toself", fillcolor="rgba(39,174,96,0.16)",
                             line=dict(width=0), name="low-high range",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=years, y=be, mode="lines+markers", name="best estimate",
                             line=dict(color="#1d7a3e", width=3),
                             marker=dict(size=9)))
    fig.update_layout(title="Terrestrial carbon stock")
    fig = _shell(fig, 400, "Tg C (million Mg C)")
    fig.update_xaxes(type="category")
    return fig


def pool_bars(pools: dict[str, tuple[float, float, float]]) -> go.Figure:
    names = [C.POOL_LABELS[p] for p in C.POOL_NAMES]
    best = [pools[p][1] / 1e6 for p in C.POOL_NAMES]
    err_lo = [(pools[p][1] - pools[p][0]) / 1e6 for p in C.POOL_NAMES]
    err_hi = [(pools[p][2] - pools[p][1]) / 1e6 for p in C.POOL_NAMES]
    fig = go.Figure(go.Bar(
        x=names, y=best, marker_color="#1d7a3e",
        error_y=dict(type="data", symmetric=False, array=err_hi, arrayminus=err_lo),
    ))
    fig.update_layout(title="Carbon by IPCC pool")
    return _shell(fig, 320, "Tg C")


# -------------------------------------------------------------------- flux charts
def flux_waterfall(rows: list[dict], top: int = 12) -> go.Figure:
    """The largest individual conversions, losses left, gains right."""
    losses = [r for r in rows if r["best_Mg_C"] < 0][:top]
    gains = sorted([r for r in rows if r["best_Mg_C"] > 0],
                   key=lambda r: -r["best_Mg_C"])[:max(3, top // 3)]
    sel = losses + gains[::-1]
    labels = [f"{r['from_name'][:26]} → {r['to_name'][:26]}" for r in sel]
    vals = [r["best_Mg_C"] / 1e6 for r in sel]
    colours = ["#c0392b" if v < 0 else "#1d7a3e" for v in vals]

    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h", marker_color=colours,
        hovertemplate="%{y}<br>%{x:.2f} Tg C<extra></extra>",
    ))
    fig.update_layout(title="Largest carbon changes by conversion",
                      height=max(340, 26 * len(sel) + 120))
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
                      hovermode="closest")
    fig.update_xaxes(gridcolor=GRID, title="Tg C (negative = loss)", zeroline=True,
                     zerolinecolor="rgba(128,128,128,0.5)")
    fig.update_yaxes(autorange="reversed")
    return fig


def sankey(agg_trans: dict[tuple[int, int], float], year_from: int,
           year_to: int) -> go.Figure:
    """Four-class from-to flow, showing conversions only.

    Persistence is deliberately excluded. Over 96% of Pakistan keeps its class
    across a decade, and vegetation alone is 72% of the country, so a diagram
    that includes persistence is one enormous band with the conversions invisible
    beside it and the small-class labels stacked on top of each other. Dropping
    the diagonal makes the thing it is meant to show actually visible; the
    persisting area is stated in the caption instead.
    """
    order = sorted(C.AGG_NAMES)
    n = len(order)
    labels = ([f"{C.AGG_NAMES[i]} {year_from}" for i in order]
              + [f"{C.AGG_NAMES[i]} {year_to}" for i in order])
    node_col = [C.AGG_COLOURS[i] for i in order] * 2

    src, dst, val, lcol = [], [], [], []
    for (f, t), ha in sorted(agg_trans.items(), key=lambda kv: -kv[1]):
        if f == t or ha <= 0:
            continue
        src.append(f)
        dst.append(n + t)
        val.append(ha / 100.0)
        base = C.AGG_COLOURS[f].lstrip("#")
        r, g, b = (int(base[i:i + 2], 16) for i in (0, 2, 4))
        lcol.append(f"rgba({r},{g},{b},0.6)")

    fig = go.Figure(go.Sankey(
        node=dict(label=labels, color=node_col, pad=26, thickness=16,
                  line=dict(width=0)),
        link=dict(source=src, target=dst, value=val, color=lcol,
                  hovertemplate="%{source.label} → %{target.label}"
                                "<br>%{value:,.0f} km²<extra></extra>"),
    ))
    # A 10px margin leaves Plotly no room to place node labels outside the
    # diagram, so it falls back to drawing them inward, directly over the
    # (often dark-saturated) flow bands -- illegible for any label that lands
    # on a similarly dark colour. 130px on each side is enough for the
    # longest label ("Bare / sparse 2003") to sit fully in the margin, on the
    # plain page background, at this font size.
    fig.update_layout(
        title=f"Land converted between {year_from} and {year_to} "
              f"(persistence excluded)",
        height=460, margin=dict(l=130, r=130, t=50, b=10),
        paper_bgcolor=PLOT_BG,
        font=dict(size=12, color="#243e36"))
    return fig


def district_scatter(rows: list[dict]) -> go.Figure:
    """Built-up gain against carbon loss, one point per district."""
    fig = go.Figure(go.Scatter(
        x=[r["builtup_gain_ha"] / 100.0 for r in rows],
        y=[r["net_Mg_C"] / 1e6 for r in rows],
        mode="markers",
        marker=dict(size=9, color=[r["net_Mg_C"] / 1e6 for r in rows],
                    colorscale="RdYlGn", cmid=0, line=dict(width=0.5, color="#666"),
                    colorbar=dict(title="Tg C")),
        text=[f"{r['district']}<br>{r['province']}" for r in rows],
        hovertemplate="%{text}<br>built-up gain %{x:,.0f} km²"
                      "<br>net carbon %{y:.3f} Tg C<extra></extra>",
    ))
    fig.update_layout(title="Every district: built-up gain against net carbon change")
    fig = _shell(fig, 460, "net carbon change (Tg C)")
    fig.update_xaxes(title="built-up area gained (km²)")
    fig.update_layout(hovermode="closest")
    return fig


# --------------------------------------------------------------------- the map
def build_map(tile_layers: list[tuple[str, str]], boundary_geojson: dict | None,
              centre=(30.4, 69.4), zoom=5) -> folium.Map:
    """Folium map with one Earth Engine tile layer per requested year."""
    m = folium.Map(location=centre, zoom_start=zoom, tiles=None,
                   control_scale=True, prefer_canvas=True)
    # Both basemaps are keyless. folium's built-in "cartodbpositron" is not:
    # CARTO now gates that endpoint and serves tiles stamped "API KEY REQUIRED",
    # which looked fine locally and would have shipped a watermarked map.
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Terrain_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Terrain basemap", control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="OpenStreetMap contributors", name="Street basemap", control=True,
    ).add_to(m)

    for label, url in tile_layers:
        folium.raster_layers.TileLayer(
            tiles=url, attr="GLC-FCS30D / Google Earth Engine",
            name=label, overlay=True, control=True, opacity=0.85,
        ).add_to(m)

    if boundary_geojson:
        folium.GeoJson(
            boundary_geojson, name="Boundary",
            style_function=lambda _: {"color": "#111", "weight": 1.6,
                                      "fill": False, "opacity": 0.85},
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def legend_html(codes: list[int], aggregate: bool = False) -> str:
    """A legend Streamlit can render, since folium legends do not survive well."""
    items = []
    if aggregate:
        for cid, label in C.AGG_NAMES.items():
            items.append((C.AGG_COLOURS[cid], label))
    else:
        for c in codes:
            items.append((C.LCCS_COLOURS.get(c, "#999"), C.LCCS.get(c, str(c))))
    cells = "".join(
        f'<div style="display:flex;align-items:center;gap:7px;'
        f'padding:2px 10px 2px 0;font-size:12px;">'
        f'<span style="width:13px;height:13px;background:{col};'
        f'border:1px solid rgba(0,0,0,.28);border-radius:2px;flex:none;"></span>'
        f'<span>{name}</span></div>'
        for col, name in items
    )
    return (f'<div style="display:flex;flex-wrap:wrap;gap:2px 4px;">{cells}</div>')
