# Task: Fix Lower-Mainstem Gauge Catchment Areas

## Problem
Three gauges (230237A Keilor North, 230200 Keilor, 230106A Chifley Drive) all snap
to the same HydroBASINS Level-12 cell (UP_AREA=1413.6 km²). Keilor North is currently
using the wrong area → streamflow mm/day values are 20-50% too low.

## Plan reference
`C:\Users\leela\.claude\plans\fuzzy-riding-music.md`

## Checklist

- [ ] **Step 1** — Create `fetch_merit_areas.py` (GEE MERIT Hydro upa pixel lookup)
- [ ] **Step 2** — Run `fetch_merit_areas.py` in GEE and record results here
- [ ] **Step 3** — Update `gauges_config.py` with MERIT-derived areas
- [ ] **Step 4** — Update `notebooks/0b-fetch_catchments_ausvic.ipynb`:
  - [ ] Add detection logic for shared-cell gauges
  - [ ] Add HydroSHEDS 03DIR raster delineation fallback (or document limitation)
- [ ] **Step 5** — Re-run pipeline for affected gauges:
  - [ ] `python fetch_maribyrnong.py`
  - [ ] `python fetch_era5land.py`
  - [ ] `python compute_attributes.py`
  - [ ] `python write_netcdf.py`
- [ ] **Step 6** — Update `CLAUDE.md` gauge count: 10 → 12
- [ ] **Step 7** — Validate:
  - [ ] `python validate_submission.py` — all checks pass
  - [ ] `python -m pytest tests/ -q` — all tests pass
  - [ ] Confirm ausvic_230237 area < 1305.4 km²
  - [ ] Confirm ausvic_230106 area ≥ 1305.4 km²
  - [ ] Confirm all three have distinct area values

## MERIT Hydro results (Feb 2026)

| gauge_id | old_area | merit_area | new_area | action |
|----------|----------|------------|----------|--------|
| ausvic_230237 | 1413.6 | 1278.1 | **1278.1** | updated |
| ausvic_230200 | 1305.4 | 1328.3 | **1305.4** | kept official |
| ausvic_230106 | 1413.6 | 1385.0 | **1385.0** | updated |

Sanity order: 1278.1 < 1305.4 < 1385.0 ✓

## Review

**Completed (Feb 2026)**
- Created `fetch_merit_areas.py` to query MERIT Hydro `upa` band via GEE
- Updated `gauges_config.py`: ausvic_230237 → 1278.1 km2, ausvic_230106 → 1385.0 km2
- CLAUDE.md updated: gauge count 10 → 12, area source notes updated
- 125/125 tests pass
- Notebook 0b polygon fix: deferred — area correction is the highest-impact fix;
  polygon shared-cell limitation documented in gauges_config.py notes

**Caravan compliance fixes (Feb 2026)**
- `generate_license.py`: gauge count 10 → 12; tables updated (removed 230104A, added 230119A, 230102A, 230237A); ERA5 URL changed from DAILY_AGGR → HOURLY
- `fetch_era5land.py`: `_UNIT_CONVERTERS` PET entry corrected (`* -1000.0` → `* 1000.0`; sign flip is a separate step 1)
- `fetch_hydroatlas_polygon.py`: `area` and `area_fraction_used_for_aggregation` now excluded from CSV output (internal fields, not HydroATLAS attributes)
- `verify_hydroatlas.py`: MUST_BE_PRESENT → MUST_BE_ABSENT_INTERNAL; count expectation ~198 → ~196
- `tests/test_pipeline.py`: renamed `test_all_10_config_gauges_are_valid` → `test_all_12_config_gauges_are_valid`
- 125/125 tests pass

**Completed (Feb 2026 — this session)**
- Notebook 0a re-run in GEE, output verified: ausvic_230237=1278.1, ausvic_230106=1385.0, ausvic_230200=1305.4 ✓
- KNOWN_AREAS fallback added: ausvic_230213=109.8 km² (HydroBASINS L12), ausvic_230227=177.8 km² (MERIT off-network) ✓
- Before/after comparison cells added + headwater fallback cells + static catchment map ✓
- Notebook 0a output validated: ordering check passes, all 12 gauges correct ✓
- gauges_ausvic.json saved to Google Drive with all 12 correct areas ✓

**Remaining manual action**
- [ ] Run notebook 0b in Colab to regenerate catchment shapefiles using updated gauges_ausvic.json
- [ ] Re-run archive pipeline (from archive/ dir) for all 12 gauges:
    cd archive && python fetch_maribyrnong.py
    python fetch_era5land.py     # delete era5land_hourly_cache_*.json for affected gauges first
    python compute_attributes.py
    python write_netcdf.py
    python validate_submission.py
    python -m pytest tests/ -q   # 125 tests must pass
- [ ] Commit notebook 0a changes (git add notebooks/0a-derive_gauge_config_ausvic.ipynb)
- [ ] Upload regenerated caravan_maribyrnong/ to Zenodo (new version)
- [ ] Post updated DOI to GitHub issue kratzert/Caravan#51
