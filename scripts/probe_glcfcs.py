"""Establish exactly which years GLC-FCS30D offers and how it tiles over Pakistan."""
import json, ee
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])

for name in ("annual", "five-years-map"):
    col = ee.ImageCollection(f"projects/sat-io/open-datasets/GLC-FCS30D/{name}")
    first = col.first()
    bands = first.bandNames().getInfo()
    print(f"--- {name}: {col.size().getInfo()} tiles, {len(bands)} bands")
    print("   ", bands)
    props = first.propertyNames().getInfo()
    print("    props:", props)
    print()

# Does it actually cover Pakistan, and what class codes appear there?
pak = (ee.FeatureCollection("FAO/GAUL/2015/level1")
       .filter(ee.Filter.eq("ADM0_NAME", "Pakistan")))
print("Pakistan ADM1 units:", pak.size().getInfo())
print("provinces:", pak.aggregate_array("ADM1_NAME").getInfo())
geom = pak.geometry()
print("area km2:", round(geom.area(maxError=1000).getInfo() / 1e6))

ann = ee.ImageCollection("projects/sat-io/open-datasets/GLC-FCS30D/annual")
n_over = ann.filterBounds(geom).size().getInfo()
print("annual tiles intersecting Pakistan:", n_over)

mosaic = ann.filterBounds(geom).mosaic()
# histogram of last band (2022) over Pakistan at coarse scale, just to see codes
hist = mosaic.select("b23").reduceRegion(
    reducer=ee.Reducer.frequencyHistogram(), geometry=geom,
    scale=2000, maxPixels=1e9, bestEffort=True).getInfo()
print("\n2022 (b23) class codes over Pakistan @2km:")
h = hist.get("b23", {})
tot = sum(h.values())
for k in sorted(h, key=lambda x: -h[x]):
    print(f"   code {k:>4}  {100*h[k]/tot:6.2f}%")
