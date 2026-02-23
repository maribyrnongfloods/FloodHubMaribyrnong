# FloodHubMaribyrnong — Project Context

Contributing 10 Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan),
the open community dataset used by Google Flood Hub to train its AI flood forecasting model.

- **Zenodo DOI:** https://doi.org/10.5281/zenodo.18736844
- **Caravan submission:** https://github.com/kratzert/Caravan/issues/51
- **GitHub:** https://github.com/maribyrnongfloods/FloodHubMaribyrnong

## Repository layout

```
fetch_maribyrnong.py   — streamflow CSVs from Melbourne Water + Victorian Water APIs
fetch_era5land.py      — ERA5-Land variables via Google Earth Engine (full 1950+ range)
fetch_hydroatlas.py    — HydroATLAS basin attributes via GEE (use Caravan Colab notebook instead)
fetch_catchments.py    — upstream catchment polygons via GEE → single ausvic_basin_shapes.shp
write_netcdf.py        — converts merged CSVs → CF-1.8 netCDF4
generate_license.py    — writes license_ausvic.md
make_map.py            — generates gauge_map.png (B&W basemap, blue rivers, coloured gauges)
gauges_config.py       — SINGLE SOURCE OF TRUTH for all 10 gauges (lat/lon/area/API/dates)
tests/test_pipeline.py — unit tests, no network calls
test_run.py            — live API smoke test (Hydstra + Melbourne Water only)
fetch_silo_met.py      — DEPRECATED: SILO removed per Caravan reviewer (not globally available)
```

Output lives in `caravan_maribyrnong/` (gitignored).
Zenodo zip is `caravan_maribyrnong_zenodo.zip` (also gitignored).

## Gauge network

10 stations across the Maribyrnong catchment, Victoria, Australia.
Gauge IDs follow Caravan convention: `ausvic_XXXXXX` (two-part format).

- **Mainstem** (Melbourne Water API): 230100A, 230211A, 230104A, 230107A, 230200, 230106A
- **Tributaries** (Victorian Water / Hydstra API): 230206, 230202, 230213, 230227

3 gauges excluded (in CAMELS AUS v2): 230210, 230205, 230209.

Keilor (230200) has records from 1908 — the longest in the network.
Chifley Drive (230106A) is tidal — only 263 valid flow days above the tidal threshold.

## Key technical facts

- Streamflow unit: **mm/day** (converted from ML/day ÷ catchment area km²)
- ERA5-Land fetched from **1950** (dataset start); pre-1950 rows have ERA5 cols = ""
- SILO removed: not globally available (Caravan reviewer Feb 2026)
- Missing data: empty string in CSV, `_FillValue = -9999` in netCDF
- CSV has **35 columns**: date + streamflow + 33 ERA5-Land (no SILO)
- Catchment areas from HydroATLAS `UP_AREA`, except Keilor (official Victorian Water figure: 1305.4 km²)
- All data licensed CC-BY-4.0
