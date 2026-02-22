# FloodHubMaribyrnong

Adding Maribyrnong to Google Flood Hub

This project contributes two Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan) — a global community dataset for large-sample hydrology used by Google Flood Hub and hydrological ML research.

---

## Data Pipeline

The scripts run in sequence, each building on the previous:

```
1. fetch_maribyrnong.py   → streamflow timeseries CSVs
2. fetch_silo_met.py      → adds meteorological columns to those CSVs
3. fetch_hydroatlas.py    → basin attribute CSVs from GEE
4. fetch_catchments.py    → catchment boundary GeoJSON shapefiles
5. write_netcdf.py        → converts CSVs → netCDF4 files (Caravan format)
6. generate_license.py    → writes the required license markdown
```

---

## File-by-File Summary

### `gauges_config.py`
Single source of truth for the two gauges:
- **230200** — Maribyrnong at Keilor (1305 km², data from 1907, Victorian Water WMIS)
- **230106A** — Maribyrnong at Chifley Drive (area unknown/TODO, data from 1996, Melbourne Water API)

### `fetch_maribyrnong.py`
Fetches daily streamflow (ML/day) from two REST APIs:
- **Hydstra** (`data.water.vic.gov.au`) — uses water level → discharge rating table conversion
- **Melbourne Water** (`api.melbournewater.com.au`) — returns `meanRiverFlow` directly

Both fetch year-by-year with exponential retry, filter out bad quality flags (`q==255`) and negatives, convert ML/day → mm/day (dividing by catchment area km²), deduplicate, and write `aus_vic_230200.csv` / `aus_vic_230106.csv`.

Also writes a combined `attributes_caravan_aus_vic.csv` with metadata including `streamflow_period`, `streamflow_missing`, source, and license.

### `fetch_silo_met.py`
Fetches gridded climate data from the **SILO DataDrill API** (1889–present):
- Variables: precipitation, Tmax, Tmin, Morton PET, solar radiation, vapour pressure
- Fetches in 10-year chunks, caches raw CSV to disk
- Merges met data into the existing streamflow CSVs (adds 7 new columns)
- Computes and writes climate stats back to the attributes CSV: `p_mean`, `pet_mean`, `aridity` (PET/P), `high_prec_freq` (>5×mean), `low_prec_freq` (<1 mm/d), `frac_snow` (hardcoded 0 — Victoria has no meaningful snow)

Usage:
```
python fetch_silo_met.py --username your@email.com
```

### `fetch_hydroatlas.py`
Uses the **Google Earth Engine Python API** to query the WWF HydroATLAS BasinATLAS Level-12 dataset:
- Finds the level-12 basin polygon containing each gauge point
- Extracts all ~100+ basin attributes (geology, land cover, climate indices, etc.)
- Writes `attributes_hydroatlas_aus_vic.csv`
- Auto-backfills `area_km2=None` in `gauges_config.py` using `UP_AREA` from HydroATLAS
- Includes a geopandas-based fallback if you prefer not to use GEE

### `fetch_catchments.py`
Also uses GEE, but derives the full **upstream catchment polygon**:
- Finds the outlet HydroBASINS Level-12 cell
- Iteratively traverses upstream via `NEXT_DOWN` links (BFS graph walk)
- Unions all upstream cells into one polygon (30 m tolerance)
- Saves individual `{gauge_id}_catchment.geojson` + combined `aus_vic_catchments.geojson`
- These shapefiles are uploaded to GEE as assets for ERA5-Land spatial averaging

### `write_netcdf.py`
Converts the merged CSVs to **CF-1.8 compliant netCDF4** files using `xarray`:
- One `.nc` file per gauge with all time series variables
- Proper `units`, `long_name`, and `_FillValue` (-9999) metadata on each variable
- Global attributes follow Caravan conventions (gauge metadata, sources, license)
- Merges `p_mean`, `pet_mean`, `aridity` from the attributes CSV into the netCDF global attrs

### `generate_license.py`
Writes `license_aus_vic.md` — required by the Caravan contribution process — declaring all data sources and their CC-BY-4.0 licenses.

---

## Output Structure

```
caravan_maribyrnong/
├── timeseries/
│   ├── csv/aus_vic/
│   │   ├── aus_vic_230200.csv   ← streamflow + met columns
│   │   └── aus_vic_230106.csv
│   └── netcdf/aus_vic/
│       ├── aus_vic_230200.nc
│       └── aus_vic_230106.nc
├── attributes/
│   ├── attributes_caravan_aus_vic.csv
│   ├── attributes_hydroatlas_aus_vic.csv
│   └── hydroatlas_raw_*.json
├── shapefiles/
│   ├── aus_vic_catchments.geojson
│   └── {gauge_id}_catchment.geojson
├── licenses/aus_vic/license_aus_vic.md
└── silo_cache_*.csv              ← cached SILO downloads
```

---

## Requirements

```
pip install earthengine-api xarray netCDF4 numpy
```

For GEE scripts, authenticate once:
```
earthengine authenticate
```

---

## Key Design Notes

- **`gauges_config.py` as single source of truth** — all scripts import `GAUGES` from it, so adding a new gauge only requires editing one file
- **Year-by-year fetching with retry** — avoids API timeouts on long historical records
- **Missing data handling** — gaps are left as empty strings in CSV (Caravan convention) and as `_FillValue=-9999` in netCDF
- **`area_km2=None` for 230106A** — the Melbourne Water API does not expose catchment area; HydroATLAS auto-fill or manual lookup is required before the flow unit conversion can run for that gauge
