# FloodHubMaribyrnong

Contributing Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan) — a global community dataset for large-sample hydrology used by Google Flood Hub and hydrological ML research.

**Dataset DOI:** [10.5281/zenodo.18736844](https://doi.org/10.5281/zenodo.18736844)

---

## Gauge Network (13 stations)

### Maribyrnong mainstem — Melbourne Water API

| Station | Name | Area (km²) | Streamflow period |
|---------|------|-----------|-------------------|
| 230100A | Maribyrnong River at Darraweit | 682.7 | 2004-01-01 – 2025-12-29 |
| 230211A | Maribyrnong River at Clarkefield | 177.9 | 2008-08-09 – 2026-01-15 |
| 230104A | Maribyrnong River at Sunbury | 406.7 | 2004-01-01 – 2026-02-22 |
| 230107A | Konagaderra Creek at Konagaderra | 682.7 | 2004-01-01 – 2025-12-14 |
| 230200 | Maribyrnong River at Keilor | 1305.4 | 1908-02-02 – 2026-02-21 |
| 230106A | Maribyrnong River at Chifley Drive* | 1413.6 | 2004-06-19 – 2026-01-13 |

### Tributaries — Victorian Water / Hydstra API

| Station | Name | Area (km²) | Streamflow period |
|---------|------|-----------|-------------------|
| 230210 | Jacksons Creek at Bullengarook | 154.1 | 1970-01-01 – 2026-02-21 |
| 230206 | Jackson Creek at Gisborne | 154.1 | 1960-05-10 – 2026-02-21 |
| 230202 | Jackson Creek at Sunbury | 406.7 | 1960-01-01 – 2026-02-21 |
| 230205 | Deep Creek at Bulla | 876.1 | 1960-01-01 – 2026-02-21 |
| 230209 | Barringo Creek at Barringo | 109.9 | 1970-01-01 – 2026-02-21 |
| 230213 | Turritable Creek at Mount Macedon | 109.9 | 1980-01-01 – 2026-02-21 |
| 230227 | Main Creek at Kerrie | 177.9 | 1990-01-01 – 2026-02-21 |

*Chifley Drive is in the tidal zone — flow is only reliable during high-flow events (>16,520 ML/day).

Catchment areas for all stations come from HydroATLAS `UP_AREA` (auto-filled by `fetch_hydroatlas.py`), except Keilor (230200) which uses the official Victorian Water figure of 1305.4 km².

---

## Data Pipeline

Run the scripts in sequence, each building on the previous:

```
1. fetch_maribyrnong.py   → streamflow timeseries CSVs + attributes_other
2. fetch_silo_met.py      → adds SILO met columns + writes attributes_caravan
3. fetch_era5land.py      → adds ERA5-Land columns (wind, pressure, soil moisture, etc.)
4. fetch_hydroatlas.py    → basin attribute CSVs from GEE
5. fetch_catchments.py    → catchment boundary GeoJSON + ESRI shapefiles
6. write_netcdf.py        → converts CSVs -> netCDF4 files (Caravan format)
7. generate_license.py    → writes the required license markdown
```

---

## Dataset Coverage

Status after full pipeline run (2026-02-23), ERA5-Land fetched from 1950:

| # | Station | Name | Streamflow | Flow days | ERA5-Land | ERA5 days |
|---|---------|------|-----------|----------:|-----------|----------:|
|  1 | 230100A | Maribyrnong River at Darraweit      | 2004-01-01 – 2025-12-29 |  5,487 | 2004-01-01 – 2025-12-29 |  5,487 |
|  2 | 230211A | Maribyrnong River at Clarkefield    | 2008-08-09 – 2026-01-15 |  4,618 | 2008-08-09 – 2026-01-15 |  4,618 |
|  3 | 230104A | Maribyrnong River at Sunbury        | 2004-01-01 – 2026-02-22 |  7,558 | 2004-01-01 – 2026-02-15 |  7,551 |
|  4 | 230107A | Konagaderra Creek at Konagaderra    | 2004-01-01 – 2025-12-14 |  4,272 | 2004-01-01 – 2025-12-14 |  4,272 |
|  5 | 230200  | Maribyrnong River at Keilor         | 1908-02-02 – 2026-02-21 | 36,484 | 1950-01-02 – 2026-02-15 | 27,804 |
|  6 | 230106A | Maribyrnong River at Chifley Drive  | 2004-06-19 – 2026-01-13 |    263 | 2004-06-19 – 2026-01-13 |    263 |
|  7 | 230210  | Jacksons Creek at Bullengarook      | 1970-01-01 – 2026-02-21 | 20,506 | 1950-01-02 – 2026-02-15 | 27,804 |
|  8 | 230206  | Jackson Creek at Gisborne           | 1960-05-10 – 2026-02-21 | 24,029 | 1950-01-02 – 2026-02-15 | 27,804 |
|  9 | 230202  | Jackson Creek at Sunbury            | 1960-01-01 – 2026-02-21 | 24,159 | 1950-01-02 – 2026-02-15 | 27,804 |
| 10 | 230205  | Deep Creek at Bulla                 | 1960-01-01 – 2026-02-21 | 24,159 | 1950-01-02 – 2026-02-15 | 27,804 |
| 11 | 230209  | Barringo Creek at Barringo          | 1970-01-01 – 2026-02-21 | 20,506 | 1950-01-02 – 2026-02-15 | 27,804 |
| 12 | 230213  | Turritable Creek at Mount Macedon   | 1980-01-01 – 2026-02-21 | 16,854 | 1950-01-02 – 2026-02-15 | 27,804 |
| 13 | 230227  | Main Creek at Kerrie                | 1990-01-01 – 2026-02-21 | 10,596 | 1990-01-01 – 2026-02-15 | 10,590 |

Notes:
- ERA5-Land fetched from 1950 (dataset start) for all gauges. Pre-1950 flow (Keilor 1908–1949) has no ERA5-Land equivalent — no reanalysis exists for that period.
- Chifley Drive (230106A) has sparse flow records — tidal station, data only during major flood events.
- ERA5-Land end dates lag streamflow by ~1 week due to the GEE `DAILY_AGGR` publication delay.

---

## File-by-File Summary

### `gauges_config.py`
Single source of truth for all 13 gauges. All other scripts import `GAUGES` from here. To add a new gauge, only this file needs editing. Catchment areas are auto-filled by `fetch_hydroatlas.py` and committed back into this file.

### `fetch_maribyrnong.py`
Fetches daily streamflow (ML/day) from two REST APIs:
- **Hydstra** (`data.water.vic.gov.au`) — uses water level -> discharge rating table conversion (`varfrom=100.00`, `varto=141.00`)
- **Melbourne Water** (`api.melbournewater.com.au`) — returns `meanRiverFlow` directly

Both fetch year-by-year with exponential retry, filter out bad quality flags (`q==255`) and negatives, convert ML/day -> mm/day (dividing by catchment area km²), deduplicate, and write one `aus_vic_XXXXXX.csv` per gauge with a single `streamflow` column.

Also writes `attributes_other_aus_vic.csv` with gauge metadata (lat, lon, name, area, streamflow period, missing fraction, source, license).

Usage:
```
python fetch_maribyrnong.py
```

### `fetch_silo_met.py`
Fetches gridded climate data from the **SILO DataDrill API** (1889–present):
- Variables: `total_precipitation_sum`, `temperature_2m_max/min/mean`, `potential_evaporation_sum` (Morton method), `radiation_mj_m2_d`, `vapour_pressure_hpa`
- Fetches in 10-year chunks, caches raw text to disk
- Merges met data into the existing streamflow CSVs (adds 7 new columns)
- Writes `attributes_caravan_aus_vic.csv` with 10 climate stats: `p_mean`, `pet_mean`, `aridity`, `frac_snow`, `moisture_index`, `moisture_index_seasonality`, `high_prec_freq`, `high_prec_dur`, `low_prec_freq`, `low_prec_dur`

Usage:
```
python fetch_silo_met.py --username your@email.com
```

### `fetch_era5land.py`
Fetches ERA5-Land variables not provided by SILO, via the **Google Earth Engine Python API** (1981–present):
- Variables (mean/min/max per day): `dewpoint_temperature_2m`, `surface_net_solar_radiation`, `surface_net_thermal_radiation`, `surface_pressure`, `u_component_of_wind_10m`, `v_component_of_wind_10m`, `snow_depth_water_equivalent`, `volumetric_soil_water_layer_1/2/3/4`
- Fetches year-by-year via `getRegion`, aggregates hourly -> daily client-side with unit conversions (K->°C, Pa->kPa, m->mm, J/m²->W/m²)
- Caches results to JSON; merges 33 new columns into the existing timeseries CSVs

### `fetch_hydroatlas.py`
Uses the **Google Earth Engine Python API** to query the WWF HydroATLAS BasinATLAS Level-12 dataset:
- Finds the level-12 basin polygon containing each gauge point
- Extracts all 294 basin attributes (geology, land cover, climate indices, etc.)
- Writes `attributes_hydroatlas_aus_vic.csv`
- Auto-backfills `area_km2=None` in `gauges_config.py` using `UP_AREA` from HydroATLAS
- Includes a geopandas-based fallback if you prefer not to use GEE

GEE project: `floodhubmaribyrnong`

### `fetch_catchments.py`
Also uses GEE to derive the full **upstream catchment polygon**:
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

Must be run after `fetch_maribyrnong.py`, `fetch_silo_met.py`, and `fetch_era5land.py`.

### `generate_license.py`
Writes `license_aus_vic.md` — required by the Caravan contribution process — declaring all data sources (Victorian Water, Melbourne Water, SILO, ERA5-Land, HydroATLAS) and their respective licenses.

---

## Output Structure

```
caravan_maribyrnong/
├── timeseries/
│   ├── csv/aus_vic/
│   │   ├── aus_vic_230100.csv   <- streamflow + SILO + ERA5-Land columns
│   │   ├── aus_vic_230104.csv
│   │   ├── aus_vic_230106.csv
│   │   ├── aus_vic_230107.csv
│   │   ├── aus_vic_230200.csv
│   │   ├── aus_vic_230202.csv
│   │   ├── aus_vic_230205.csv
│   │   ├── aus_vic_230206.csv
│   │   ├── aus_vic_230209.csv
│   │   ├── aus_vic_230210.csv
│   │   ├── aus_vic_230211.csv
│   │   ├── aus_vic_230213.csv
│   │   └── aus_vic_230227.csv
│   └── netcdf/aus_vic/
│       └── aus_vic_XXXXXX.nc   (one per gauge)
├── attributes/aus_vic/
│   ├── attributes_other_aus_vic.csv       <- gauge metadata
│   ├── attributes_caravan_aus_vic.csv     <- climate stats (10 columns)
│   ├── attributes_hydroatlas_aus_vic.csv  <- HydroATLAS basin attributes (294 columns)
│   └── hydroatlas_raw_*.json              <- raw GEE responses per gauge
├── shapefiles/aus_vic/
│   ├── aus_vic_catchments.geojson
│   ├── aus_vic_catchments.shp  (+ .dbf, .shx, .prj)
│   └── {gauge_id}_catchment.geojson / .shp
├── licenses/aus_vic/license_aus_vic.md
├── silo_cache_*.csv              <- cached SILO downloads
└── era5land_cache_*.json         <- cached ERA5-Land downloads
```

---

## Requirements

```
pip install earthengine-api xarray netCDF4 numpy geopandas rasterio pysheds
```

GEE setup (one-off):
```python
import ee
ee.Authenticate()
ee.Initialize(project='floodhubmaribyrnong')
```

---

## Testing

A unit test suite and a one-day API smoke test are included:

```
python -m pytest tests/ -q          # unit tests (no network)
python test_run.py --username your@email.com   # live API smoke test
```

Tests run automatically on every `git commit` via the pre-commit hook.

---

## Caravan Compliance

This dataset extension targets full compliance with the [Caravan](https://github.com/kratzert/Caravan) submission standard:

| Requirement | Status |
|---|---|
| `streamflow` column (mm/d) | done |
| SILO met columns (precip, temp, PET, radiation, vapour pressure) | done |
| ERA5-Land columns (dewpoint, wind, pressure, soil moisture, snow, radiation) | done |
| 10 climate stats in `attributes_caravan_aus_vic.csv` | done |
| HydroATLAS attributes in `attributes_hydroatlas_aus_vic.csv` | done |
| Gauge metadata in `attributes_other_aus_vic.csv` | done |
| ESRI shapefile catchment boundaries | done |
| CF-1.8 compliant netCDF4 | done |
| CC-BY-4.0 license file | done |
| Zenodo upload + GitHub issue | done |

---

## Submission Status

| Item | Detail |
|---|---|
| Zenodo DOI | [10.5281/zenodo.18736844](https://doi.org/10.5281/zenodo.18736844) |
| Zenodo zip | `caravan_maribyrnong_zenodo.zip` — 35.6 MB, 115 files |
| GitHub issue | [kratzert/Caravan#51](https://github.com/kratzert/Caravan/issues/51) |

Awaiting review from the Caravan maintainers. They may request minor adjustments to column names, metadata, or file structure before the dataset is merged into the official Caravan release.

---

## Key Design Notes

- **`gauges_config.py` as single source of truth** — all scripts import `GAUGES` from it, so adding a new gauge only requires editing one file
- **Two APIs** — Melbourne Water for mainstem gauges, Victorian Water Hydstra for tributary gauges; both use year-by-year fetching with exponential retry
- **Caching** — SILO data cached as CSV, ERA5-Land as JSON; delete cache files to force re-download
- **Missing data handling** — gaps are left as empty strings in CSV and as `_FillValue=-9999` in netCDF
- **HydroATLAS area snapping** — level-12 basin boundaries are coarser than individual gauge locations; pairs of nearby gauges may share the same `UP_AREA` value. The Keilor (230200) area uses the official Victorian Water figure (1305.4 km²) rather than the HydroATLAS estimate (1413.6 km²)
