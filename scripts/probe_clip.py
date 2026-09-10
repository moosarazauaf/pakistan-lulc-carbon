"""Does clipping ADM2 districts to the mainland make the units tile exactly?"""
import ee, json, time
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])

A1 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM1") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))
A2 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM2") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))
SPECIAL = ["Azad Kashmir", "Gilgit-Baltistan"]
mainland = A1.filter(ee.Filter.inList("shapeName", SPECIAL).Not()).geometry(maxError=1000)
km2 = lambda g: g.area(maxError=2000).divide(1e6).getInfo()

print("mainland ADM1 union km2:", round(km2(mainland)))
t = time.time()
clipped = A2.geometry(maxError=1000).intersection(mainland, 1000)
print("ADM2 clipped to mainland km2:", round(km2(clipped)), f"({time.time()-t:.1f}s)")

# per-district timing for a border district
t = time.time()
d = A2.filter(ee.Filter.eq("shapeName", "Neelum")).size().getInfo()
print("\n'Neelum' in ADM2?", d)
for name in ("Muzaffarabad", "Kohistan", "Mansehra", "Lahore"):
    f = A2.filter(ee.Filter.eq("shapeName", name))
    if f.size().getInfo() == 0:
        print(f"  {name:<16} not in ADM2")
        continue
    raw = f.geometry(maxError=1000)
    t0 = time.time()
    cl = raw.intersection(mainland, 1000)
    print(f"  {name:<16} raw {km2(raw):>9,.0f} -> clipped {km2(cl):>9,.0f} km2  ({time.time()-t0:.1f}s)")
