#!/usr/bin/env python3
"""
fetch_era5land.py

Fetches hourly ERA5-Land meteorological variables from ECMWF/ERA5_LAND/HOURLY
via Google Earth Engine and produces daily aggregates in local time, following
the Caravan Part-2 postprocessing notebook (Caravan_part2_local_postprocessing.ipynb)
exactly.

Processing pipeline (verbatim notebook order):
  1. Flip potential_evaporation sign: * -1  (upward negative -> positive)
  2. Disaggregate accumulated variables (total_precipitation,
     surface_net_solar_radiation, surface_net_thermal_radiation,
     potential_evaporation) by diff(1), replacing hour==1 and iloc[0]
     with original values.  Replicates caravan_utils.disaggregate_features().
  3. Clip total_precipitation and snow_depth_water_equivalent to >= 0.
  4. Unit conversion: K->degC, m->mm, Pa->kPa, J/m2->W/m2.
     Replicates caravan_utils.era5l_unit_conversion().
  5. Convert UTC to local standard time (fixed offset, not DST-aware).
     Trim to [first hour==1, last hour==0].  Resample with
     offset=pd.Timedelta(hours=1) to group each local calendar day as
     [01:00, 01:00 next day).  Replicates caravan_utils.aggregate_df_to_daily().
  6. Compute FAO-56 Penman-Monteith PET from daily Series.
     Replicates pet.get_fao_pm_pet().
  7. Rename potential_evaporation_sum -> potential_evaporation_sum_ERA5_LAND.
  8. Round to 2 decimal places.

Reference implementations:
  code_to_leverage/caravan_utils.py  (disaggregate_features,
    era5l_unit_conversion, aggregate_df_to_daily, _utc_to_local_standard_time,
    _get_offset)
  code_to_leverage/pet.py  (get_fao_pm_pet, _preprocess_inputs,
    _calculate_pm_pet_daily)

Produces 39 ERA5-Land output columns (plus date and streamflow = 41 total).
See caravan-standard.md for column names and units.

Requirements:
    pip install earthengine-api pandas numpy timezonefinder pytz

First-time setup:
    earthengine authenticate
"""

import csv
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from gauges_config import GAUGES

# ── Paths ──────────────────────────────────────────────────────────────────────

OUT_DIR = Path("caravan_maribyrnong")
TS_DIR  = OUT_DIR / "timeseries" / "csv" / "ausvic"

ERA5_START_YEAR = 1950
GEE_COLLECTION  = "ECMWF/ERA5_LAND/HOURLY"   # NOT DAILY_AGGR
GEE_PROJECT     = "floodhubmaribyrnong"

# ── Variable lists (verbatim from Part-2 notebook config) ──────────────────────

# All 14 hourly bands fetched from GEE
ERA5L_BANDS = [
    'temperature_2m',
    'dewpoint_temperature_2m',
    'volumetric_soil_water_layer_1',
    'volumetric_soil_water_layer_2',
    'volumetric_soil_water_layer_3',
    'volumetric_soil_water_layer_4',
    'surface_net_solar_radiation',
    'surface_net_thermal_radiation',
    'u_component_of_wind_10m',
    'v_component_of_wind_10m',
    'surface_pressure',
    'total_precipitation',
    'snow_depth_water_equivalent',
    'potential_evaporation',
]

# Aggregation targets — verbatim from notebook MEAN_VARS / SUM_VARS
MEAN_VARS = [
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
]
MIN_VARS = MEAN_VARS
MAX_VARS = MEAN_VARS
SUM_VARS = ['total_precipitation', 'potential_evaporation']

# Final 39 ERA5-Land output column names (must match write_netcdf.py VAR_META)
ERA5_COLS = (
    [f"{v}_mean" for v in MEAN_VARS]   # 12
    + [f"{v}_min"  for v in MIN_VARS]  # 12
    + [f"{v}_max"  for v in MAX_VARS]  # 12
    + ["total_precipitation_sum",
       "potential_evaporation_sum_ERA5_LAND",
       "potential_evaporation_sum_FAO_PENMAN_MONTEITH"]  # 3
)  # 39 total


# ── Scalar unit converter (kept for test backward-compatibility) ───────────────

