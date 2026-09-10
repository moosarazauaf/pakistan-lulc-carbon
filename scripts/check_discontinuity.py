"""Is the 1995->2003 built-up jump real growth, or a seam between two products?

GLC-FCS30D is built from two production lines: five-yearly maps for 1985-1995
and annual maps for 2000-2022. If the jump is real, built-up should rise
smoothly through 2000, 2001, 2002. If it is a seam, 2000 will already sit at the
2003 level and the whole step will fall between 1995 and 2000.
"""
import sys, ee
sys.path.insert(0, "src")
import gee, classes as C
gee.init()

# Punjab is the urbanising heartland and completes fast.
geom = gee.districts().filter(ee.Filter.eq("ADM2_NAME", "Lahore District")).geometry()
print("Lahore District built-up share by year (30 m):\n")
print(f"  {'year':<8}{'source':<18}{'built-up km2':>14}{'share %':>10}")
prev = None
for y in [1985, 1990, 1995, 2000, 2001, 2002, 2003, 2005, 2010, 2013, 2022]:
    coll, band = C.band_for(y)
    a = gee.class_areas_ha(y, geom, scale=30, tile_scale=16)
    a = {k: v for k, v in a.items() if k not in C.NODATA_CODES}
    tot = sum(a.values())
    b = a.get(190, 0.0)
    flag = ""
    if prev is not None:
        jump = (b - prev) / prev * 100 if prev else 0
        flag = f"   {jump:+.0f}% vs previous"
    print(f"  {y:<8}{coll:<18}{b/100:>14,.0f}{100*b/tot:>10.2f}{flag}")
    prev = b
