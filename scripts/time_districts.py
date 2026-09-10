"""Can we afford native 30 m accounting if we split by district and parallelise?"""
import sys, time, ee, concurrent.futures as cf
sys.path.insert(0, "src")
import gee
gee.init()

d = gee.districts()
info = d.aggregate_array("ADM2_NAME").getInfo()
areas = d.geometry().area(maxError=2000).getInfo()/1e6
print(f"{len(info)} districts, national {areas:,.0f} km2")

# find the largest few
feats = d.map(lambda f: f.set("km2", f.geometry().area(maxError=2000).divide(1e6)))
big = feats.sort("km2", False).limit(5).aggregate_array("ADM2_NAME").getInfo()
bigkm = feats.sort("km2", False).limit(5).aggregate_array("km2").getInfo()
print("largest:", [f"{n} {k:,.0f}km2" for n,k in zip(big,bigkm)])

# time the single largest at 30 m
name = big[0]
g = gee.district(name).geometry()
t=time.time(); a = gee.class_areas_ha(2022, g, scale=30); dt=time.time()-t
print(f"\n{name} @30m: {dt:.1f}s, {sum(a.values())/100:,.0f} km2")

# time a parallel batch of 12 mid-size districts at 30 m
sample = [n for n in info if n not in big][:12]
t=time.time()
def one(n):
    return n, sum(gee.class_areas_ha(2022, gee.district(n).geometry(), scale=30).values())
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    res = list(ex.map(one, sample))
dt = time.time()-t
tot = sum(v for _,v in res)/100
print(f"12 districts in parallel @30m: {dt:.1f}s for {tot:,.0f} km2  -> {tot/dt:,.0f} km2/s")
print(f"projected full country, 1 epoch: {areas/(tot/dt)/60:.1f} min")
