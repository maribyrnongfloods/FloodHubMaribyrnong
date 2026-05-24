# FloodHubMaribyrnong — Project Specification

**Zenodo DOI:** https://doi.org/10.5281/zenodo.18821361
**Caravan submission:** https://github.com/kratzert/Caravan/issues/51
**GitHub:** https://github.com/maribyrnongfloods/FloodHubMaribyrnong

---

## 1. Project Overview

FloodHubMaribyrnong is a dataset extension for [Caravan](https://github.com/kratzert/Caravan) —
the open community dataset used by Google Flood Hub to train its AI flood forecasting model.

The project contributes **12 gauging stations** from the Maribyrnong River catchment, Victoria,
Australia, providing:

- Daily streamflow records (1908–present at Keilor; 1960–present for Victorian Water tributaries;
  1996–present for Melbourne Water gauges)
- ERA5-Land meteorological forcing (39 columns, 1950–present)
- HydroATLAS basin attributes (195 BasinATLAS Level-12 attributes)
- Catchment polygons derived from HydroBASINS Level-12

All output files strictly follow the Caravan format so they can be integrated into the global
dataset alongside 25,000+ basins from other subdatasets.

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.10+ |
| Notebooks | Jupyter / Google Colab | — |
| Data processing | pandas | 1.3+ |
| Array / netCDF | numpy, xarray | 1.21+ / 0.20+ |
| Geospatial | geopandas, shapely | 0.10+ / 1.8+ |
| Remote sensing | earthengine-api (GEE) | 0.1+ |
| Time / location | pytz, timezonefinder | 2021+ / 5.2+ |
| Performance | numba | 0.55+ |
| Progress UI | tqdm | 4.60+ |
| Testing | pytest | 6.0+ |
| Version control | git (GitHub) | — |
| Dataset hosting | Zenodo (CC-BY-4.0) | — |

---

## 3. Architecture

The pipeline has two phases. The GEE phase runs in Google Colab; everything else runs locally.

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 — Google Earth Engine / Colab                          │
│                                                                  │
│  Notebook 1                                                      │
│  derive_gauge_config  ──► gauges_ausvic.json (12 gauges)        │
│  (MERIT Hydro areas)                                             │
│                                                                  │
│  Notebook 2                                                      │
│  fetch_catchments  ──► ausvic_basin_shapes.shp                  │
│  (HydroBASINS BFS)     ausvic_basin_shapes.geojson              │
│                                                                  │
│  Notebook 4 (Colab)                                             │
│  Caravan_part1_GEE ──► batch01–batch77.csv (~2.9 GB)            │
│  (ERA5-Land hourly,    attributes/attributes.csv                 │
│   HydroATLAS)                                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ download to local
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2 — Local postprocessing                                  │
│                                                                  │
│  Notebook 3                                                      │
│  fetch_streamflow  ──► timeseries/csv/ausvic/*.csv              │
│  (MW + VW APIs)         (date + streamflow, mm/day)              │
│                                                                  │
│  Notebook 5                                                      │
│  Caravan_part2    ──► timeseries/csv/ausvic/*.csv  (41 cols)    │
│  (ERA5 processing,     timeseries/netcdf/ausvic/*.nc             │
│   FAO-56 PET,          attributes_caravan_ausvic.csv            │
│   climate indices,     attributes_hydroatlas_ausvic.csv         │
│   netCDF write)        attributes_other_ausvic.csv              │
│                        licenses/ausvic/license_ausvic.md        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    caravan_maribyrnong_zenodo.zip
                    ── upload to Zenodo ──► DOI
                    ── post to GitHub issue ──► Caravan integration
```

### Key modules

| File | Role |
|------|------|
| `notebooks/caravan_utils.py` | Official Caravan utility library — ERA5-Land aggregation, unit conversion, climate indices |
| `notebooks/pet.py` | FAO-56 Penman-Monteith PET (official Caravan implementation) |
| `tests/test_csv_columns.py` | Schema tests — 41 column names and order |
| `tests/test_attribute_columns.py` | Schema tests — 3 attribute CSVs |
| `.git/hooks/pre-commit` | Runs `pytest tests/ -q` on every commit |
| `caravan_maribyrnong_gee/gauges_ausvic.json` | Gauge network config (12 stations) |

---

## 4. Dependencies

### Python packages

```
pandas>=1.3
numpy>=1.21
xarray>=0.20
geopandas>=0.10
shapely>=1.8
pytz>=2021.3
timezonefinder>=5.2
numba>=0.55
tqdm>=4.60
earthengine-api>=0.1
google-auth>=2.0
pytest>=6.0
```

### External services

| Service | Purpose | Auth required |
|---------|---------|---------------|
| Melbourne Water API | Streamflow data for 7 gauges | None (public) |
| Victorian Water (Hydstra) API | Streamflow data for 5 gauges | None (public) |
| Google Earth Engine | ERA5-Land forcing, HydroATLAS attrs, catchment polygons | GEE project account |
| Google Drive | Staging for GEE batch CSV exports | Google account |
| Zenodo | Dataset hosting and DOI minting | Zenodo account |

---

## 5. Configuration

### GEE project

```python
import ee
ee.Authenticate()
ee.Initialize(project='floodhubmaribyrnong')
```

### Gauge configuration — `caravan_maribyrnong_gee/gauges_ausvic.json`

All gauge metadata lives in this file. Each entry:

```json
{
  "gauge_id": "ausvic_230200",
  "name": "Maribyrnong River at Keilor",
  "lat": -37.7277,
  "lon": 144.8365,
  "area_km2": 1305.4
}
```

Area sources:
- **Keilor (230200):** official Victorian Water figure (1305.4 km²)
- **Keilor North (230237), Chifley Drive (230106):** MERIT Hydro 90m (HydroBASINS Level-12 too coarse — all three co-located gauges snap to the same cell)
- **All others:** HydroATLAS `UP_AREA`

### No environment variables required

All configuration is hardcoded in the notebooks or derived from `gauges_ausvic.json`.
GEE authentication uses the standard `earthengine-api` credential flow.

---

## 6. Key Features

### Streamflow collection
- Fetches daily streamflow from two agencies via public REST APIs
- Converts ML/day → mm/day (÷ catchment area km²)
- Filters bad quality flags (Hydstra q=255), negatives, duplicates
- Sensor ceiling filter: Melbourne Water hardware cap at ~500 m³/s (230211A)

### ERA5-Land forcing
- Fetches `ECMWF/ERA5_LAND/HOURLY` (not `DAILY_AGGR`) via GEE
- 8-step processing pipeline matching the official Caravan Part-2 notebook exactly:
  1. Flip PET sign (upward-positive convention)
  2. De-accumulate hourly flux variables
  3. Clip unphysical negatives
  4. Unit conversion (K→°C, Pa→kPa, J/m²→W/m², m→mm)
  5. UTC → local standard time (UTC+11 fixed offset for Melbourne)
  6. Aggregate to daily
  7. Compute FAO-56 Penman-Monteith PET
  8. Round to 2 decimal places
- ERA5-Land spine from 1950-01-02; pre-1950 streamflow rows (Keilor 1908–1949) have empty ERA5 columns

### HydroATLAS attributes
- Polygon intersection + area-weighting across BasinATLAS Level-12 sub-basins
- Replicates the official Caravan Part-1 GEE notebook entirely from the command line
- 195 BasinATLAS attributes (1 more than original Caravan publication due to GEE dataset update)

### Climate indices
- 14 Caravan-standard indices computed over 1981-01-01 to 2020-12-31
- Implements `calculate_climate_indices()` from official `caravan_utils.py`
- Indices: p_mean, pet_mean (ERA5 + FAO-PM), aridity, frac_snow, moisture_index, seasonality, high/low precip frequency and duration

### Automated schema validation
- 48 unit tests across 2 test files
- Verify: 41-column CSV order, gauge ID format, 14/15/196-column attribute schemas, no banned HydroATLAS columns
- Pre-commit git hook: all tests must pass before any commit

---

## 7. APIs / Interfaces

### Melbourne Water API

```
GET https://api.melbournewater.com.au/rainfall-river-level/{station_id}/river-flow/daily/range
    ?fromDate=YYYY-MM-DD&toDate=YYYY-MM-DD

Response: { dailyRiverFlowsData: [{ dateTime, meanRiverFlow, meanRiverFlow_m3 }] }
Units: ML/day
Stations: 230119A, 230100A, 230102A, 230211A, 230107A, 230237A, 230106A
```

### Victorian Water (Hydstra) API

```
POST https://data.water.vic.gov.au/cgi/webservice.exe
Body: { function: "get_ts_traces", station: "XXXXXX", variable: "141.00",
        datasource: "PUBLISH", starttime: "YYYYMMDD", endtime: "YYYYMMDD" }

Response: { return: { traces: [{ trace: [{ t, v, q }] }] } }
Units: ML/day  |  Quality flag q=255 → bad data (filtered)
Stations: 230200, 230206, 230202, 230213, 230227
```

### Google Earth Engine (Python API)

Used for three purposes:
1. ERA5-Land hourly batch exports → Google Drive CSV files
2. HydroATLAS polygon intersection → attributes CSV
3. MERIT Hydro upstream area lookup → gauge area_km2
4. HydroBASINS BFS upstream traversal → catchment polygons

---

## 8. Data Models

### Timeseries CSV — 41 columns, gapless daily

```
date                                    YYYY-MM-DD
snow_depth_water_equivalent_mean        mm
surface_net_solar_radiation_mean        W/m²
surface_net_thermal_radiation_mean      W/m²
surface_pressure_mean                   kPa
temperature_2m_mean                     °C
dewpoint_temperature_2m_mean            °C
u_component_of_wind_10m_mean            m/s
v_component_of_wind_10m_mean            m/s
volumetric_soil_water_layer_1_mean      m³/m³
volumetric_soil_water_layer_2_mean      m³/m³
volumetric_soil_water_layer_3_mean      m³/m³
volumetric_soil_water_layer_4_mean      m³/m³
[same 12 variables with _min suffix]
[same 12 variables with _max suffix]
total_precipitation_sum                 mm/day
potential_evaporation_sum_ERA5_LAND     mm/day
potential_evaporation_sum_FAO_PENMAN_MONTEITH  mm/day
streamflow                              mm/day (empty string if missing)
```

ERA5-Land date spine: 1950-01-02 to present. Pre-ERA5 rows (Keilor only): empty ERA5 columns.
netCDF encoding: float32, `_FillValue = -9999.0`, CF-1.8 compliant.

### attributes_other_ausvic.csv — 14 columns

```
gauge_id, gauge_name, gauge_lat, gauge_lon, country, basin_name,
area, unit_area, streamflow_period, streamflow_missing, streamflow_units,
source, license, note
```

`streamflow_period`: ISO 8601 interval, e.g. `1908-02-02/2026-02-28`
`streamflow_missing`: fraction 0–1
`unit_area`: always `km2`
`streamflow_units`: always `mm/d`

### attributes_caravan_ausvic.csv — 15 columns (alphabetically sorted)

```
gauge_id,
aridity_ERA5_LAND, aridity_FAO_PM, frac_snow,
high_prec_dur, high_prec_freq, low_prec_dur, low_prec_freq,
moisture_index_ERA5_LAND, moisture_index_FAO_PM,
p_mean, pet_mean_ERA5_LAND, pet_mean_FAO_PM,
seasonality_ERA5_LAND, seasonality_FAO_PM
```

Computed over 1981-01-01 to 2020-12-31 (Caravan standard period).

### attributes_hydroatlas_ausvic.csv — 196 columns

`gauge_id` + 195 BasinATLAS Level-12 attributes (alphabetically sorted).
Derived via polygon intersection + area-weighting (not point lookup).
Banned columns must not appear: `UP_AREA`, `HYBAS_ID`, `PFAF_ID`, `NEXT_DOWN`, upstream aggregates (`_usu`/`_use`), HydroRIVERS properties.

### Shapefile — `ausvic_basin_shapes.shp`

Single combined file. DBF contains one column: `gauge_id`. No other attributes.
Projection: WGS 84 (EPSG:4326). Polygons derived from HydroBASINS Level-12 BFS, unioned with 30m tolerance.

### Gauge ID format

```
ausvic_XXXXXX
└──┬──┘└──┬──┘
   │      └── 6-digit station number
   └── dataset prefix (lowercase)

gauge_id.split('_') must return exactly 2 parts.
```

---

## 9. Deployment

### Running the pipeline

Notebooks must be run in order. Notebook 4 runs in Google Colab; all others run locally.

```bash
# 1. Derive gauge config (run once, output already committed)
jupyter notebook notebooks/1-derive_gauge_config_ausvic.ipynb

# 2. Derive catchment polygons (run once, output already committed)
jupyter notebook notebooks/2-fetch_catchments_ausvic.ipynb

# 3. Fetch streamflow from APIs
jupyter notebook notebooks/3-fetch_streamflow_ausvic.ipynb

# 4. GEE: ERA5-Land + HydroATLAS (run in Google Colab, download batch*.csv)
#    Upload to: https://colab.research.google.com
#    GEE project: floodhubmaribyrnong
#    Output lands in Google Drive → download to caravan_maribyrnong_gee/

# 5. Local postprocessing (ERA5, PET, climate indices, netCDF, attributes)
jupyter notebook notebooks/5-Caravan_part2_local_postprocessing.ipynb
```

### Tests

```bash
python -m pytest tests/ -q        # 48 unit tests — must all pass
```

Tests run automatically on every `git commit` via `.git/hooks/pre-commit`.

### Build the submission zip

```bash
python -c "
import zipfile
from pathlib import Path
with zipfile.ZipFile('caravan_maribyrnong_zenodo.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for f in sorted(Path('caravan_maribyrnong').rglob('*')):
        if f.is_file(): zf.write(f, f)
"
```

Output: `caravan_maribyrnong_zenodo.zip` (~37.7 MB, 33 files). Gitignored — regenerate after pipeline runs.

### Release process

```bash
# 1. Verify tests pass
python -m pytest tests/ -q

# 2. Build zip (see above)

# 3. Upload new version to Zenodo: https://doi.org/10.5281/zenodo.18821361
#    → New version → upload zip → publish → get new DOI

# 4. Update DOI in README.md and caravan_maribyrnong/licenses/ausvic/license_ausvic.md

# 5. Commit, merge dev → main, push both
git add README.md
git commit -m "docs: update Zenodo DOI to vN"
git checkout main && git merge dev --no-edit
git push upstream dev && git push upstream main
git checkout dev

# 6. Post new DOI to https://github.com/kratzert/Caravan/issues/51
```

### Pre-submission checklist

- [ ] All 48 tests pass: `python -m pytest tests/ -q`
- [ ] No `era5land_cache_*.json` files (delete if ERA5 schema changed)
- [ ] No `attributes_hydroatlas_aus_vic.csv` (old filename)
- [ ] No `aus_vic/` directory in output (old prefix)
- [ ] License file attributes all sources (Melbourne Water, Victorian WMIS, ERA5-Land, HydroATLAS)
- [ ] DOI updated in README.md and license_ausvic.md
- [ ] Zip rebuilt after DOI update

---

## Gauge Reference

| Gauge ID | Name | Area (km²) | First flow | Valid days |
|----------|------|---:|:---:|---:|
| ausvic_230119 | Maribyrnong River at Lancefield | 226.1 | 1996-09-25 | 8,086 |
| ausvic_230100 | Deep Creek at Darraweit Guim | 481.5 | 1996-09-25 | 8,086 |
| ausvic_230102 | Deep Creek at Bulla | 857.5 | 1996-09-25 | 8,086 |
| ausvic_230211 | Bolinda Creek at Clarkefield | 94.9 | 2008-05-07 | 6,493 |
| ausvic_230107 | Konagaderra Creek at Konagaderra | 618.0 | 1996-09-25 | 8,070 |
| ausvic_230237 | Maribyrnong River at Keilor North | 1278.1 | 2007-10-25 | 6,603 |
| ausvic_230200 | Maribyrnong River at Keilor | 1305.4 | 1908-02-02 | 36,483 |
| ausvic_230106 | Maribyrnong River at Chifley Drive * | 1385.0 | 1996-09-25 | 8,070 |
| ausvic_230206 | Jackson Creek at Gisborne | 92.3 | 1960-05-10 | 24,028 |
| ausvic_230202 | Jackson Creek at Sunbury | 351.0 | 1960-01-01 | 24,158 |
| ausvic_230213 | Turritable Creek at Mount Macedon | 109.8 | 1975-03-01 | 18,620 |
| ausvic_230227 | Main Creek at Kerrie | 177.8 | 1989-12-05 | 10,622 |

\* Tidal gauge. Only 263 of 8,070 non-missing days exceed the tidal threshold.

Excluded (CAMELS AUS v2 duplicates): 230210, 230205, 230209.
