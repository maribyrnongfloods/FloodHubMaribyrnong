# Caravan dataset standard — technical reference

Source: [Kratzert et al. (2023), *Scientific Data*](https://doi.org/10.1038/s41597-023-01975-w)
and [github.com/kratzert/Caravan](https://github.com/kratzert/Caravan)

## Gauge ID format

`{country_code}_{region_code}_{station_number}` — e.g. `aus_vic_230200`

Must be unique across the entire Caravan dataset. Used as the filename prefix for all outputs.

## Timeseries CSV — 42 required columns

**date** — `YYYY-MM-DD`, one row per calendar day, no missing dates in sequence

**streamflow** — mm/day (ML/day ÷ area_km²), empty string for missing, never negative

### SILO meteorological columns (7)

| Column | Units |
|--------|-------|
| `total_precipitation_sum` | mm/d |
| `temperature_2m_max` | °C |
| `temperature_2m_min` | °C |
| `temperature_2m_mean` | °C |
| `potential_evaporation_sum` | mm/d (Morton) |
| `radiation_mj_m2_d` | MJ/m²/d |
| `vapour_pressure_hpa` | hPa |

### ERA5-Land columns (33 — mean/min/max for each of 11 variables)

| Variable | Units | Conversion |
|----------|-------|------------|
| `dewpoint_temperature_2m` | °C | K − 273.15 |
| `surface_net_solar_radiation` | W/m² | J/m² ÷ 3600 |
| `surface_net_thermal_radiation` | W/m² | J/m² ÷ 3600 |
| `surface_pressure` | kPa | Pa ÷ 1000 |
| `u_component_of_wind_10m` | m/s | — |
| `v_component_of_wind_10m` | m/s | — |
| `snow_depth_water_equivalent` | mm | m × 1000 |
| `volumetric_soil_water_layer_1` | m³/m³ | 0–7 cm |
| `volumetric_soil_water_layer_2` | m³/m³ | 7–28 cm |
| `volumetric_soil_water_layer_3` | m³/m³ | 28–100 cm |
| `volumetric_soil_water_layer_4` | m³/m³ | 100–289 cm |

ERA5-Land GEE dataset: `ECMWF/ERA5_LAND/DAILY_AGGR` (not HOURLY)

## Attributes CSVs

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

## netCDF4 requirements

- CF-1.8 compliant, float32 encoding
- `_FillValue = -9999.0` on every variable
- Each variable needs `units` and `long_name` attributes
- Global attributes: `gauge_id`, `gauge_name`, `gauge_lat`, `gauge_lon`,
  `area_km2`, `country`, `streamflow_source`, `met_source`, `license`,
  `streamflow_period`, `streamflow_missing`, `Conventions = "CF-1.8"`, `created`
- Time dimension named `"date"`, unlimited

## Shapefile requirements

Per gauge: `{gauge_id}_catchment.shp/.shx/.dbf/.prj/.cpg`
Combined: `{region}_catchments.shp` (all gauges unioned)
Projection: WGS 84 (EPSG:4326)
DBF attributes: `gauge_id`, `hybas_id_outlet`, `up_area_km2`, `num_level12`

Derived from HydroBASINS Level-12 via GEE BFS upstream traversal, unioned with 30 m tolerance.

## License file

`licenses/{region}/license_{region}.md` — must attribute all data sources:
streamflow provider, SILO, ERA5-Land (C3S licence), HydroATLAS (CC-BY-4.0),
HydroBASINS (CC-BY-4.0). Dataset extension released under CC-BY-4.0.

## Data quality rules

- Filter negative streamflow values
- Filter quality flag `q=255` (Hydstra) bad records
- Deduplicate dates (keep first occurrence after sort)
- Sort chronologically
- Missing data → empty string in CSV, `-9999.0` in netCDF

## Required citation

> Kratzert, F., Gauch, M., Nearing, G., and Klotz, D. (2023). Caravan — A
> global community dataset for large-sample hydrology. *Scientific Data*, 10,
> 61. https://doi.org/10.1038/s41597-023-01975-w

## Submission process

1. Upload zip to Zenodo (CC-BY-4.0), obtain DOI
2. Open issue on https://github.com/kratzert/Caravan with DOI, region, gauge count, data period
3. Maintainer reviews file structure, column names, license, and integrates into next release
