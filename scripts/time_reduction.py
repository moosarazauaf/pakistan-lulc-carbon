"""Measure how long a real area reduction takes, so the cache build is sized right."""
import sys, time
sys.path.insert(0, "src")
import gee, classes as C

gee.init()
print("EE ready")

isb = gee.provinces().filter(__import__("ee").Filter.eq("ADM1_NAME", "Islamabad")).geometry()
punjab = gee.provinces().filter(__import__("ee").Filter.eq("ADM1_NAME", "Punjab")).geometry()

for label, geom, scale in (("Islamabad", isb, 300), ("Punjab", punjab, 300)):
    t = time.time()
    areas = gee.class_areas_ha(2022, geom, scale=scale)
    dt = time.time() - t
    tot = sum(areas.values())
    print(f"\n{label} @{scale}m  {dt:5.1f}s  total {tot:,.0f} ha ({tot/100:,.0f} km2)")
    for c in sorted(areas, key=lambda k: -areas[k])[:6]:
        print(f"    {c:>3} {C.LCCS.get(c,'?')[:30]:<30} {areas[c]:12,.0f} ha  {100*areas[c]/tot:5.2f}%")

t = time.time()
tr = gee.transition_areas_ha(1995, 2022, isb, scale=300)
print(f"\nIslamabad transitions 1995->2022  {time.time()-t:5.1f}s  {len(tr)} pairs")
loss = sorted(((v,k) for k,v in tr.items() if k[0]!=k[1]), reverse=True)[:6]
for v,k in loss:
    print(f"    {C.LCCS.get(k[0],'?')[:24]:<24} -> {C.LCCS.get(k[1],'?')[:24]:<24} {v:10,.0f} ha")
