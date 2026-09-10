"""Earth Engine access: authentication, the GLC-FCS30D mosaic, and area accounting.

Everything that talks to Earth Engine lives here. The app itself never builds an
ee object directly, so the whole pipeline can be exercised from a cache file
with no network, which is what makes the deployed app fast and what makes the
numbers auditable.

Accounting scale
----------------
GLC-FCS30D is a 30 m product. Summing pixel area at 30 m over 789,000 km2 is
about 877 million pixels per epoch, which reduceRegion will refuse or time out
on. Areas are therefore accumulated at ACCOUNTING_SCALE_M and the app states
that scale next to every area figure. This is a sampling of the 30 m map, not a
resampling of it: Earth Engine takes the class at the centre of each coarse
cell, so class proportions over a region the size of a province are close to
unbiased while individual small features are missed.
"""
from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from pathlib import Path

import ee

ROOT = Path(__file__).resolve().parent.parent
GLC = "projects/sat-io/open-datasets/GLC-FCS30D"
GAUL1 = "FAO/GAUL/2015/level1"
GAUL2 = "FAO/GAUL/2015/level2"

# See module docstring. 300 m keeps a full-country reduction inside Earth
# Engine's interactive limits with room to spare.
ACCOUNTING_SCALE_M = 300
NATIVE_SCALE_M = 30

_INITIALISED = False


def _shape_hint(text: str, err: Exception) -> str:
    """Describe how a malformed credential secret is wrong, without echoing it.

    The secret is a private key, so nothing from it is ever printed. This
    reports only structural facts - length, and which of a few known-wrong
    shapes it matches - which is enough to tell a mispasted secret from a
    rejected one without putting key material on screen.
    """
    n = len(text)
    if not text:
        shape = "it is empty"
    elif text.startswith("{"):
        shape = ("it starts with '{' so it looks like JSON, but is truncated or "
                 "has had its quotes mangled. Check the whole file was pasted, "
                 "from the opening brace to the closing one")
    elif "-----BEGIN" in text[:80]:
        shape = ("it is the private key on its own. The secret needs the whole "
                 "service-account JSON file, not just the private_key value")
    elif "=" in text.split("\n", 1)[0] and not text.startswith("{"):
        shape = ("it looks like TOML rather than JSON, so the key name was "
                 "probably pasted inside the value as well. The value between "
                 "the triple quotes should start with '{'")
    elif text.lower().endswith(".json") or "\\" in text[:120] or "/" in text[:120]:
        shape = ("it looks like a file path. The secret must hold the file's "
                 "contents, not its location")
    else:
        shape = "it is not JSON and does not match a known mistake"

    return (
        f"GEE_SERVICE_ACCOUNT was found but could not be parsed: {shape}. "
        f"(length {n} characters; {type(err).__name__}: {err}). "
        "Two forms are accepted on Streamlit Community Cloud, under Settings "
        "then Secrets. Multi-line, where the value must start with a brace:\n\n"
        "GEE_SERVICE_ACCOUNT = '''\n{ ...whole service_account.json... }\n'''\n\n"
        "Or single-line base64, which has no quoting or newline hazards:\n\n"
        "GEE_SERVICE_ACCOUNT = \"eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsIC4uLg==\""
    )


