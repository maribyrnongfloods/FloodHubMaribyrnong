# ERA5-Land processing — notebook-faithful implementation

Reference: `code_to_leverage/Caravan_part2_local_postprocessing.ipynb`
Code:       `code_to_leverage/caravan_utils.py`, `code_to_leverage/pet.py`

## GEE collection

**MUST use `ECMWF/ERA5_LAND/HOURLY`** — NOT `DAILY_AGGR`.

The notebook fetches raw hourly data and aggregates it locally so the UTC→local
time conversion can be applied correctly before daily binning. Using the
pre-aggregated daily collection would silently produce wrong values for any
timezone that is not UTC.

## ERA5-Land accumulation convention

In `ECMWF/ERA5_LAND/HOURLY` (GEE), the four accumulated variables
(`total_precipitation`, `surface_net_solar_radiation`,
`surface_net_thermal_radiation`, `potential_evaporation`) are stored as
**running totals that reset once per UTC day**:

- `val[00:00 UTC]` = total accumulated over the **previous** 24-hour forecast
  period (forecast hour 24 from the prior UTC day initialisation)
- `val[01:00 UTC]` = first-hour accumulation of the current UTC day
- `val[02:00+ UTC]` = cumulative from 00:00 UTC

This means after `diff(1)`:

| Hour | diff result | Correct? |
|------|-------------|----------|
| 00   | last hour of previous day | YES |
| 01   | `first_hour - prev_24h_total` (wrong) | NO — replace with original |
| 02+  | consecutive hourly difference | YES |

## Processing pipeline (must follow this exact order)

```python
# Step 1: flip PET sign (upward-positive convention -> positive)
df["potential_evaporation"] = df["potential_evaporation"] * -1

# Step 2: de-accumulate hourly fluxes
df = disaggregate_features(df)

# Step 3: clip unphysical negatives
df.loc[df["total_precipitation"] < 0, "total_precipitation"] = 0.0
df.loc[df["snow_depth_water_equivalent"] < 0, "snow_depth_water_equivalent"] = 0.0

# Step 4: unit conversion (K->degC, Pa->kPa, J/m2->W/m2, m->mm)
df = era5l_unit_conversion(df)

# Step 5: UTC -> local standard time, aggregate to daily
daily = aggregate_df_to_daily(df, gauge_lat, gauge_lon)

# Step 6: FAO-56 Penman-Monteith PET
daily["potential_evaporation_sum_FAO_PENMAN_MONTEITH"] = get_fao_pm_pet(daily)

# Step 7: rename ERA5 PET column
daily.rename(
    columns={"potential_evaporation_sum": "potential_evaporation_sum_ERA5_LAND"},
    inplace=True,
)

# Step 8: round to 2 decimal places (exact notebook pattern)
daily = daily.round(2).map('{:.2f}'.format).map(float)
```

**The PET sign flip (step 1) must happen BEFORE `disaggregate_features` and
BEFORE `era5l_unit_conversion`.** It is NOT inside `era5l_unit_conversion`.

## Variable lists (verbatim from notebook)

```python
MEAN_VARS = [                           # also used for MIN and MAX
    'snow_depth_water_equivalent',
    'surface_net_solar_radiation',
    'surface_net_thermal_radiation',
    'surface_pressure',
    'temperature_2m',
    'dewpoint_temperature_2m',
    'u_component_of_wind_10m',
    'v_component_of_wind_10m',
    'volumetric_soil_water_layer_1',
    'volumetric_soil_water_layer_2',
    'volumetric_soil_water_layer_3',
    'volumetric_soil_water_layer_4',
]  # 12 variables
MIN_VARS = MEAN_VARS
MAX_VARS = MEAN_VARS

SUM_VARS = ['total_precipitation', 'potential_evaporation']  # 2 variables
```

Result: 12×3 + 2 = **38 aggregated columns**, plus
`potential_evaporation_sum_FAO_PENMAN_MONTEITH` = **39 ERA5-Land output columns total**.

## disaggregate_features()

Replicates `caravan_utils.disaggregate_features()`.

