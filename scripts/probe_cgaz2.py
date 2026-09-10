"""Do ADM2 + AJK + GB tile the national extent without overlap, and what is in GB?"""
import ee, json
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])
import sys; sys.path.insert(0, "src")
import classes as C

A1 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM1") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))
A2 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM2") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))

nat = A1.geometry(maxError=1000)
adm2 = A2.geometry(maxError=1000)
ajk = A1.filter(ee.Filter.eq("shapeName", "Azad Kashmir")).geometry(maxError=1000)
gb  = A1.filter(ee.Filter.eq("shapeName", "Gilgit-Baltistan")).geometry(maxError=1000)

km2 = lambda g: g.area(maxError=2000).divide(1e6)
print("national (ADM1 union)  km2:", round(km2(nat).getInfo()))
print("ADM2 union             km2:", round(km2(adm2).getInfo()))
print("AJK                    km2:", round(km2(ajk).getInfo()))
print("GB                     km2:", round(km2(gb).getInfo()))
print("ADM2 + AJK + GB        km2:",
      round(km2(adm2.union(ajk, 1000).union(gb, 1000)).getInfo()))
print("overlap ADM2 with AJK  km2:", round(km2(adm2.intersection(ajk, 1000)).getInfo()))
print("overlap ADM2 with GB   km2:", round(km2(adm2.intersection(gb, 1000)).getInfo()))

# What does GLC-FCS30D see in GB and AJK?
import gee as G
G._INITIALISED = True
for label, geom in (("Gilgit-Baltistan", gb), ("Azad Kashmir", ajk)):
    a = G.class_areas_ha(2022, geom, scale=300, tile_scale=16)
    a = {k: v for k, v in a.items() if k not in C.NODATA_CODES}
    tot = sum(a.values())
    print(f"\n{label}: {tot/100:,.0f} km2 (at 300 m probe)")
    for c in sorted(a, key=lambda k: -a[k])[:7]:
        print(f"    {C.LCCS.get(c,'?')[:34]:<34}{100*a[c]/tot:>6.2f}%")
