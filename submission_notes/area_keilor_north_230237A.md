# Catchment Area — ausvic_230237 (Maribyrnong River at Keilor North)

**Issue:** HydroATLAS Level-12 resolution is insufficient to assign a distinct
catchment area to this gauge.

## What happened

`fetch_hydroatlas_polygon.py` traces upstream through HydroBASINS Level-12 basins
from the gauge's nearest outlet point. For ausvic_230237 (Keilor North, lat −37.6778),
the nearest outlet is **HYBAS_ID 5120612070** — the same outlet resolved by both
ausvic_230200 (Keilor, −37.7277) and ausvic_230106 (Chifley Drive, −37.7659).

All three lower mainstem gauges therefore receive the same upstream basin polygon
and the same derived area:

| gauge_id       | Station  | HydroATLAS area | Notes                          |
|----------------|----------|----------------:|--------------------------------|
| ausvic_230237  | 230237A  | 1413.8 km²      | ← same as full catchment       |
| ausvic_230200  | 230200   | 1413.8 km²      | official figure used: 1305.4   |
| ausvic_230106  | 230106A  | 1413.8 km²      | accepted (lowest gauge)        |

## Consequence

Catchment area is the sole divisor in the ML/day → mm/day conversion:

    streamflow_mm = ML_per_day / area_km2

Using 1413.8 km² when the true area is smaller (likely 900–1200 km²) causes
a **systematic underestimate of streamflow in mm/day** for every day on record:

| True area (estimate) | mm/day error |
|----------------------|--------------|
| 1200 km²             | −15 %        |
| 1100 km²             | −22 %        |
|  900 km²             | −36 %        |

ERA5-Land climate indices are unaffected (computed from gridded forcing, not gauge area).

## Current status

`gauges_config.py` uses `area_km2 = 1413.8` with an inline comment explaining the
Level-12 limitation. The `notes` field in `attributes_other_ausvic.csv` will carry
the same caveat.

## Resolution options

1. **Melbourne Water official figure** — MW publishes catchment areas for some
   gauges. Query the MW website or API for station 230237A; if an official km²
   figure is available, override HydroATLAS (same approach used for ausvic_230200
   which uses the Victorian Water official figure of 1305.4 km²).

2. **HydroSHEDS Level-08 or finer** — a coarser DEM-based delineation at a finer
   level might resolve the three gauges separately, but this is non-standard for
   Caravan and would require manual verification.

3. **Accept 1413.8 km² and document** — defensible if disclosed clearly in
   submission notes and the `note` field of `attributes_other_ausvic.csv`.

## Action needed before Zenodo upload

Check whether Melbourne Water or the Victorian Water Register publishes an official
catchment area for station 230237A (Maribyrnong River d/s Jacksons Creek, Keilor
North / Sydenham Park). If found, update `gauges_config.py` and re-run the pipeline.
