# Basin extension process — strict rules

Source: https://github.com/kratzert/Caravan/wiki/Extending-Caravan-with-new-basins
File:   code_to_leverage/instructions to add new basin

These rules MUST be followed exactly when adding new basins to Caravan or when
helping a user extend this dataset. Unit tests in `tests/` verify each rule.

---

## Rule 1 — GEE asset field name must not be a HydroATLAS name

The shapefile uploaded to Google Earth Engine must have a unique basin ID field.
The field name MUST be different from any HydroATLAS / HydroBASINS field.

**Allowed**: `gauge_id`, `basin_id`, or any name not in the reserved list.
**Forbidden**: `HYBAS_ID`, `PFAF_ID`, `NEXT_DOWN`, `UP_AREA`, `SUB_AREA`,
`MAIN_BAS`, `DIST_SINK`, `DIST_MAIN`, `ORDER_`, `SORT_`, `ENDO_`, `COAST_`,
`LAKE_`, `SIDE_`, `system:index`, `.geo`.

Why: The GEE notebook joins user features with HydroATLAS. A name collision
silently overwrites the basin ID with a HydroATLAS integer, producing wrong output.

---

## Rule 2 — Gauge IDs must follow the Caravan two-part format

Every gauge ID must:
- Contain exactly one underscore, splitting into exactly **two** non-empty parts.
- Use a consistent lowercase prefix: `ausvic` for this dataset.
- Be unique across the entire dataset.

**Correct**: `ausvic_230200`
**Wrong**:   `aus_vic_230200` (three parts), `230200` (no prefix), `ausvic_` (empty station)

Why: Reviewer requirement. `gauge_id.split('_')` must return exactly 2 elements
to be compatible with Caravan's merging logic across all subdatasets.

Tests: `test_gauge_id_format` in `tests/test_csv_columns.py`.

---

## Rule 3 — Shapefile DBF must contain ONLY gauge_id

The combined shapefile `ausvic_basin_shapes.shp` must have exactly one DBF column:
`gauge_id`. No other columns are permitted.

Fields computed internally (e.g. `up_area_km2`) must be stripped before writing.

**Correct DBF columns**: `['gauge_id']`
**Wrong**: `['gauge_id', 'area_km2']`, `['GAUGE_ID']`, `[]`

Why: Caravan reviewer requirement (Feb 2026). Extra columns in the DBF are
disallowed; the combined shapefile is for geometry only.

---

## Rule 4 — GeoJSON features must contain ONLY gauge_id

The output GeoJSON `ausvic_basin_shapes.geojson` must have exactly one property
per feature: `{"gauge_id": "ausvic_XXXXXX"}`. No other properties.

Why: Consistency with the shapefile. Internal fields must not leak into outputs.

---

## Rule 5 — ERA5-Land must use the HOURLY GEE collection

`fetch_era5land.py` MUST use `ECMWF/ERA5_LAND/HOURLY`, never `DAILY_AGGR`.

See `.claude/rules/era5land-processing.md` for full details.

---

## Rule 6 — All required output files must exist before submission

The following files must all be present under `caravan_maribyrnong/`:

```
timeseries/csv/ausvic/                          (directory)
timeseries/netcdf/ausvic/                       (directory)
attributes/ausvic/attributes_other_ausvic.csv
attributes/ausvic/attributes_caravan_ausvic.csv
attributes/ausvic/attributes_hydroatlas_ausvic.csv
shapefiles/ausvic/ausvic_basin_shapes.shp
shapefiles/ausvic/ausvic_basin_shapes.shx
shapefiles/ausvic/ausvic_basin_shapes.dbf
shapefiles/ausvic/ausvic_basin_shapes.prj
licenses/ausvic/license_ausvic.md
```

---

## Two-notebook process (must follow in order)

### Notebook 1 — Caravan_part1_Earth_Engine.ipynb (GEE)

1. Prepare a shapefile with basin polygons (one row per gauge).
   - Field name: `gauge_id` (not any HydroATLAS name — see Rule 1).
   - Values: unique, two-part format `ausvic_XXXXXX` (see Rule 2).
   - Upload files: `.shp`, `.dbf`, `.shx`.
2. Upload to GEE: Assets → New → Shape files.
   Note the asset path (e.g. `projects/floodhubmaribyrnong/assets/ausvic_basin_shapes`).
3. Authenticate Google Drive (Colab auth cell → accept all prompts → paste token).
4. Run notebook. Output lands in Google Drive. Download locally.

### Notebook 2 — Caravan_part2_local_postprocessing.ipynb (local)

The notebook processes intermediate GEE outputs into the final Caravan format.

**In this project, Notebook 2 is fully replicated by `fetch_era5land.py`.**
Do NOT run the actual notebook — instead run:

```bash
python fetch_era5land.py
```

The pipeline must follow the exact order in `.claude/rules/era5land-processing.md`.

---

## Pre-submission checklist

Run this before every Zenodo upload:

```bash
python -m pytest tests/ -q           # all tests must pass
```

Then verify manually:
- [ ] `caravan_maribyrnong/` contains no files from old schema
  (delete `era5land_cache_*.json` if ERA5 schema changed; use `era5land_hourly_cache_*.json`)
- [ ] `attributes_hydroatlas_aus_vic.csv` does NOT exist (old filename)
- [ ] No `aus_vic/` directory in output (old prefix)
- [ ] License file references all data sources (Melbourne Water, Victorian WMIS, ERA5-Land, HydroATLAS)

---

## When adding a new gauge

1. Add entry to `gauges_config.py` following the existing structure.
   - `gauge_id`: `ausvic_XXXXXX` format (Rule 2).
   - `area_km2`: set from HydroATLAS `UP_AREA` after running `fetch_hydroatlas_polygon.py`.
2. Run `python fetch_maribyrnong.py` — generates streamflow CSV.
3. Run `python fetch_era5land.py` — merges ERA5-Land (may take minutes per gauge).
4. Run `python compute_attributes.py` — updates climate indices.
5. Run `python fetch_hydroatlas_polygon.py` — updates HydroATLAS attributes.
6. Run `python fetch_catchments.py` — regenerates combined shapefile.
7. Run `python write_netcdf.py` — regenerates all netCDF files.
8. Run `python -m pytest tests/ -q` — all tests must pass.
