# FloodHubMaribyrnong — Claude Context

## Project purpose

Contributing 13 Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan),
the open community dataset used by Google Flood Hub to train its AI flood forecasting model.

- **Zenodo DOI:** https://doi.org/10.5281/zenodo.18736844
- **Caravan submission:** https://github.com/kratzert/Caravan/issues/51
- **GitHub:** https://github.com/maribyrnongfloods/FloodHubMaribyrnong

## Repository layout

```
fetch_maribyrnong.py   — streamflow CSVs from Melbourne Water + Victorian Water APIs
fetch_silo_met.py      — SILO meteorological data (precip, temp, PET, radiation, VP)
fetch_era5land.py      — ERA5-Land variables via Google Earth Engine (wind, pressure, soil moisture, etc.)
fetch_hydroatlas.py    — HydroATLAS basin attributes via GEE
fetch_catchments.py    — upstream catchment polygons via GEE → GeoJSON + shapefiles
write_netcdf.py        — converts merged CSVs → CF-1.8 netCDF4
generate_license.py    — writes license_aus_vic.md
make_map.py            — generates gauge_map.png (B&W basemap, blue rivers, coloured gauges)
gauges_config.py       — SINGLE SOURCE OF TRUTH for all 13 gauges (lat/lon/area/API/dates)
tests/test_pipeline.py — 39 unit tests, no network calls
test_run.py            — live API smoke test (requires --username your@email.com for SILO)
```

Output lives in `caravan_maribyrnong/` (gitignored — 591 MB).
Zenodo zip is `caravan_maribyrnong_zenodo.zip` (35.6 MB, also gitignored).

## Gauge network

13 stations across the Maribyrnong catchment, Victoria, Australia.
Gauge IDs follow Caravan convention: `aus_vic_XXXXXX`.

- **Mainstem** (Melbourne Water API): 230100A, 230211A, 230104A, 230107A, 230200, 230106A
- **Tributaries** (Victorian Water / Hydstra API): 230210, 230206, 230202, 230205, 230209, 230213, 230227

Keilor (230200) has records from 1908 — the longest in the network.
Chifley Drive (230106A) is tidal — only 263 valid flow days above the tidal threshold.

## Key technical facts

- Streamflow unit: **mm/day** (converted from ML/day ÷ catchment area km²)
- ERA5-Land fetched from **1950** (dataset start) — pre-1950 Keilor flow has no reanalysis equivalent
- Missing data: empty string in CSV, `_FillValue = -9999` in netCDF
- CSV has 42 columns: date + streamflow + 7 SILO + 33 ERA5-Land
- Catchment areas from HydroATLAS `UP_AREA`, except Keilor (official Victorian Water figure: 1305.4 km²)
- All data licensed CC-BY-4.0

## Data pipeline (run in order)

```
1. python fetch_maribyrnong.py
2. python fetch_silo_met.py --username your@email.com
3. python fetch_era5land.py          # requires GEE auth
4. python fetch_hydroatlas.py        # requires GEE auth
5. python fetch_catchments.py        # requires GEE auth
6. python write_netcdf.py
7. python generate_license.py
8. python make_map.py                # generates gauge_map.png
```

GEE project: `floodhubmaribyrnong`

## Git branches

- `main` — stable, mirrors latest release
- `dev`  — active development (default working branch)

Always work on `dev`. Merge to `main` when ready to publish.

## Tests

```bash
python -m pytest tests/ -q          # 39 unit tests, no network
python test_run.py --username your@email.com  # live smoke test
```

Tests run automatically on every `git commit` via pre-commit hook.

## Caravan compliance checklist

All items complete:
- `streamflow` column in mm/day
- SILO met columns (7 variables)
- ERA5-Land columns (33 variables)
- `attributes_caravan_aus_vic.csv` (10 climate stats)
- `attributes_hydroatlas_aus_vic.csv` (294 basin attributes)
- `attributes_other_aus_vic.csv` (gauge metadata)
- ESRI shapefiles (per-gauge + combined)
- CF-1.8 compliant netCDF4
- CC-BY-4.0 license file
- Zenodo upload + GitHub issue

---

## Caravan standard — full technical reference