_UNIT_CONVERTERS = {
    "temperature_2m":                lambda v: v - 273.15,
    "dewpoint_temperature_2m":       lambda v: v - 273.15,
    "surface_pressure":              lambda v: v / 1000.0,
    "u_component_of_wind_10m":       lambda v: v,
    "v_component_of_wind_10m":       lambda v: v,
    "snow_depth_water_equivalent":   lambda v: v * 1000.0,
    "volumetric_soil_water_layer_1": lambda v: v,
    "volumetric_soil_water_layer_2": lambda v: v,
    "volumetric_soil_water_layer_3": lambda v: v,
    "volumetric_soil_water_layer_4": lambda v: v,
    "surface_net_solar_radiation":   lambda v: v / 3600.0,
    "surface_net_thermal_radiation": lambda v: v / 3600.0,
    "total_precipitation":           lambda v: v * 1000.0,
    "potential_evaporation":         lambda v: v * -1000.0,
}


def convert_units(var: str, value: float) -> float:
    """Scalar unit conversion for a base ERA5-Land variable name.
    Kept for backward compatibility with tests.
    """
    converter = _UNIT_CONVERTERS.get(var)
    if converter is None:
        raise KeyError(f"No unit converter registered for variable: {var!r}")
    return converter(value)


# ── Notebook-faithful processing functions ─────────────────────────────────────
#
# Each function below replicates the corresponding function in
# code_to_leverage/caravan_utils.py or code_to_leverage/pet.py.
# Variable names and logic match the reference implementations verbatim.


def disaggregate_features(df: pd.DataFrame) -> pd.DataFrame:
    """Disaggregate daily accumulated ERA5-Land features into hourly values.

    Replicates caravan_utils.disaggregate_features() exactly.

    ERA5-Land HOURLY (GEE): accumulated variables reset once per UTC day.
    val[00:00 UTC] = total accumulated over the previous 24-hour period
                     (forecast hour 24 from the previous UTC day).
    val[01:00 UTC] = first-hour accumulation of the current UTC day.
    val[02:00+  ] = cumulative from 00:00 UTC.

    After diff(1):
      - hour 00: correct  (= last hour of previous UTC day)
      - hour 01: wrong    (= first_hour - prev_24h_total), must be replaced
      - hour 02+: correct (consecutive hourly diffs)
    """
    columns = [
        "total_precipitation",
        "surface_net_solar_radiation",
        "surface_net_thermal_radiation",
        "potential_evaporation",
    ]
    columns = [c for c in columns if c in df.columns]

    temp = df[columns].diff(1)

    # replace every 00:00 to 01:00 value with the original data
    temp.loc[temp.index.hour == 1] = df[columns].loc[df.index.hour == 1].values

    # the first time step in diff time series is NaN, replace with original data
    temp.iloc[0] = df[columns].iloc[0]

    df[columns] = temp
    return df


def era5l_unit_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """Convert ERA5-Land units to commonly used hydrology units.

    Replicates caravan_utils.era5l_unit_conversion() exactly.
    NOTE: potential_evaporation sign flip (* -1) must be applied BEFORE
    calling this function (not inside it), matching the notebook order.
    """
    for col in df.columns:
        if col == "dewpoint_temperature_2m":
            df[col] = df[col] - 273.15          # K -> degC

        elif col == "temperature_2m":
            df[col] = df[col] - 273.15          # K -> degC

        elif col == "snow_depth_water_equivalent":
            df[col] = df[col] * 1000            # m -> mm

        elif col == "surface_net_solar_radiation":
            df[col] = df[col] / 3600            # J/m2 -> W/m2

        elif col == "surface_net_thermal_radiation":
            df[col] = df[col] / 3600            # J/m2 -> W/m2

        elif col == "surface_pressure":
            df[col] = df[col] / 1000            # Pa -> kPa

        elif col == "total_precipitation":
            df[col] = df[col] * 1000            # m -> mm

        elif col == "potential_evaporation":
            df[col] = df[col] * 1000            # m -> mm (sign already flipped)

    return df


def _get_timezone_offset(tz_name: str, lat: float) -> float:
    """Return fixed UTC offset in hours for a timezone.

    Uses summer time for the relevant hemisphere to get a consistent
    (non-DST-switching) offset for the full year.
    Replicates caravan_utils._get_offset() exactly.
    """
    from pytz import timezone as pytz_tz, utc as pytz_utc

    # Southern hemisphere: use January (southern summer = DST).
    # Northern hemisphere: use August (northern summer = DST).
    if lat <= 0:
        some_date = datetime.strptime("2020-01-01", "%Y-%m-%d")
    else:
        some_date = datetime.strptime("2020-08-01", "%Y-%m-%d")

    tz_target = pytz_tz(tz_name)
    date_lst = tz_target.localize(some_date)
    date_utc = pytz_utc.localize(some_date)
    return (date_utc - date_lst).total_seconds() / 3600.0


