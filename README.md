# FloodHubMaribyrnong

Adding Maribyrnong to Google Flood Hub

This project contributes two Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan) — a global community dataset for large-sample hydrology used by Google Flood Hub and hydrological ML research.

---

## Data Pipeline

The scripts run in sequence, each building on the previous:

```
1. fetch_maribyrnong.py   → streamflow timeseries CSVs + attributes_other
2. fetch_silo_met.py      → adds SILO met columns + writes attributes_caravan
3. fetch_era5land.py      → adds ERA5-Land columns (wind, pressure, soil moisture, etc.)
4. fetch_hydroatlas.py    → basin attribute CSVs from GEE
5. fetch_catchments.py    → catchment boundary GeoJSON + ESRI shapefiles
6. write_netcdf.py        → converts CSVs → netCDF4 files (Caravan format)
7. generate_license.py    → writes the required license markdown
```

---

## File-by-File Summary

### `gauges_config.py`
Single source of truth for the two gauges:
- **230200** — Maribyrnong at Keilor (1305 km², data from 1907, Victorian Water WMIS)
- **230106A** — Maribyrnong at Chifley Drive (area unknown/TODO, data from 1996, Melbourne Water API)

All other scripts import `GAUGES` from here. To add a new gauge, only this file needs editing.

### `fetch_maribyrnong.py`
Fetches daily streamflow (ML/day) from two REST APIs:
- **Hydstra** (`data.water.vic.gov.au`) — uses water level → discharge rating table conversion
- **Melbourne Water** (`api.melbournewater.com.au`) — returns `meanRiverFlow` directly

Both fetch year-by-year with exponential retry, filter out bad quality flags (`q==255`) and negatives, convert ML/day → mm/day (dividing by catchment area km²), deduplicate, and write `aus_vic_230200.csv` / `aus_vic_230106.csv` with a single `streamflow` column.

Also writes `attributes_other_aus_vic.csv` with gauge metadata (lat, lon, name, area, streamflow period, missing fraction, source, license).

### `fetch_silo_met.py`
Fetches gridded climate data from the **SILO DataDrill API** (1889–present):
- Variables: `total_precipitation_sum`, `temperature_2m_max/min/mean`, `potential_evaporation_sum` (Morton method), `radiation_mj_m2_d`, `vapour_pressure_hpa`
- Fetches in 10-year chunks, caches raw CSV to disk
- Merges met data into the existing streamflow CSVs (adds 7 new columns)
- Writes `attributes_caravan_aus_vic.csv` with 10 climate stats: `p_mean`, `pet_mean`, `aridity`, `frac_snow`, `moisture_index`, `moisture_index_seasonality`, `high_prec_freq`, `high_prec_dur`, `low_prec_freq`, `low_prec_dur`

Usage:
```
python fetch_silo_met.py --username your@email.com
```

### `fetch_era5land.py`
Fetches the ERA5-Land variables that SILO does not provide, via the **Google Earth Engine Python API** (1981–present):
- Variables (mean/min/max per day): `dewpoint_temperature_2m`, `surface_net_solar_radiation`, `surface_net_thermal_radiation`, `surface_pressure`, `u_component_of_wind_10m`, `v_component_of_wind_10m`, `snow_depth_water_equivalent`, `volumetric_soil_water_layer_1/2/3/4`
- Fetches year-by-year via `getRegion`, aggregates hourly → daily client-side with unit conversions (K→°C, Pa→kPa, m→mm, J/m²→W/m²)
- Caches results to JSON; merges 33 new columns into the existing timeseries CSVs

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
- Converts to **ESRI shapefile** format (`.shp/.dbf/.shx`) via geopandas — required by Caravan

### `write_netcdf.py`
Converts the fully merged CSVs to **CF-1.8 compliant netCDF4** files using `xarray`:
- One `.nc` file per gauge covering all time series variables (streamflow + SILO + ERA5-Land)
- Proper `units`, `long_name`, and `_FillValue` (-9999) metadata on each variable
- Global attributes follow Caravan conventions (gauge metadata, sources, license)
- Loads and merges both `attributes_caravan_aus_vic.csv` and `attributes_other_aus_vic.csv` to populate netCDF global attributes

Must be run after `fetch_maribyrnong.py`, `fetch_silo_met.py`, and `fetch_era5land.py`.

### `generate_license.py`
Writes `license_aus_vic.md` — required by the Caravan contribution process — declaring all data sources (Victorian Water, Melbourne Water, SILO, ERA5-Land, HydroATLAS) and their respective licenses.

---

## Output Structure

```
caravan_maribyrnong/
├── timeseries/
│   ├── csv/aus_vic/
│   │   ├── aus_vic_230200.csv   ← streamflow + SILO + ERA5-Land columns
│   │   └── aus_vic_230106.csv
│   └── netcdf/aus_vic/
│       ├── aus_vic_230200.nc
│       └── aus_vic_230106.nc
├── attributes/
│   ├── attributes_other_aus_vic.csv       ← gauge metadata
│   ├── attributes_caravan_aus_vic.csv     ← climate stats (10 columns)
│   ├── attributes_hydroatlas_aus_vic.csv  ← HydroATLAS basin attributes
│   └── hydroatlas_raw_*.json
├── shapefiles/
│   ├── aus_vic_catchments.geojson
│   ├── aus_vic_catchments.shp  (+ .dbf, .shx, .prj)
│   └── {gauge_id}_catchment.geojson / .shp
├── licenses/aus_vic/license_aus_vic.md
├── silo_cache_*.csv              ← cached SILO downloads
└── era5land_cache_*.json         ← cached ERA5-Land downloads
```

---

## Requirements

```
pip install earthengine-api xarray netCDF4 numpy geopandas
```

For GEE scripts, authenticate once:
```
earthengine authenticate
```

---

## Caravan Compliance

This dataset extension targets full compliance with the [Caravan](https://github.com/kratzert/Caravan) submission standard:

| Requirement | Status |
|---|---|
| `streamflow` column (mm/d) | ✓ |
| SILO met columns (precip, temp, PET, radiation, vapour pressure) | ✓ |
| ERA5-Land columns (dewpoint, wind, pressure, soil moisture, snow, radiation) | ✓ |
| 10 climate stats in `attributes_caravan_aus_vic.csv` | ✓ |
| HydroATLAS attributes in `attributes_hydroatlas_aus_vic.csv` | ✓ |
| Gauge metadata in `attributes_other_aus_vic.csv` | ✓ |
| ESRI shapefile catchment boundaries | ✓ |
| CF-1.8 compliant netCDF4 | ✓ |
| CC-BY-4.0 license file | ✓ |
| Zenodo upload + GitHub issue | manual step |

---

## Key Design Notes

- **`gauges_config.py` as single source of truth** — all scripts import `GAUGES` from it, so adding a new gauge only requires editing one file
- **Year-by-year fetching with retry** — avoids API timeouts on long historical records
- **Caching** — SILO data cached as CSV, ERA5-Land as JSON; delete cache files to force re-download
- **Missing data handling** — gaps are left as empty strings in CSV and as `_FillValue=-9999` in netCDF
- **`area_km2=None` for 230106A** — the Melbourne Water API does not expose catchment area; `fetch_hydroatlas.py` will auto-fill it from HydroATLAS `UP_AREA` when run
