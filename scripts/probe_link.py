import ee, json, collections
info = json.load(open("service_account.json"))
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], "service_account.json"),
              project=info["project_id"])
A1 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM1") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))
A2 = ee.FeatureCollection("projects/sat-io/open-datasets/geoboundaries/CGAZ_ADM2") \
       .filter(ee.Filter.eq("shapeGroup", "PAK"))
id2name = dict(zip(A1.aggregate_array("shapeID").getInfo(),
                   A1.aggregate_array("shapeName").getInfo()))
rows = A2.reduceColumns(ee.Reducer.toList(2), ["shapeName", "ADM1_shape"]).getInfo()["list"]
c = collections.Counter()
unmapped = []
for n, a1 in rows:
    p = id2name.get(a1)
    c[p] += 1
    if p is None:
        unmapped.append((n, a1))
print("districts per ADM1:")
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print(f"   {str(k):<38}{v}")
print("unmapped:", unmapped[:5])
dupes = [n for n, k in collections.Counter(r[0] for r in rows).items() if k > 1]
print("duplicate district names:", dupes)