def init() -> None:
    """Authenticate once, from a service-account file or an env var.

    On Hugging Face Spaces the key cannot be committed, so it arrives as the
    GEE_SERVICE_ACCOUNT secret holding the JSON itself.
    """
    global _INITIALISED
    if _INITIALISED:
        return

    raw = os.environ.get("GEE_SERVICE_ACCOUNT")

    # Streamlit Community Cloud supplies secrets through st.secrets. It also
    # mirrors top-level string secrets into the environment, but not reliably
    # for every value shape, so read st.secrets explicitly rather than trusting
    # the mirror. Wrapped because gee.py must stay importable without Streamlit
    # (the cache builder and the tests both use it headless).
    if not raw:
        try:
            import streamlit as st

            raw = st.secrets.get("GEE_SERVICE_ACCOUNT")
        except Exception:  # noqa: BLE001
            raw = None

    if raw:
        # A TOML table arrives as a Mapping, not a dict: Streamlit wraps
        # sections in its own AttrDict, which is a Mapping but not a dict
        # subclass, so an isinstance(raw, dict) test misses it and the value
        # falls through to json.loads.
        if isinstance(raw, Mapping):
            info = {k: v for k, v in raw.items()}
            key_data = json.dumps(info)
        else:
            text = str(raw).strip()
            try:
                info = json.loads(text)
            except json.JSONDecodeError as e:
                # Fall back to base64. Pasting multi-line JSON into a hosting
                # secrets box is easy to get wrong: the triple quotes can be
                # saved empty, the editor can eat the newlines inside
                # private_key, or the key name can end up inside the value. A
                # single-line base64 blob has none of those failure modes, so
                # GEE_SERVICE_ACCOUNT accepts either form.
                try:
                    decoded = base64.b64decode(text, validate=True).decode("utf-8")
                    info = json.loads(decoded)
                    text = decoded
                except Exception:  # noqa: BLE001
                    raise RuntimeError(_shape_hint(text, e)) from None
            key_data = text
    else:
        path = ROOT / "service_account.json"
        if not path.exists():
            raise RuntimeError(
                "No Earth Engine credentials. Either place service_account.json "
                "at the project root, or set the GEE_SERVICE_ACCOUNT environment "
                "variable to the contents of that file."
            )
        info = json.loads(path.read_text())
        key_data = path.read_text()

    creds = ee.ServiceAccountCredentials(info["client_email"], key_data=key_data)
    ee.Initialize(creds, project=info["project_id"])
    _INITIALISED = True


# ------------------------------------------------------------------ geometries
# Boundaries are geoBoundaries CGAZ, not FAO GAUL.
#
# GAUL was the first choice and had to be abandoned. It files Gilgit-Baltistan
# and Azad Kashmir under a separate 'Jammu and Kashmir' ADM0 whose sub-units are
# all literally named "Administrative unit not available", so the two
# Pakistan-administered territories cannot be selected from it at all. GAUL also
# still carries the pre-2018 'North-West Frontier' and 'Federally Administered
# Tribal Areas' split.
#
# geoBoundaries names all eight ADM1 units, including Azad Kashmir and
# Gilgit-Baltistan, and uses Khyber Pakhtunkhwa. Excluding those two territories
# was not a small omission: Gilgit-Baltistan is 22% permanent ice and snow, and
# Azad Kashmir is 67% closed forest, which is the densest carbon in the country.
#
# Their sovereignty is disputed with India. They are included here because they
# are administered by Pakistan, and the app labels them as such rather than
# silently folding them into the national total.
CGAZ1 = "projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM1"
CGAZ2 = "projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM2"

# The two ADM1 units that have no ADM2 children in geoBoundaries, so they are
# carried as whole-territory units instead of being split into districts.
NO_DISTRICTS = ["Azad Kashmir", "Gilgit-Baltistan"]


def pakistan() -> ee.FeatureCollection:
    """All eight ADM1 units, 866,631 km2 including AJK and Gilgit-Baltistan."""
    return ee.FeatureCollection(CGAZ1).filter(ee.Filter.eq("shapeGroup", "PAK"))


def provinces() -> ee.FeatureCollection:
    return pakistan()


def province(name: str) -> ee.FeatureCollection:
    return pakistan().filter(ee.Filter.eq("shapeName", name))


def mainland() -> ee.Geometry:
    """Everything except AJK and Gilgit-Baltistan, used to clip the districts.

    geoBoundaries' ADM2 layer does not nest cleanly inside its own ADM1 layer:
    the district union is 794,481 km2 against a 788,670 km2 ADM1 mainland, and
    it overlaps AJK and Gilgit-Baltistan by 585 km2. Summing districts and the
    two territories unclipped would therefore double-count. Intersecting each
    district with this geometry removes both the overlap and the spill across
    the international border, leaving units that tile the country.
    """
    return (pakistan()
            .filter(ee.Filter.inList("shapeName", NO_DISTRICTS).Not())
            .geometry(maxError=1000))


def districts() -> ee.FeatureCollection:
    return ee.FeatureCollection(CGAZ2).filter(ee.Filter.eq("shapeGroup", "PAK"))


