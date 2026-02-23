# Pipeline, workflow and testing rules

## Data pipeline (run in order)

```
1. python fetch_maribyrnong.py
         → timeseries/csv/ausvic/*.csv  (streamflow only)
         → attributes/ausvic/attributes_other_ausvic.csv

2. python fetch_era5land.py
         → merges 39 ERA5-Land cols into each timeseries CSV
         → computes FAO-56 PM PET inline
         → delete era5land_cache_*.json first if ERA5 schema has changed

3. python compute_attributes.py
         → attributes/ausvic/attributes_caravan_ausvic.csv
         → climate indices over 1981-01-01 to 2020-12-31

4. [Caravan Part-1 Colab notebook]    ← MANUAL STEP
         → https://github.com/kratzert/Caravan/blob/main/code/Caravan_part1_Earth_Engine.ipynb
         → produces attributes/ausvic/attributes_hydroatlas_ausvic.csv  (294 standard columns)
         → also produces area_km2 for each basin

5. python fetch_catchments.py
         → shapefiles/ausvic/ausvic_basin_shapes.shp  (single file, gauge_id only)
         → shapefiles/ausvic/ausvic_basin_shapes.geojson

6. python write_netcdf.py
         → timeseries/netcdf/ausvic/ausvic_XXXXXX.nc  (CF-1.8, 41 cols)

7. python generate_license.py
         → licenses/ausvic/license_ausvic.md

8. python make_map.py
         → gauge_map.png
```

NOTE: `fetch_silo_met.py` has been removed. SILO is not globally available
and must not be included in Caravan (reviewer feedback Feb 2026).

NOTE: `fetch_hydroatlas.py` (our custom script) produces non-standard columns.
Use the official Caravan Part-1 Colab notebook instead:
  https://github.com/kratzert/Caravan/blob/main/code/Caravan_part1_Earth_Engine.ipynb

GEE project: `floodhubmaribyrnong`

GEE one-off setup:
```python
import ee
ee.Authenticate()
ee.Initialize(project='floodhubmaribyrnong')
```

## Git branches

- `main` — stable, mirrors latest release
- `dev`  — active development (default working branch)

Always work on `dev`. To publish: push `dev`, merge to `main`, push `main`.

```bash
git push upstream dev
git checkout main && git merge dev --no-edit
git push upstream main
git checkout dev
```

## Tests

```bash
python -m pytest tests/ -q     # unit tests, no network (26 tests)
python test_run.py             # live API smoke test (Hydstra + Melbourne Water)
```

Tests run automatically on every `git commit` via pre-commit hook.
Never use `--no-verify` to skip the hook.

## Caravan compliance checklist (status: Feb 2026)

- [x] `streamflow` column in mm/day
- [x] ERA5-Land 39 columns (date + streamflow + 39 = 41 total)
      temperature_2m ×3, dewpoint_2m ×3, surface_pressure ×3,
      u/v wind 10m ×3 each, snow_depth_we ×3, soil_water_1-4 ×3 each,
      surface_net_solar_rad ×3, surface_net_thermal_rad ×3,
      total_precipitation_sum, potential_evaporation_sum_ERA5_LAND,
      potential_evaporation_sum_FAO_PENMAN_MONTEITH
- [x] `attributes_caravan_ausvic.csv` — computed from ERA5-Land via compute_attributes.py
- [ ] `attributes_hydroatlas_ausvic.csv` — must re-derive via Caravan Part-1 Colab notebook
- [x] `attributes_other_ausvic.csv` — exactly 14 standard columns (no extras)
- [x] `ausvic_basin_shapes.shp` (single combined, gauge_id column only)
- [x] CF-1.8 compliant netCDF4 (41 cols, float32, _FillValue=-9999)
- [x] CC-BY-4.0 license file (`licenses/ausvic/license_ausvic.md`)
- [x] 10 gauges (3 CAMELS AUS v2 duplicates removed: 230205, 230209, 230210)
- [x] All gauge IDs use `ausvic_XXXXXX` format (two-part, splits on `_` to exactly 2)
- [ ] Delete `caravan_maribyrnong/attributes/attributes_hydroatlas_aus_vic.csv` if present
- [ ] Re-run full pipeline with new 41-col ERA5 schema
- [ ] Zenodo re-upload with new version
- [ ] Update GitHub issue kratzert/Caravan#51 with new DOI
