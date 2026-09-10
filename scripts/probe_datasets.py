"""Probe which national land-cover archives are actually reachable in GEE.

Nothing downstream is designed until this says what exists, because the whole
1993-2023 story depends on an archive that genuinely reaches back to 1993.
"""
import json
import ee

KEY = "service_account.json"
info = json.load(open(KEY))
creds = ee.ServiceAccountCredentials(info["client_email"], KEY)
ee.Initialize(creds, project=info["project_id"])
print("EE initialised as", info["client_email"], "\n")

CANDIDATES = [
    # (id, kind)
    ("projects/sat-io/open-datasets/ESA_CCI_LC", "ImageCollection"),
    ("projects/sat-io/open-datasets/ESA/ESA_CCI_LC_1992_2020", "ImageCollection"),
    ("projects/sat-io/open-datasets/GLC-FCS30D/annual", "ImageCollection"),
    ("projects/sat-io/open-datasets/GLC-FCS30D/five-years-map", "ImageCollection"),
    ("MODIS/061/MCD12Q1", "ImageCollection"),
    ("ESA/WorldCover/v200", "ImageCollection"),
    ("COPERNICUS/Landcover/100m/Proba-V-C3/Global", "ImageCollection"),
    ("USGS/NLCD_RELEASES/2019_REL/NLCD", "ImageCollection"),
    ("FAO/GAUL/2015/level1", "FeatureCollection"),
]

for asset_id, kind in CANDIDATES:
    try:
        if kind == "ImageCollection":
            col = ee.ImageCollection(asset_id)
            n = col.size().getInfo()
            first = col.first()
            bands = first.bandNames().getInfo()
            # date range
            dates = col.aggregate_array("system:time_start").getInfo()
            import datetime as dt
            yrs = sorted({dt.datetime.utcfromtimestamp(d / 1000).year
                          for d in dates if d}) if dates else []
            span = f"{yrs[0]}-{yrs[-1]}" if yrs else "no time_start"
            print(f"OK   {asset_id}\n     n={n} bands={bands[:6]} years={span}")
            if yrs:
                print(f"     year list: {yrs}")
        else:
            fc = ee.FeatureCollection(asset_id)
            print(f"OK   {asset_id}  n={fc.size().getInfo()}")
    except Exception as e:
        msg = str(e).split("\n")[0][:150]
        print(f"FAIL {asset_id}\n     {msg}")
    print()