def aggregate_df_to_daily(
    df: pd.DataFrame,
    gauge_lat: float,
    gauge_lon: float,
) -> pd.DataFrame:
    """Aggregate hourly ERA5-Land (UTC) to daily in local standard time.

    Replicates caravan_utils.aggregate_df_to_daily() exactly, using the
    notebook's MEAN_VARS / MIN_VARS / MAX_VARS / SUM_VARS lists.

    Steps:
      1. Shift UTC index by fixed local offset (non-DST for hemisphere).
      2. Trim data to [first hour==1, last hour==0] to ensure complete days.
      3. Resample with offset=pd.Timedelta(hours=1) so each daily bin covers
         [01:00, 01:00 next day) in local time, matching the 24 hourly
         accumulation periods (01:00..23:00 + 00:00 of next UTC day).
    """
    from timezonefinder import TimezoneFinder
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=gauge_lat, lng=gauge_lon)
    if tz_name is None:
        tz_name = "UTC"
    offset = _get_timezone_offset(tz_name, gauge_lat)

    # Shift index from UTC to local standard time (naive, fixed offset)
    df = df.copy()
    df.index = df.index + pd.to_timedelta(offset, unit='h')

    # Trim to complete days: first hour==1 to last hour==0
    start_date = df.loc[df.index.hour == 1].first_valid_index()
    end_date   = df.loc[df.index.hour == 0].last_valid_index()
    df = df[start_date:end_date]

    dfs = []

    # mean / min / max: offset=1h so bins = [01:00, 01:00 next day)
    df_mean = df[MEAN_VARS].resample('1D', offset=pd.Timedelta(hours=1)).mean()
    df_mean = df_mean.rename(columns={c: f"{c}_mean" for c in df_mean.columns})
    dfs.append(df_mean)

    df_min = df[MIN_VARS].resample('1D', offset=pd.Timedelta(hours=1)).min()
    df_min = df_min.rename(columns={c: f"{c}_min" for c in df_min.columns})
    dfs.append(df_min)

    df_max = df[MAX_VARS].resample('1D', offset=pd.Timedelta(hours=1)).max()
    df_max = df_max.rename(columns={c: f"{c}_max" for c in df_max.columns})
    dfs.append(df_max)

    df_sum = df[SUM_VARS].resample('1D', offset=pd.Timedelta(hours=1)).sum()
    df_sum = df_sum.rename(columns={c: f"{c}_sum" for c in df_sum.columns})
    dfs.append(df_sum)

    aggregates = pd.concat(dfs, axis=1)

    # Convert index to plain date strings, then to DatetimeIndex (date-only)
    aggregates.index = aggregates.index.strftime('%Y-%m-%d')
    aggregates.index = pd.to_datetime(aggregates.index, format="%Y-%m-%d")
    return aggregates