```python
columns = ['total_precipitation', 'surface_net_solar_radiation',
           'surface_net_thermal_radiation', 'potential_evaporation']
temp = df[columns].diff(1)
temp.loc[temp.index.hour == 1] = df[columns].loc[df.index.hour == 1].values  # fix hour 01
temp.iloc[0] = df[columns].iloc[0]                                             # fix first row
df[columns] = temp
```

Key: replaces `hour == 1` rows (not `hour == 0`) with original values.

## era5l_unit_conversion()

Replicates `caravan_utils.era5l_unit_conversion()`. Conversions:

| Variable | Conversion |
|----------|-----------|
| `temperature_2m` | K − 273.15 → °C |
| `dewpoint_temperature_2m` | K − 273.15 → °C |
| `surface_pressure` | Pa ÷ 1000 → kPa |
| `snow_depth_water_equivalent` | m × 1000 → mm |
| `surface_net_solar_radiation` | J/m² ÷ 3600 → W/m² |
| `surface_net_thermal_radiation` | J/m² ÷ 3600 → W/m² |
| `total_precipitation` | m × 1000 → mm |
| `potential_evaporation` | m × 1000 → mm (sign already flipped in step 1) |
| `u_component_of_wind_10m` | none (already m/s) |
| `v_component_of_wind_10m` | none (already m/s) |
| `volumetric_soil_water_layer_*` | none (already m³/m³) |

## aggregate_df_to_daily()

Replicates `caravan_utils.aggregate_df_to_daily()`.

1. **Fixed UTC offset** (not DST-aware): use `timezonefinder` to get timezone
   name, then use `pytz` to get the UTC offset for:
   - Southern hemisphere (lat ≤ 0): January date → southern summer = AEDT (UTC+11 for Melbourne)
   - Northern hemisphere (lat > 0): August date → northern summer
2. **Trim**: keep rows from first `hour==1` to last `hour==0` (ensures complete days).
3. **Resample**: `offset=pd.Timedelta(hours=1)` — bins are `[01:00, 01:00 next day)` in
   local standard time. This is positive, not negative.

For Melbourne (37.8°S, 145.0°E): UTC+11 (January/AEDT used year-round for consistency).

## get_fao_pm_pet()

Replicates `pet.get_fao_pm_pet()` + helpers from `code_to_leverage/pet.py`.

Inputs (after daily aggregation and unit conversion):

| Column | Units |
|--------|-------|
| `surface_pressure_mean` | kPa |
| `temperature_2m_mean` | °C |
| `dewpoint_temperature_2m_mean` | °C |
| `u_component_of_wind_10m_mean` | m/s |
| `v_component_of_wind_10m_mean` | m/s |
| `surface_net_solar_radiation_mean` | W/m² |
| `surface_net_thermal_radiation_mean` | W/m² |

Wind speed at 10 m → 2 m height:
```python
windspeed2m = sqrt(u² + v²) * 4.87 / log(67.8 * 10 - 5.42)
```

Net radiation in MJ/m²/day:
```python
net_rad = (solar_mean + thermal_mean) * 3600 * 24 / 1e6
```

Soil heat flux = 0 (FAO eq. 42 for daily).

Result is clipped to `lower=0.0`.

## Cache strategy

- Cache file: `era5land_hourly_cache_{gauge_id}.json`
- Stores **post-processed daily data** (after the full 8-step pipeline above)
- Delete cache files when ERA5-Land schema or processing logic changes
- GEE is queried in quarterly chunks to avoid memory limits

## What NOT to do

- Do NOT use `ECMWF/ERA5_LAND/DAILY_AGGR` — this bypasses the UTC→local
  aggregation and produces wrong daily values for non-UTC timezones.
- Do NOT flip PET sign inside `era5l_unit_conversion` — the sign flip is a
  separate notebook step that must happen first.
- Do NOT use DST-aware timezone conversion — the notebook uses a fixed
  summer-time offset for the entire year.
- Do NOT use `offset=-pd.Timedelta(hours=1)` in resample — the notebook uses
  positive `+1h` offset (despite some markdown comments suggesting otherwise).
