import ee, json
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])

a1 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM1") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))
a2 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM2") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))

f1 = a1.map(lambda f: f.set("km2", f.geometry().area(maxError=2000).divide(1e6)))
rows = f1.reduceColumns(ee.Reducer.toList(2), ["shapeName", "km2"]).getInfo()["list"]
print("ADM1 units:", len(rows))
for n, k in sorted(rows, key=lambda r: -r[1]):
    print(f"   {n:<32}{k:>10,.0f} km2")
print("ADM1 total km2:", round(sum(r[1] for r in rows)))

print("\nADM2 districts:", a2.size().getInfo())
names = a2.aggregate_array("shapeName").getInfo()
print("sample:", sorted(names)[:8])
for probe in ("Lahore", "Muzaffarabad", "Gilgit", "Skardu", "Neelum", "Hunza"):
    hits = [n for n in names if probe.lower() in n.lower()]
    print(f"   {probe:<14} -> {hits}")