def get_fao_pm_pet(daily_df: pd.DataFrame) -> pd.Series:
    """Compute FAO-56 Penman-Monteith reference ET (mm/day) as a pd.Series.

    Replicates pet.get_fao_pm_pet(), pet._preprocess_inputs(), and
    pet._calculate_pm_pet_daily() from code_to_leverage/pet.py exactly.

    All inputs must be in Caravan units (after era5l_unit_conversion):
      surface_pressure_mean      kPa
      temperature_2m_mean        degC
      dewpoint_temperature_2m_mean degC
      u_component_of_wind_10m_mean m/s
      v_component_of_wind_10m_mean m/s
      surface_net_solar_radiation_mean  W/m2
      surface_net_thermal_radiation_mean W/m2
    """
    # _preprocess_inputs
    windspeed10m = np.sqrt(
        daily_df["u_component_of_wind_10m_mean"] ** 2
        + daily_df["v_component_of_wind_10m_mean"] ** 2
    )
    windspeed2m_m_s = windspeed10m * 4.87 / (np.log(67.8 * 10 - 5.42))

    net_radiation_MJ_m2 = (
        (daily_df["surface_net_solar_radiation_mean"]
         + daily_df["surface_net_thermal_radiation_mean"])
        * 3600 * 24 / 1e6
    )

    # _calculate_pm_pet_daily
    lmbda = 2.45       # latent heat of vaporization [MJ kg-1]
    cp    = 1.013e-3   # specific heat at constant pressure [MJ kg-1 degC-1]
    eps   = 0.622      # ratio molecular weight water/dry air

    P_kpa = daily_df["surface_pressure_mean"]
    T_c   = daily_df["temperature_2m_mean"]
    Td_c  = daily_df["dewpoint_temperature_2m_mean"]

    psychometric_kpa_c = cp * P_kpa / (eps * lmbda)
    svp_kpa   = 0.6108 * np.exp((17.27 * T_c) / (T_c + 237.3))
    delta_kpa_c = 4098.0 * svp_kpa / (T_c + 237.3) ** 2
    avp_kpa   = 0.6108 * np.exp((17.27 * Td_c) / (Td_c + 237.3))
    svpdeficit_kpa = svp_kpa - avp_kpa

    soil_heat_flux = np.zeros_like(P_kpa)

    numerator = (
        0.408 * delta_kpa_c * (net_radiation_MJ_m2 - soil_heat_flux)
        + psychometric_kpa_c * (900 / (T_c + 273)) * windspeed2m_m_s * svpdeficit_kpa
    )
    denominator = delta_kpa_c + psychometric_kpa_c * (1 + 0.34 * windspeed2m_m_s)

    ET0_mm_day = numerator / denominator
    return ET0_mm_day.clip(lower=0.0)   # clip negative PET to zero


# ── GEE helpers ───────────────────────────────────────────────────────────────

