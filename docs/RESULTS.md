# Results, and what they will and will not support

Generated from the completed cache: 133 accounting units, five epochs, native
30 m, 864,256 km² reconciled against the geoBoundaries CGAZ boundary. Includes
Azad Kashmir and Gilgit-Baltistan, both Pakistan-administered and disputed with
India.

## The five things worth knowing before quoting any number

### 1. The 1995 to 2000 step is a product seam, not urbanisation

GLC-FCS30D stitches two production lines together: five-yearly maps for
1985-1995, annual maps from 2000. They do not join. Measured on Lahore District
at 30 m:

| Year | Source | Built-up km² | Change |
|---|---|---|---|
| 1985 | five-yearly | 202 | |
| 1990 | five-yearly | 202 | **+0%** |
| 1995 | five-yearly | 234 | +16% |
| 2000 | **annual** | 389 | **+66%** |
| 2003 | annual | 451 | +7% |
| 2013 | annual | 551 | +8% |
| 2022 | annual | 587 | +6% |

The annual series grows smoothly at 6-9% per interval. The 66% step lands
exactly on the seam, and 1985 equals 1990 to the pixel.

Nationally:

| Comparison | Built-up gain | Growth |
|---|---|---|
| 1995 → 2022 (crosses seam) | 11,946 km² | **+223%** |
| 2000 → 2022 (seam-free) | 3,227 km² | **+23%** |

**About three quarters of the apparent national urban growth is a product
artefact.** The app defaults to the seam-free comparison and labels the others.

### 2. The national net carbon change is not distinguishable from zero

Seam-free, 2000 to 2022:

- gross loss **−151.0 Tg C**
- gross gain **+203.6 Tg C**
- net **+52.5 Tg C**, uncertainty band **−471 to +580 Tg C**

The band is roughly ten times the point estimate and spans zero. These data
cannot say whether Pakistan was a net terrestrial source or sink. The limit is
the carbon densities, not the land-cover map.

### 3. The defensible sub-figure is the built-up conversion

Seam-free, 2000 to 2022:

- vegetated land converted to built-up: **6,357 km²**
- carbon released: **17.3 Tg C** best estimate (band +6.0 to −41.8),
  about **63 Tg CO₂**
- all vegetated land lost to any non-vegetated class: **24,424 km²**,
  **90.9 Tg C**

This is the figure closest to the original question. Its band also crosses zero.

### 4. Vegetation area went up, not down

| Epoch | Built-up km² | Vegetation km² | Carbon Tg C |
|---|---|---|---|
| 1995 | 5,354 | 628,709 | 4,233.9 |
| 2000 | 14,072 | 623,083 | 4,197.7 |
| 2003 | 15,361 | 622,254 | 4,194.5 |
| 2013 | 17,523 | 621,766 | 4,198.5 |
| 2022 | 17,300 | 626,608 | 4,250.2 |

Vegetation gained about 3,500 km² between 2000 and 2022, and built-up fell
slightly between 2013 and 2022. The dominant national flows are a two-way
exchange between bare/sparse and vegetation in the arid zones, which dwarfs
urban conversion. That is partly real (irrigation expansion, rangeland response
to rainfall) and partly classification instability between dry soil and sparse
cover, the same bare-land churn the Lahore project documented.

**The premise that Pakistan lost vegetation nationally is not supported by this
dataset.** Vegetation loss is real and large in specific districts, and
cropland-to-built-up conversion is real everywhere, but nationally both are
outweighed by bare-to-vegetation gain.

### 5. The permanent-ice class is snow, not glaciers

Adding Gilgit-Baltistan brought class 220 into the national picture:

| Year | Ice and snow km² |
|---|---|
| 1995 | 16,506 |
| 2000 | 16,105 |
| 2003 | 17,683 |
| 2013 | 19,875 |
| 2022 | 16,912 |

A 14% swing in nine years is not something permanent ice can do. It is
interannual snowpack and scene timing. It matters for carbon because grassland
scored as turning to ice registers as a total loss, and the reverse as a gain:
about **5% of gross loss** over 2000-2022, **−4.5 Tg C** net. Net flux excluding
it is +57.1 Tg C against +52.5 with it.

**Nothing here is a glacier measurement**, in either direction. The Karakoram
anomaly cannot be investigated with an annual land-cover classification.

## What Azad Kashmir and Gilgit-Baltistan changed

Including them added 9.6% to the national area but **13.7% to the carbon stock**
(3,738 → 4,250 Tg C in 2022), because Azad Kashmir is the densest carbon in the
country.

| Territory | Area km² | Carbon Tg C | Density Mg C/ha |
|---|---|---|---|
| **Azad Kashmir** | 13,419 | 217.0 | **161.7** |
| Khyber Pakhtunkhwa | 75,051 | 702.9 | 93.7 |
| Islamabad Capital Territory | 897 | 7.6 | 85.0 |
| Federally Administered Tribal Areas | 25,628 | 212.9 | 83.1 |
| Punjab | 204,949 | 1,065.9 | 52.0 |
| Sindh | 134,588 | 642.2 | 47.7 |
| **Gilgit-Baltistan** | 64,546 | 301.9 | 46.8 |
| Balochistan | 345,179 | 1,099.7 | 31.9 |

Azad Kashmir is 67% closed forest and carries five times Balochistan's carbon
density. Gilgit-Baltistan is 59% grassland and 21% ice and snow, so its density
is middling despite the high-altitude forest it holds.

## The largest individual conversions, 2000-2022

| From | To | km² | Tg C |
|---|---|---|---|
| Grassland | Bare areas | 4,244 | −17.0 |
| Deciduous shrubland | Unconsolidated bare areas | 2,662 | −10.3 |
| Irrigated cropland | Built-up | 3,737 | −9.9 |
| Grassland | Permanent ice and snow | 1,229 | −6.2 |
| Grassland | Sparse vegetation | 1,944 | −6.1 |
| Marsh | Flooded flat | 692 | −5.2 |
| Deciduous shrubland | Sparse vegetation | 1,521 | −4.8 |
| Deciduous shrubland | Herbaceous cover cropland | 3,516 | −4.8 |

The grassland-to-ice row is the snow artefact from item 5, and appears here only
because Gilgit-Baltistan is now included. It should not be read as land change.

## The correction, measured

The uncorrected single-value table (Vegetation at 150 Mg C/ha) against per-class:

| Comparison | Uncorrected | Corrected |
|---|---|---|
| 1995 → 2022 | −18.8 Tg C | +16.3 Tg C |
| 2000 → 2022 | +46.2 Tg C | +52.5 Tg C |

Over the seam-crossing period the uncorrected table **flips the sign**,
reporting a net loss where per-class accounting reports a net gain. A stronger
version of the Lahore finding, where the same error inflated the loss by 5.9×.

## What would move these numbers

1. **Measured carbon densities for Pakistani land-cover classes.** The dominant
   uncertainty by a wide margin, and the reason the national net has no
   established sign. Azad Kashmir's forest densities matter most per hectare.
2. **An independent accuracy assessment of GLC-FCS30D over Pakistan.**
   Classification error enters the transition matrix as fictitious change; the
   bare/vegetation churn and the snow/ice swing are the visible symptoms.
3. **A consistent pre-2000 baseline**, to recover the first seven years of the
   study period. That needs a classification built on the same footing as the
   annual series.
4. **District boundaries for Azad Kashmir and Gilgit-Baltistan.** geoBoundaries
   gives them none, so each is a single unit with no drill-down.
