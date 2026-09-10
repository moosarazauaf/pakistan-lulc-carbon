"""Is 300 m accounting defensible? Compare against 100 m and 30 m on real regions."""
import sys, time, ee
sys.path.insert(0, "src")
import gee, classes as C
gee.init()

def run(geom, label, scales):
    res = {}
    for s in scales:
        t = time.time()
        try:
            res[s] = (gee.class_areas_ha(2022, geom, scale=s), time.time()-t)
        except Exception as e:
            print(f"  {label} @{s}m FAILED: {str(e)[:90]}")
    base = max(res)  # coarsest
    fine = min(res)
    a_f, a_c = res[fine][0], res[base][0]
    tf, tc = sum(a_f.values()), sum(a_c.values())
    print(f"\n{label}: {fine}m {res[fine][1]:.1f}s vs {base}m {res[base][1]:.1f}s")
    print(f"  total ha: {tf:,.0f} vs {tc:,.0f}  ({100*(tc-tf)/tf:+.2f}%)")
    print(f"  {'class':<32}{'share@'+str(fine)+'m':>12}{'share@'+str(base)+'m':>12}{'diff pp':>9}")
    worst = 0.0
    for c in sorted(set(a_f) | set(a_c), key=lambda k: -a_f.get(k, 0)):
        pf, pc = 100*a_f.get(c,0)/tf, 100*a_c.get(c,0)/tc
        if max(pf, pc) < 0.5:
            continue
        worst = max(worst, abs(pf-pc))
        print(f"  {C.LCCS.get(c,'?')[:31]:<32}{pf:11.2f}%{pc:11.2f}%{pc-pf:+8.2f}")
    print(f"  worst class shift: {worst:.2f} percentage points")

isb = gee.provinces().filter(ee.Filter.eq("ADM1_NAME","Islamabad")).geometry()
pun = gee.provinces().filter(ee.Filter.eq("ADM1_NAME","Punjab")).geometry()
run(isb, "Islamabad", [30, 100, 300])
run(pun, "Punjab", [100, 300])