def init_gee():
    """Initialise GEE, authenticating if needed. Returns the ee module."""
    try:
        import ee
    except ImportError:
        print("ERROR: earthengine-api not installed.")
        print("       Run: pip install earthengine-api")
        sys.exit(1)

    print("Initialising Google Earth Engine ...")
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        print("  Not authenticated -- opening browser for Google sign-in ...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)

    return ee


def fetch_hourly_chunk(ee, lat: float, lon: float,
                       start: str, end: str) -> list[dict]:
    """Fetch hourly ERA5-Land for a date range via GEE getRegion.

    Returns a list of raw dicts: {timestamp_ms, band1, band2, ...}.
    Uses quarterly chunks (passed as start/end ISO dates) to stay within
    GEE response-size limits (~2000 hours x 14 bands per request).
    """
    point = ee.Geometry.Point([lon, lat])
    col = (
        ee.ImageCollection(GEE_COLLECTION)
          .filterDate(start, end)
          .select(ERA5L_BANDS)
    )
    region = col.getRegion(point, scale=9000).getInfo()
    if not region or len(region) < 2:
        return []

    header = region[0]  # ['id', 'longitude', 'latitude', 'time', band1, ...]
    rows   = region[1:]

    result = []
    for row in rows:
        if None in row:
            continue
        d = dict(zip(header, row))
        ts = d.get("time")
        if ts is None:
            continue
        rec = {"timestamp_ms": ts}
        for band in ERA5L_BANDS:
            rec[band] = d.get(band)
        result.append(rec)
    return result


def fetch_all_hourly_raw(ee, gauge: dict) -> list[dict]:
    """Fetch all hourly ERA5-Land from ERA5_START_YEAR to present, quarterly.

    Returns a flat list of raw hourly dicts (timestamp_ms + 14 ERA5 bands).
    Quarterly chunking avoids GEE memory limits on large date ranges.
    """
    all_rows: list[dict] = []
    end_year = date.today().year

    # Quarter boundaries (month starts)
    quarters = [(1, 4), (4, 7), (7, 10), (10, 1)]

    for year in range(ERA5_START_YEAR, end_year + 1):
        print(f"    {year} ...", end=" ", flush=True)
        year_rows = []
        for (m_start, m_end) in quarters:
            y_end = year + 1 if m_end == 1 else year
            start = f"{year}-{m_start:02d}-01"
            end   = f"{y_end}-{m_end:02d}-01"
            try:
                chunk = fetch_hourly_chunk(ee, gauge["lat"], gauge["lon"],
                                           start, end)
                year_rows.extend(chunk)
                time.sleep(0.3)
            except Exception as exc:
                print(f"\n    ERROR ({start} to {end}): {exc}")
        print(f"{len(year_rows)} hours")
        all_rows.extend(year_rows)

    return all_rows


# ── Full hourly -> daily processing pipeline ──────────────────────────────────

def process_hourly_to_daily(raw_rows: list[dict],
                             gauge_lat: float,
                             gauge_lon: float) -> pd.DataFrame:
    """Convert raw GEE hourly records to daily ERA5-Land DataFrame.

    Follows the Part-2 notebook cell order exactly:
      1. Flip PET sign (* -1)
      2. disaggregate_features()
      3. Clip precip and SWE to 0
      4. era5l_unit_conversion()
      5. aggregate_df_to_daily()
      6. Add FAO PM PET column
      7. Rename potential_evaporation_sum -> potential_evaporation_sum_ERA5_LAND
      8. Round to 2 decimal places
    """
    # Build UTC-indexed DataFrame from raw GEE records
    rows_for_df = []
    for r in raw_rows:
        ts_ms = r["timestamp_ms"]
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ts_ms)
        row = {band: r.get(band) for band in ERA5L_BANDS}
        row["dt"] = dt.replace(tzinfo=None)   # naive UTC (consistent with caravan_utils)
        rows_for_df.append(row)

    df = pd.DataFrame(rows_for_df).set_index("dt")
    df.index.name = "date"
    df = df.sort_index()

    # Step 1: flip PET sign (upward negative -> positive)
    # Matches: df["potential_evaporation"] = df["potential_evaporation"] * -1
    df["potential_evaporation"] = df["potential_evaporation"] * -1

    # Step 2: disaggregate accumulated features
    df = disaggregate_features(df)

    # Step 3: clip precipitation and SWE to 0
    df.loc[df["total_precipitation"] < 0, "total_precipitation"] = 0.0
    df.loc[df["snow_depth_water_equivalent"] < 0, "snow_depth_water_equivalent"] = 0.0

    # Step 4: unit conversion
    df = era5l_unit_conversion(df)

    # Step 5: aggregate to daily in local time
    daily = aggregate_df_to_daily(df, gauge_lat, gauge_lon)

    # Step 6: FAO Penman-Monteith PET
    daily["potential_evaporation_sum_FAO_PENMAN_MONTEITH"] = get_fao_pm_pet(daily)

    # Step 7: rename ERA5-Land PET column
    daily.rename(
        columns={'potential_evaporation_sum': 'potential_evaporation_sum_ERA5_LAND'},
        inplace=True,
    )

    # Step 8: round to 2 decimal places
    # Matches: df.round(2).map('{:.2f}'.format).map(float)
    daily = daily.round(2).map('{:.2f}'.format).map(float)

    return daily


# ── Cache handling (stores daily post-processed data) ─────────────────────────

def load_daily_cache(cache_path: Path) -> pd.DataFrame | None:
    """Load cached daily DataFrame.  Returns None if absent or stale."""
    if not cache_path.exists():
        return None
    with open(cache_path) as f:
        rows = json.load(f)
    if not rows:
        return None

    # Validate that all expected ERA5 columns are present
    expected = set(ERA5_COLS)
    if not expected.issubset(set(rows[0].keys())):
        missing = expected - set(rows[0].keys())
        print(f"    Cache stale ({len(missing)} columns missing) -- re-downloading ...")
        return None

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df = df.set_index("date")
    print(f"    Using cache: {cache_path.name}")
    print(f"    (Delete to force fresh download)")
    return df


