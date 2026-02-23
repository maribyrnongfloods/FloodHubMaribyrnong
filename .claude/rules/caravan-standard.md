# Caravan dataset standard — technical reference

Source: [Kratzert et al. (2023), *Scientific Data*](https://doi.org/10.1038/s41597-023-01975-w)
and [github.com/kratzert/Caravan](https://github.com/kratzert/Caravan)

## Gauge ID format

`{country_code}{region_code}_{station_number}` — e.g. `ausvic_230200`

The prefix is a single token before the underscore: `ausvic` (not `aus_vic`).
Splitting on `_` must return exactly **2** parts.
Must be unique across the entire Caravan dataset.

## Timeseries CSV — 41 required columns

**date** — `YYYY-MM-DD`, one row per calendar day, no missing dates in the ERA5-Land
spine (1950-01-02 to present). Pre-ERA5 streamflow rows (e.g. Keilor 1908–1949) are
prepended with empty ERA5 columns.

**streamflow** — mm/day (ML/day ÷ area_km²), empty string for missing, never negative

### ERA5-Land columns (39 total)

ERA5-Land source: `ECMWF/ERA5_LAND/DAILY_AGGR` via Google Earth Engine

#### Instantaneous state variables — mean / min / max (30 columns)

| Variable | Units | Conversion from ERA5 |
|----------|-------|----------------------|
| `temperature_2m` | °C | K − 273.15 |
| `dewpoint_temperature_2m` | °C | K − 273.15 |
| `surface_pressure` | kPa | Pa ÷ 1000 |
| `u_component_of_wind_10m` | m/s | — |
| `v_component_of_wind_10m` | m/s | — |
| `snow_depth_water_equivalent` | mm | m × 1000 |
| `volumetric_soil_water_layer_1` | m³/m³ | 0–7 cm |
| `volumetric_soil_water_layer_2` | m³/m³ | 7–28 cm |
| `volumetric_soil_water_layer_3` | m³/m³ | 28–100 cm |
| `volumetric_soil_water_layer_4` | m³/m³ | 100–289 cm |

Each produces three columns: `{variable}_mean`, `{variable}_min`, `{variable}_max`.

#### Accumulated flux variables — mean / min / max (6 columns)

| Variable | Units | Conversion |
|----------|-------|------------|
| `surface_net_solar_radiation` | W/m² | J/m²/hr ÷ 3600; sum band ÷ 86400 for mean |
| `surface_net_thermal_radiation` | W/m² | same as solar |

Each produces three columns: `{variable}_mean`, `{variable}_min`, `{variable}_max`.

#### Daily totals — single column each (3 columns)

| Column | Units | Conversion |
|--------|-------|------------|
| `total_precipitation_sum` | mm/d | m × 1000 |
| `potential_evaporation_sum_ERA5_LAND` | mm/d | m × 1000 |
| `potential_evaporation_sum_FAO_PENMAN_MONTEITH` | mm/d | computed inline (FAO-56 PM) |

`potential_evaporation_sum_FAO_PENMAN_MONTEITH` is computed by `_fao_pm_pet_scalar()`
in `fetch_era5land.py` using the formula from
[Caravan pet.py](https://github.com/kratzert/Caravan/blob/main/code/pet.py).

## Attributes CSVs

**`attributes_other_ausvic.csv`** — gauge metadata (one row per gauge):
`gauge_id`, `gauge_name`, `gauge_lat`, `gauge_lon`, `country`, `basin_name`,
`area`, `unit_area` (always "km2"), `streamflow_period` (ISO 8601 start/end),
`streamflow_missing` (fraction 0–1), `streamflow_units` (always "mm/d"),
`source`, `license`, `note`

**`attributes_caravan_ausvic.csv`** — 14 Caravan climate indices (computed over
1981-01-01 to 2020-12-31 per the official Caravan standard period):
`gauge_id`, `p_mean`, `pet_mean_ERA5_LAND`, `pet_mean_FAO_PM`,
`aridity_ERA5_LAND`, `aridity_FAO_PM`, `frac_snow`,
`moisture_index_ERA5_LAND`, `seasonality_ERA5_LAND`,
`moisture_index_FAO_PM`, `seasonality_FAO_PM`,
`high_prec_freq`, `high_prec_dur`, `low_prec_freq`, `low_prec_dur`

Script: `compute_attributes.py` — follows `calculate_climate_indices()` from
[Caravan caravan_utils.py](https://github.com/kratzert/Caravan/blob/main/code/caravan_utils.py)

**`attributes_hydroatlas_ausvic.csv`** — 294 HydroATLAS Level-12 basin attributes.
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

Single combined file: `ausvic_basin_shapes.shp/.shx/.dbf/.prj/.cpg`
Projection: WGS 84 (EPSG:4326)
DBF attributes: `gauge_id` only (no extra columns)

Derived from HydroBASINS Level-12 via GEE BFS upstream traversal, unioned
with 30 m tolerance.

## License file

`licenses/ausvic/license_ausvic.md` — must attribute all data sources:
streamflow providers (Melbourne Water CC-BY-4.0, Victorian WMIS CC-BY-4.0),
ERA5-Land (Copernicus C3S licence), HydroATLAS/HydroBASINS (CC-BY-4.0).
Dataset extension released under CC-BY-4.0.

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

## Pipeline run order

```
python fetch_maribyrnong.py      # streamflow CSVs + attributes_other_ausvic.csv
python fetch_era5land.py         # ERA5-Land forcing (39 cols incl. FAO PM PET)
python compute_attributes.py     # attributes_caravan_ausvic.csv (climate indices)
python fetch_hydroatlas.py       # attributes_hydroatlas_ausvic.csv
python fetch_catchments.py       # ausvic_basin_shapes.shp + .geojson
python write_netcdf.py           # netCDF timeseries files
python generate_license.py       # license_ausvic.md
```
