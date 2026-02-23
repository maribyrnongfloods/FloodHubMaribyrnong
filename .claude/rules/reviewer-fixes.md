# Caravan reviewer feedback — required fixes

Source: GitHub issue [kratzert/Caravan#51](https://github.com/kratzert/Caravan/issues/51)
Reviewer: F. Kratzert (maintainer)

---

## 1. Gauge ID rename — `aus_vic_XXXXXX` → `ausvic_XXXXXX` — ✅ DONE

All other Caravan subdatasets use `provider_ID` (two parts only).
`gauge_id.split('_')` must return exactly two parts.

**Completed:** All gauge IDs in `gauges_config.py` changed to `ausvic_XXXXXX`.
All output paths, script references, attribute CSV names, and netCDF global
attributes use `ausvic` prefix. Tests verify format.

---

## 2. CAMELS AUS (v2) overlap — ✅ DONE

Checked against `CAMELS_AUS_Attributes&Indices_MasterTable.csv` (Zenodo 13350616).
Three of our gauges are already in Caravan via CAMELS AUS v2:

| Station | Name | CAMELS AUS period | Our fetch_start | Decision |
|---------|------|-------------------|-----------------|----------|
| 230210 | Bullengarook | 1968-05-10 – 2022-02-28 | 1970 | **REMOVED** |
| 230205 | Deep Creek, Bulla | 1955-06-22 – 2022-02-28 | 1960 | **REMOVED** |
| 230209 | Barringo | 1966-06-17 – 2020-02-29 | 1970 | **REMOVED** |

`gauges_config.py` updated. **Extension is now 10 gauges.**
Test `TestGaugeConfig::test_gauge_count` verifies exactly 10 gauges.
Test `TestGaugeConfig::test_excluded_gauges_absent` verifies the 3 stations are absent.

---

## 3. Shapefiles — single combined file, no individual files — ✅ DONE

`fetch_catchments.py` updated to write only:
```
shapefiles/ausvic/
    ausvic_basin_shapes.shp   ← single file, gauge_id column only
    ausvic_basin_shapes.shx
    ausvic_basin_shapes.dbf
    ausvic_basin_shapes.prj
    ausvic_basin_shapes.cpg
```
Individual per-gauge shapefiles are NOT written.
DBF contains only `gauge_id` (no extra columns).

---

## 4. Use official Caravan code — ✅ DONE (ERA5-Land + PET + climate indices)

**What was done:**
- `fetch_era5land.py` now fetches `temperature_2m`, `total_precipitation`,
  and `potential_evaporation` from ERA5-Land DAILY_AGGR (matching the Caravan
  standard variable set).
- FAO-56 Penman-Monteith PET computed inline via `_fao_pm_pet_scalar()`,
  faithfully implementing the formula from
  [pet.py](https://github.com/kratzert/Caravan/blob/main/code/pet.py).
- `compute_attributes.py` (new) implements `calculate_climate_indices()` from
  [caravan_utils.py](https://github.com/kratzert/Caravan/blob/main/code/caravan_utils.py)
  over the standard period 1981-01-01 to 2020-12-31.

**HydroATLAS — ⚠️ STILL REQUIRES MANUAL ACTION:**
Our `fetch_hydroatlas.py` custom script produces more columns than the
standard. The official Caravan Part-1 Colab notebook must be used:

1. Open: https://github.com/kratzert/Caravan/blob/main/code/Caravan_part1_Earth_Engine.ipynb
2. Run from Google Colab (< 5 minutes per reviewer).
3. Replace `caravan_maribyrnong/attributes/ausvic/attributes_hydroatlas_ausvic.csv`
   with the notebook output. Notebook produces exactly 294 standard columns.

---

## 5. Duplicate HydroATLAS file — delete from root — ⚠️ MANUAL ACTION NEEDED

If you have run `fetch_hydroatlas.py` from a previous version, this file
may exist:
```
caravan_maribyrnong/attributes/attributes_hydroatlas_aus_vic.csv   ← DELETE
```
It is not created by the current code (paths were updated to `ausvic`).
Delete it manually if present in your `caravan_maribyrnong/` output folder.

---

## 6. `attributes_other` — NO ACTION NEEDED

`attributes_other_ausvic.csv` produced by `fetch_maribyrnong.py` has exactly
the 14 standard Caravan columns:
```
gauge_id, gauge_name, gauge_lat, gauge_lon, country, basin_name,
area, unit_area, streamflow_period, streamflow_missing, streamflow_units,
source, license, note
```
No extra columns are present, so no `attributes_additional_ausvic.csv` is needed.

---

## 7. SILO columns — ✅ DONE

SILO is Australian-only; Caravan requires globally available data.

**Completed:**
- All SILO columns removed from `write_netcdf.py` VAR_META
- `fetch_silo_met.py` replaced with an informative `ImportError` placeholder
- Note: `temperature_2m_mean/min/max` and `total_precipitation_sum` were originally
  SILO columns but are now **re-added as legitimate ERA5-Land columns** (see §4).
- The old "35 columns" figure is now **41 columns**:
  `date` + `streamflow` + 39 ERA5-Land (see caravan-standard.md)

---

## 8. ERA5-Land for full period — ✅ DONE

`fetch_era5land.py` builds a 1950-to-present date spine. Pre-1950 streamflow
rows (e.g. Keilor 1908–1949) are prepended with empty ERA5 columns.
No SILO data is used to fill ERA5 gaps.

---

## Summary checklist

- [x] Cross-check CAMELS AUS v2 overlap; remove duplicate gauges (10 remain)
- [x] Rename all `aus_vic_` → `ausvic_` in `gauges_config.py` + all scripts
- [x] Shapefiles: single `ausvic_basin_shapes.shp`, `gauge_id` only, no individual files
- [x] SILO columns removed; `fetch_silo_met.py` deprecated
- [x] ERA5-Land fetch starts 1950; pre-1950 rows have empty ERA5 cols
- [x] `temperature_2m`, `total_precipitation_sum`, `potential_evaporation` added as ERA5-Land cols
- [x] FAO-56 PM PET computed inline from ERA5-Land inputs (per Caravan pet.py)
- [x] `compute_attributes.py` — official climate indices 1981-2020 (per Caravan caravan_utils.py)
- [x] `attributes_other_ausvic.csv` has exactly 14 standard columns; no extras
- [x] 26/26 unit tests pass
- [ ] **Re-derive HydroATLAS via official Caravan Part-1 Colab notebook** (< 5 min)
- [ ] **Delete** `caravan_maribyrnong/attributes/attributes_hydroatlas_aus_vic.csv` if present
- [ ] **Re-run full pipeline** with new ERA5 schema (delete era5land_cache_*.json first)
- [ ] **Re-upload to Zenodo** (new version), post updated DOI to GitHub issue #51
