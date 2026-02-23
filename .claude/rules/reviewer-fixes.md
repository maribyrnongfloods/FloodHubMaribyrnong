# Caravan reviewer feedback — required fixes

Source: GitHub issue [kratzert/Caravan#51](https://github.com/kratzert/Caravan/issues/51)
Reviewer: F. Kratzert (maintainer)
Status: **ALL ITEMS OUTSTANDING — must resolve before re-submission**

---

## 1. Gauge ID rename — `aus_vic_XXXXXX` → `ausvic_XXXXXX`

All other Caravan subdatasets use `provider_ID` (two parts only).
`gauge_id.split('_')` must return exactly two parts.

**Affects every file in the dataset:**
- All timeseries CSV filenames: `ausvic_230200.csv`
- All shapefile filenames: `ausvic_230200_catchment.shp` etc.
- `gauge_id` column in all three attributes CSVs
- `gauge_id` global attribute in every netCDF file
- `gauges_config.py` — update `gauge_id` field for all 13 gauges
- Combined shapefile name (see §3 below)

**In `gauges_config.py`:** change e.g. `"aus_vic_230200"` → `"ausvic_230200"` for all 13 gauges.

---

## 2. CAMELS AUS (v2) overlap — RESOLVED

Checked against `CAMELS_AUS_Attributes&Indices_MasterTable.csv` (Zenodo 13350616).
Three of our gauges are already in Caravan via CAMELS AUS v2:

| Station | Name | CAMELS AUS period | Our fetch_start | Decision |
|---------|------|-------------------|-----------------|----------|
| 230210 | Bullengarook | 1968-05-10 – 2022-02-28 | 1970 | **REMOVED** — CAMELS has earlier start |
| 230205 | Deep Creek, Bulla | 1955-06-22 – 2022-02-28 | 1960 | **REMOVED** — CAMELS has earlier start |
| 230209 | Barringo | 1966-06-17 – 2020-02-29 | 1970 | **REMOVED** — CAMELS has earlier start |

`gauges_config.py` updated. **Extension is now 10 gauges.**

---

## 3. Shapefiles — single combined file, no individual files

**Required structure:**
```
shapefiles/ausvic/
    ausvic_basin_shapes.shp   ← single file, all basins
    ausvic_basin_shapes.shx
    ausvic_basin_shapes.dbf
    ausvic_basin_shapes.prj
    ausvic_basin_shapes.cpg
```

- **Remove** all individual per-gauge shapefiles (`ausvic_230200_catchment.shp` etc.)
- Only mandatory DBF column: `gauge_id`
- Remove `hybas_id_outlet`, `up_area_km2`, `num_level12` from DBF (not Caravan standard)
- Projection: WGS 84 (EPSG:4326) — unchanged

Update `fetch_catchments.py` to write only the combined shapefile.

---

## 4. HydroATLAS attributes — re-derive using official Caravan notebook

Our `fetch_hydroatlas.py` produced more columns than the Caravan standard.

**Required action:**
1. Open the official notebook: https://github.com/kratzert/Caravan/blob/main/code/Caravan_part1_Earth_Engine.ipynb
2. Run it from Google Colab (takes < 5 minutes per the reviewer).
3. Replace `attributes_hydroatlas_ausvic.csv` with the output of that notebook.
4. Delete `fetch_hydroatlas.py` (our custom implementation) — it produced non-standard columns.

The notebook produces exactly the 294 HydroATLAS columns that all other Caravan subdatasets have.

---

## 5. Duplicate HydroATLAS file — remove from root

`attributes_hydroatlas_aus_vic.csv` exists in two places:
- `attributes/aus_vic/attributes_hydroatlas_aus_vic.csv` ✓ (keep, renamed)
- `attributes/attributes_hydroatlas_aus_vic.csv` ✗ **delete this one**

---

## 6. `attributes_other` — split extra columns into `attributes_additional`

`attributes_other_ausvic.csv` currently has more columns than the Caravan standard.

**Standard columns to keep in `attributes_other_ausvic.csv`:**
`gauge_id`, `gauge_name`, `gauge_lat`, `gauge_lon`, `country`, `basin_name`,
`area`, `unit_area`, `streamflow_period`, `streamflow_missing`, `streamflow_units`,
`source`, `license`, `note`

**All extra columns** (anything beyond the above) go into a new file:
```
attributes/ausvic/attributes_additional_ausvic.csv
```
with `gauge_id` as the key column.

---

## 7. SILO columns — REMOVE entirely

SILO is an Australian-only product. Caravan requires globally available data only.

**Remove these 7 columns from all timeseries CSVs and netCDF files:**
- `total_precipitation_sum`
- `temperature_2m_max`
- `temperature_2m_min`
- `temperature_2m_mean`
- `potential_evaporation_sum`
- `radiation_mj_m2_d`
- `vapour_pressure_hpa`

After removal the CSV has **35 columns**: `date` + `streamflow` + 33 ERA5-Land.

**Delete `fetch_silo_met.py`** — no longer needed.
Update `write_netcdf.py` to drop SILO variables.
Update `tests/test_pipeline.py` — column count changes from 42 → 35.

---

## 8. Timeseries — ERA5-Land for full period, not just streamflow overlap

All gauges must have ERA5-Land forcings for the **full ERA5-Land period (1950-01-01 onward)**, regardless of when streamflow records begin.

For Keilor (230200, records from 1908):
- Rows before 1950-01-01: `streamflow` value present, all ERA5-Land columns = empty string (CSV) / -9999 (netCDF)
- Rows 1950-01-01 onward: both streamflow and ERA5-Land populated where available

**Do NOT include SILO data before 1950** — that was filling ERA5-Land gaps with SILO, which is no longer permitted (see §7).

Update `fetch_era5land.py` to always start from `date(1950, 1, 1)` regardless of gauge `fetch_start`.

---

## 9. Updated caravan-standard.md corrections

After these fixes the timeseries CSV has **35 columns** (not 42):
- `date`
- `streamflow`
- 33 ERA5-Land columns (mean/min/max for 11 variables)

SILO section of `caravan-standard.md` is now void for this extension.

---

## Summary checklist

- [ ] Cross-check CAMELS AUS v2 overlap; remove duplicate gauges
- [ ] Rename all `aus_vic_` → `ausvic_` in `gauges_config.py` + all output files
- [ ] Re-run HydroATLAS via official Colab notebook
- [ ] Delete duplicate `attributes/attributes_hydroatlas_aus_vic.csv`
- [ ] Split `attributes_other` extra columns into `attributes_additional_ausvic.csv`
- [ ] Remove all SILO columns from CSVs and netCDF; delete `fetch_silo_met.py`
- [ ] Fix ERA5-Land fetch to start 1950 for all gauges
- [ ] Rebuild combined shapefile as `ausvic_basin_shapes.shp`; remove individual shapefiles
- [ ] Re-run `write_netcdf.py` with updated schema
- [ ] Update `tests/test_pipeline.py` (column count 42 → 35, new gauge IDs)
- [ ] Re-upload to Zenodo (new version), post updated DOI to GitHub issue
