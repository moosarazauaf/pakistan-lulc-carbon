import json, ee
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])

g1 = ee.FeatureCollection("FAO/GAUL/2015/level1")
pak = g1.filter(ee.Filter.eq("ADM0_NAME", "Pakistan"))
print("GAUL Pakistan ADM1:", pak.aggregate_array("ADM1_NAME").getInfo())
print("GAUL Pakistan km2:", round(pak.geometry().area(maxError=2000).getInfo()/1e6))

jk = g1.filter(ee.Filter.stringContains("ADM0_NAME", "Jammu"))
print("\nJammu/Kashmir ADM0 names:", sorted(set(jk.aggregate_array("ADM0_NAME").getInfo())))
print("Jammu/Kashmir ADM1 names:", jk.aggregate_array("ADM1_NAME").getInfo())

# level2 districts, for the drill-down
g2 = ee.FeatureCollection("FAO/GAUL/2015/level2")
pak2 = g2.filter(ee.Filter.eq("ADM0_NAME", "Pakistan"))
print("\nGAUL Pakistan ADM2 districts:", pak2.size().getInfo())
names = pak2.aggregate_array("ADM2_NAME").getInfo()
print("sample:", sorted(names)[:15])
print("Lahore present:", "Lahore" in names)