Source: [Kratzert et al. (2023), *Scientific Data*](https://doi.org/10.1038/s41597-023-01975-w)
and [github.com/kratzert/Caravan](https://github.com/kratzert/Caravan)

### Gauge ID format

`{country_code}_{region_code}_{station_number}` — e.g. `aus_vic_230200`

Must be unique across the entire Caravan dataset. Used as the filename prefix for all outputs.

### Timeseries CSV — 42 required columns

**date** — `YYYY-MM-DD`, one row per calendar day, no missing dates in sequence

**streamflow** — mm/day (ML/day ÷ area_km²), empty string for missing, never negative

**SILO meteorological (7 columns):**

| Column | Units |
|--------|-------|
| `total_precipitation_sum` | mm/d |
| `temperature_2m_max` | °C |
| `temperature_2m_min` | °C |
| `temperature_2m_mean` | °C |
| `potential_evaporation_sum` | mm/d (Morton) |
| `radiation_mj_m2_d` | MJ/m²/d |
| `vapour_pressure_hpa` | hPa |

**ERA5-Land (33 columns — mean/min/max for each of 11 variables):**

| Variable | Units |
|----------|-------|
| `dewpoint_temperature_2m` | °C (K − 273.15) |
| `surface_net_solar_radiation` | W/m² (J/m² ÷ 3600) |
| `surface_net_thermal_radiation` | W/m² (J/m² ÷ 3600) |
| `surface_pressure` | kPa (Pa ÷ 1000) |
| `u_component_of_wind_10m` | m/s |
| `v_component_of_wind_10m` | m/s |
| `snow_depth_water_equivalent` | mm (m × 1000) |
| `volumetric_soil_water_layer_1` | m³/m³ (0–7 cm) |
| `volumetric_soil_water_layer_2` | m³/m³ (7–28 cm) |
| `volumetric_soil_water_layer_3` | m³/m³ (28–100 cm) |
| `volumetric_soil_water_layer_4` | m³/m³ (100–289 cm) |

### Attributes CSVs

**`attributes_other_aus_vic.csv`** — gauge metadata (one row per gauge):
`gauge_id`, `gauge_name`, `gauge_lat`, `gauge_lon`, `country`, `basin_name`,
`area`, `unit_area` (always "km2"), `streamflow_period` (ISO 8601 start/end),
`streamflow_missing` (fraction 0–1), `streamflow_units` (always "mm/d"),
`source`, `license`, `note`

**`attributes_caravan_aus_vic.csv`** — 10 climate statistics:
`gauge_id`, `p_mean`, `pet_mean`, `aridity` (PET/P), `frac_snow`,
`moisture_index` (P/PET), `moisture_index_seasonality`,
`high_prec_freq`, `high_prec_dur`, `low_prec_freq`, `low_prec_dur`

**`attributes_hydroatlas_aus_vic.csv`** — 294 HydroATLAS Level-12 basin attributes
(geology, land cover, climate indices, soils, hydrology, topography, human impact).
Key field: `UP_AREA` (auto-fills `area_km2` in `gauges_config.py`).

### netCDF4 requirements

- CF-1.8 compliant, float32 encoding
- `_FillValue = -9999.0` on every variable
- Each variable needs `units` and `long_name` attributes
- Global attributes: `gauge_id`, `gauge_name`, `gauge_lat`, `gauge_lon`,
  `area_km2`, `country`, `streamflow_source`, `met_source`, `license`,
  `streamflow_period`, `streamflow_missing`, `Conventions = "CF-1.8"`, `created`
- Time dimension named `"date"`, unlimited

### Shapefile requirements

Per gauge: `{gauge_id}_catchment.shp/.shx/.dbf/.prj/.cpg`
Combined: `{region}_catchments.shp` (all gauges unioned)
Projection: WGS 84 (EPSG:4326)
DBF attributes: `gauge_id`, `hybas_id_outlet`, `up_area_km2`, `num_level12`

Derived from HydroBASINS Level-12 via GEE BFS upstream traversal, unioned with 30 m tolerance.

### License file

`licenses/{region}/license_{region}.md` — must attribute all data sources:
streamflow provider, SILO, ERA5-Land (C3S licence), HydroATLAS (CC-BY-4.0),
HydroBASINS (CC-BY-4.0). Dataset extension released under CC-BY-4.0.

### Data quality rules

- Filter negative streamflow values
- Filter quality flag `q=255` (Hydstra) bad records
- Deduplicate dates (keep first occurrence)
- Sort chronologically
- Missing data → empty string in CSV, `-9999.0` in netCDF
- ERA5-Land source: `ECMWF/ERA5_LAND/DAILY_AGGR` (not HOURLY)

### Required citation

> Kratzert, F., Gauch, M., Nearing, G., and Klotz, D. (2023). Caravan — A
> global community dataset for large-sample hydrology. *Scientific Data*, 10,
> 61. https://doi.org/10.1038/s41597-023-01975-w

### Submission process

1. Upload zip to Zenodo (CC-BY-4.0), obtain DOI
2. Open issue on https://github.com/kratzert/Caravan with DOI, region, gauge count, data period
3. Maintainer reviews file structure, column names, license, and integrates into next release
