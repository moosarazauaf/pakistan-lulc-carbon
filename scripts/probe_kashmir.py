"""Identify which GAUL 'Jammu and Kashmir' sub-units are Pakistan-administered."""
import ee, json
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])

g2 = ee.FeatureCollection("FAO/GAUL/2015/level2")
jk = g2.filter(ee.Filter.eq("ADM0_NAME", "Jammu and Kashmir"))
print("ADM2 features:", jk.size().getInfo())

feats = jk.map(lambda f: f.set(
    "km2", f.geometry().area(maxError=2000).divide(1e6),
    "lon", f.geometry().centroid(maxError=2000).coordinates().get(0),
    "lat", f.geometry().centroid(maxError=2000).coordinates().get(1)))
rows = feats.reduceColumns(
    ee.Reducer.toList(5),
    ["ADM2_NAME", "ADM1_NAME", "km2", "lon", "lat"]).getInfo()["list"]

print(f"\n{'ADM2_NAME':<34}{'ADM1_NAME':<34}{'km2':>10}{'lon':>8}{'lat':>7}")
for r in sorted(rows, key=lambda x: -x[2]):
    print(f"{str(r[0])[:33]:<34}{str(r[1])[:33]:<34}{r[2]:>10,.0f}{r[3]:>8.2f}{r[4]:>7.2f}")
print("\ntotal km2:", round(sum(r[2] for r in rows)))
