"""Is geoBoundaries available in GEE, and does it name AJK / GB districts?"""
import ee, json
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])

CANDIDATES = [
    "WM/geoLab/geoBoundaries/600/PAK/ADM1",
    "WM/geoLab/geoBoundaries/600/PAK/ADM2",
    "projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM1",
    "projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM2",
    "USDOS/LSIB_SIMPLE/2017",
]
for a in CANDIDATES:
    try:
        fc = ee.FeatureCollection(a)
        n = fc.size().getInfo()
        props = fc.first().propertyNames().getInfo()
        print(f"OK   {a}\n     n={n} props={props}")
    except Exception as e:
        print(f"FAIL {a}\n     {str(e).splitlines()[0][:120]}")
    print()