def unit_geometry(name: str) -> ee.Geometry:
    """Geometry of one accounting unit: a clipped district, or a whole territory."""
    if name in NO_DISTRICTS:
        return province(name).geometry(maxError=1000)
    return (districts()
            .filter(ee.Filter.eq("shapeName", name))
            .geometry(maxError=1000)
            .intersection(mainland(), 1000))


def district(name: str) -> ee.FeatureCollection:
    """Kept for the map's boundary overlay, which wants a FeatureCollection."""
    if name in NO_DISTRICTS:
        return province(name)
    return districts().filter(ee.Filter.eq("shapeName", name))


# ----------------------------------------------------------------- land cover
def land_cover(actual_year: int, region: ee.Geometry | None = None) -> ee.Image:
    """One year of GLC-FCS30D as a single-band image named 'lc'.

    The archive is 961 global tiles, so it has to be mosaicked. Filtering to the
    region first cuts that to the 9 tiles that touch Pakistan.
    """
    import classes as C

    coll_name, band = C.band_for(actual_year)
    coll = ee.ImageCollection(f"{GLC}/{coll_name}")
    if region is not None:
        coll = coll.filterBounds(region)
    return coll.mosaic().select([band], ["lc"])


def aggregated(img: ee.Image) -> ee.Image:
    """Remap the LCCS band to the four-class Lahore-comparable scheme."""
    import classes as C

    codes = sorted(C.AGGREGATE)
    return img.remap(codes, [C.AGGREGATE[c] for c in codes]).rename("agg")


# ------------------------------------------------------------------ accounting
def class_areas_ha(actual_year: int, region: ee.Geometry,
                   scale: int = ACCOUNTING_SCALE_M,
                   tile_scale: int = 16) -> dict[int, float]:
    """Area in hectares of every LCCS class inside `region` for one year."""
    img = land_cover(actual_year, region)
    grouped = (
        ee.Image.pixelArea()
        .addBands(img)
        .reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName="lc"),
            geometry=region,
            scale=scale,
            maxPixels=int(1e13),
            tileScale=tile_scale,
        )
    )
    out = {}
    for g in grouped.getInfo().get("groups", []):
        out[int(g["lc"])] = g["sum"] / 1e4  # m2 -> ha
    return out


def transition_areas_ha(year_from: int, year_to: int, region: ee.Geometry,
                        scale: int = ACCOUNTING_SCALE_M,
                        tile_scale: int = 16) -> dict[tuple[int, int], float]:
    """From-to crosstab in hectares between two epochs.

    A from-to crosstab, not a subtraction. Class codes are nominal labels rather
    than quantities, so `lc_2022 - lc_1995` is not interpretable: a difference of
    2 could be built-up becoming water or cropland becoming bare land, and the
    two render identically. This is the same correction the Lahore project made
    to its original Earth Engine script.
    """
    a = land_cover(year_from, region).rename("a")
    b = land_cover(year_to, region).rename("b")
    combined = a.multiply(1000).add(b).rename("ab")

    grouped = (
        ee.Image.pixelArea()
        .addBands(combined)
        .reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName="ab"),
            geometry=region,
            scale=scale,
            maxPixels=int(1e13),
            tileScale=tile_scale,
        )
    )
    out = {}
    for g in grouped.getInfo().get("groups", []):
        code = int(g["ab"])
        out[(code // 1000, code % 1000)] = g["sum"] / 1e4
    return out


# ------------------------------------------------------------------- map tiles
def tile_url(img: ee.Image, vis: dict) -> str:
    """XYZ template for a folium raster layer."""
    return ee.Image(img).getMapId(vis)["tile_fetcher"].url_format


def lccs_vis() -> dict:
    import classes as C

    codes = sorted(C.LCCS)
    return {
        "min": 0,
        "max": len(codes) - 1,
        "palette": [C.LCCS_COLOURS[c].lstrip("#") for c in codes],
    }


def lccs_for_display(img: ee.Image) -> ee.Image:
    """Remap sparse LCCS codes onto a dense 0..n-1 index so a palette lines up."""
    import classes as C

    codes = sorted(C.LCCS)
    return img.remap(codes, list(range(len(codes)))).rename("idx")


def agg_vis() -> dict:
    import classes as C

    return {
        "min": 0,
        "max": 3,
        "palette": [C.AGG_COLOURS[i].lstrip("#") for i in range(4)],
    }