def save_daily_cache(cache_path: Path, daily: pd.DataFrame) -> None:
    """Save daily DataFrame as a JSON cache file."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for d, row in daily.iterrows():
        rec = {"date": d.strftime("%Y-%m-%d")}
        for col, val in row.items():
            rec[col] = None if pd.isna(val) else val
        rows.append(rec)
    with open(cache_path, "w") as f:
        json.dump(rows, f)
    print(f"    Cached -> {cache_path.name}")


# ── Merge daily ERA5-Land into timeseries CSV ──────────────────────────────────

def merge_era5land(gauge: dict, daily: pd.DataFrame) -> None:
    """Rebuild the timeseries CSV with a 1950-present ERA5-Land date spine.

    daily : pd.DataFrame
        DatetimeIndex (daily), columns = ERA5_COLS (39).
        Produced by process_hourly_to_daily() or loaded from cache.

    Pre-1950 streamflow rows (e.g. Keilor 1908-1949) are prepended with
    empty ERA5 columns, so the file starts with the earliest available data.
    """
    gid     = gauge["gauge_id"]
    ts_path = TS_DIR / f"{gid}.csv"

    # Load existing streamflow keyed by ISO date string
    sf_by_date: dict[str, str] = {}
    if ts_path.exists():
        with open(ts_path, newline="") as f:
            for row in csv.DictReader(f):
                sf_by_date[row["date"]] = row.get("streamflow", "")

    all_cols  = ["date", "streamflow"] + ERA5_COLS
    era5_dates = {d.strftime("%Y-%m-%d") for d in daily.index}

    # ── 1. ERA5 spine (1950+): streamflow merged in where available ────────
    matched = 0
    merged: list[dict] = []
    for d in sorted(daily.index):
        date_str = d.strftime("%Y-%m-%d")
        sf = sf_by_date.get(date_str, "")
        if sf:
            matched += 1
        row_data = daily.loc[d]
        new_row = {"date": date_str, "streamflow": sf}
        for col in ERA5_COLS:
            val = row_data.get(col)
            new_row[col] = "" if (val is None or pd.isna(val)) else val
        merged.append(new_row)

    # ── 2. Pre-ERA5 streamflow rows (e.g. Keilor 1908-1949) ───────────────
    era5_start = min(era5_dates)
    pre_era5: list[dict] = []
    for d, sf in sorted(sf_by_date.items()):
        if d not in era5_dates and sf and d < era5_start:
            pre_era5.append({"date": d, "streamflow": sf,
                             **{c: "" for c in ERA5_COLS}})

    # ── 3. Post-ERA5 streamflow rows (GEE lag) ────────────────────────────
    era5_end = max(era5_dates)
    post_era5: list[dict] = []
    for d, sf in sorted(sf_by_date.items()):
        if d not in era5_dates and sf and d > era5_end:
            post_era5.append({"date": d, "streamflow": sf,
                              **{c: "" for c in ERA5_COLS}})

    merged = pre_era5 + merged + post_era5

    print(f"    Streamflow matched with ERA5: {matched} / {len(sf_by_date)}")
    print(f"    Pre-ERA5 streamflow rows:     {len(pre_era5)}")
    print(f"    Total rows in output CSV:     {len(merged)}")

    with open(ts_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols)
        writer.writeheader()
        writer.writerows(merged)
    print(f"    Written -> {ts_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching ERA5-Land variables via Google Earth Engine")
    print("(ECMWF/ERA5_LAND/HOURLY, notebook-faithful Part-2 pipeline)\n")

    ee = init_gee()

    for gauge in GAUGES:
        gid  = gauge["gauge_id"]
        print(f"\n{'─' * 60}")
        print(f"ERA5-Land: {gauge['name']} ({gauge['station_id']})")
        print(f"{'─' * 60}")

        if gauge["lat"] is None or gauge["lon"] is None:
            print("  Skipping -- lat/lon not set in gauges_config.py")
            continue

        cache_path = OUT_DIR / f"era5land_hourly_cache_{gid}.json"

        daily = load_daily_cache(cache_path)
        if daily is None:
            print(f"  Fetching hourly ERA5-Land at ({gauge['lat']}, {gauge['lon']}) "
                  f"from {ERA5_START_YEAR} ...")
            raw_rows = fetch_all_hourly_raw(ee, gauge)
            print(f"  Total hourly records fetched: {len(raw_rows)}")
            print("  Processing: flip -> disaggregate -> clip -> convert -> "
                  "local-time daily -> FAO PET -> round ...")
            daily = process_hourly_to_daily(raw_rows, gauge["lat"], gauge["lon"])
            save_daily_cache(cache_path, daily)

        print(f"  Total daily rows: {len(daily)}")
        merge_era5land(gauge, daily)

    print(f"""
{'=' * 60}
 ERA5-Land merge complete (HOURLY, local-time, notebook-faithful).
 Next steps:
   python compute_attributes.py
   python fetch_hydroatlas_polygon.py
   python fetch_catchments.py
   python write_netcdf.py
{'=' * 60}
""")


if __name__ == "__main__":
    main()
