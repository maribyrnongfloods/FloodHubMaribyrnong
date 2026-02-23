#!/usr/bin/env python3
"""
fetch_era5land.py

Fetches daily ERA5-Land meteorological variables at each gauge location via
Google Earth Engine and merges them into the existing timeseries CSVs.

Uses ECMWF/ERA5_LAND/DAILY_AGGR (pre-aggregated daily statistics, 365 images/year)
instead of the hourly collection (8,760 images/year) to avoid GEE memory limits.

Adds the variables that SILO DataDrill does not provide:
    dewpoint_temperature_2m_mean/min/max     (degC)
    surface_net_solar_radiation_mean/min/max (W/m2)
    surface_net_thermal_radiation_mean/min/max (W/m2)
    surface_pressure_mean/min/max            (kPa)
    u_component_of_wind_10m_mean/min/max     (m/s)
    v_component_of_wind_10m_mean/min/max     (m/s)
    snow_depth_water_equivalent_mean/min/max (mm)
    volumetric_soil_water_layer_1_mean/min/max (m3/m3)
    volumetric_soil_water_layer_2_mean/min/max (m3/m3)
    volumetric_soil_water_layer_3_mean/min/max (m3/m3)
    volumetric_soil_water_layer_4_mean/min/max (m3/m3)

Must be run after:
    python fetch_maribyrnong.py

Requirements:
    pip install earthengine-api

First-time setup (one-off, opens browser for Google sign-in):
    earthengine authenticate

Usage:
    python fetch_era5land.py
"""

import csv
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from gauges_config import GAUGES

# ── Paths ──────────────────────────────────────────────────────────────────────

OUT_DIR = Path("caravan_maribyrnong")
TS_DIR  = OUT_DIR / "timeseries" / "csv" / "ausvic"

# ERA5-Land coverage starts 1950; fetch from 1950 to maximise overlap with
# long-record gauges (e.g. Keilor 230200 which starts 1908).
ERA5_START_YEAR = 1950

# GEE daily aggregated collection (24x fewer images than hourly)
GEE_COLLECTION = "ECMWF/ERA5_LAND/DAILY_AGGR"

# Output column names (must match write_netcdf.py VAR_META keys)
INSTANT_VARS = [
    "dewpoint_temperature_2m",
    "surface_pressure",
    "u_component_of_wind_10m",
    "v_component_of_wind_10m",
    "snow_depth_water_equivalent",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4",
]
ACCUM_VARS = [
    "surface_net_solar_radiation",
    "surface_net_thermal_radiation",
]


# ── Unit converters ───────────────────────────────────────────────────────────

_UNIT_CONVERTERS = {
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
}


def convert_units(var: str, value: float) -> float:
    """Apply the ERA5-Land unit conversion for a base variable name."""
    converter = _UNIT_CONVERTERS.get(var)
    if converter is None:
        raise KeyError(f"No unit converter registered for variable: {var!r}")
    return converter(value)


# ── GEE helpers ───────────────────────────────────────────────────────────────

def init_gee():
    """Initialise GEE, authenticating if needed. Returns the ee module."""
    try:
        import ee
    except ImportError:
        print("ERROR: earthengine-api not installed.")
        print("       Run: pip install earthengine-api")
        print("       Then authenticate once with: earthengine authenticate")
        sys.exit(1)

    GEE_PROJECT = "floodhubmaribyrnong"
    print("Initialising Google Earth Engine ...")
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        print("  Not authenticated -- opening browser for Google sign-in ...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)

    return ee


# ── Band mapping: output column -> (DAILY_AGGR source band, unit converter) ──
#
# In ECMWF/ERA5_LAND/DAILY_AGGR:
#   Instantaneous state vars: bare name = daily mean (no _mean suffix),
#                             {var}_min and {var}_max also exist.
#   Accumulated flux vars:    {var}_sum  = J/m2/day (daily total)
#                             {var}_min  = J/m2/hr  (hourly minimum)
#                             {var}_max  = J/m2/hr  (hourly maximum)

BAND_MAP: dict[str, tuple[str, object]] = {
    # dewpoint temperature (K -> degC)
    "dewpoint_temperature_2m_mean": ("dewpoint_temperature_2m",     lambda v: v - 273.15),
    "dewpoint_temperature_2m_min":  ("dewpoint_temperature_2m_min", lambda v: v - 273.15),
    "dewpoint_temperature_2m_max":  ("dewpoint_temperature_2m_max", lambda v: v - 273.15),
    # surface pressure (Pa -> kPa)
    "surface_pressure_mean":        ("surface_pressure",            lambda v: v / 1000.0),
    "surface_pressure_min":         ("surface_pressure_min",        lambda v: v / 1000.0),
    "surface_pressure_max":         ("surface_pressure_max",        lambda v: v / 1000.0),
    # wind components (m/s -- no conversion)
    "u_component_of_wind_10m_mean": ("u_component_of_wind_10m",     lambda v: v),
    "u_component_of_wind_10m_min":  ("u_component_of_wind_10m_min", lambda v: v),
    "u_component_of_wind_10m_max":  ("u_component_of_wind_10m_max", lambda v: v),
    "v_component_of_wind_10m_mean": ("v_component_of_wind_10m",     lambda v: v),
    "v_component_of_wind_10m_min":  ("v_component_of_wind_10m_min", lambda v: v),
    "v_component_of_wind_10m_max":  ("v_component_of_wind_10m_max", lambda v: v),
    # snow depth water equivalent (m -> mm)
    "snow_depth_water_equivalent_mean": ("snow_depth_water_equivalent",     lambda v: v * 1000.0),
    "snow_depth_water_equivalent_min":  ("snow_depth_water_equivalent_min", lambda v: v * 1000.0),
    "snow_depth_water_equivalent_max":  ("snow_depth_water_equivalent_max", lambda v: v * 1000.0),
    # volumetric soil water layers (m3/m3 -- no conversion)
    "volumetric_soil_water_layer_1_mean": ("volumetric_soil_water_layer_1",     lambda v: v),
    "volumetric_soil_water_layer_1_min":  ("volumetric_soil_water_layer_1_min", lambda v: v),
    "volumetric_soil_water_layer_1_max":  ("volumetric_soil_water_layer_1_max", lambda v: v),
    "volumetric_soil_water_layer_2_mean": ("volumetric_soil_water_layer_2",     lambda v: v),
    "volumetric_soil_water_layer_2_min":  ("volumetric_soil_water_layer_2_min", lambda v: v),
    "volumetric_soil_water_layer_2_max":  ("volumetric_soil_water_layer_2_max", lambda v: v),
    "volumetric_soil_water_layer_3_mean": ("volumetric_soil_water_layer_3",     lambda v: v),
    "volumetric_soil_water_layer_3_min":  ("volumetric_soil_water_layer_3_min", lambda v: v),
    "volumetric_soil_water_layer_3_max":  ("volumetric_soil_water_layer_3_max", lambda v: v),
    "volumetric_soil_water_layer_4_mean": ("volumetric_soil_water_layer_4",     lambda v: v),
    "volumetric_soil_water_layer_4_min":  ("volumetric_soil_water_layer_4_min", lambda v: v),
    "volumetric_soil_water_layer_4_max":  ("volumetric_soil_water_layer_4_max", lambda v: v),
    # surface net solar radiation:
    #   _sum  (J/m2/day) -> daily mean W/m2 = sum / 86400
    #   _min/_max (J/m2/hr) -> W/m2 = value / 3600
    "surface_net_solar_radiation_mean":   ("surface_net_solar_radiation_sum",  lambda v: v / 86400.0),
    "surface_net_solar_radiation_min":    ("surface_net_solar_radiation_min",  lambda v: v / 3600.0),
    "surface_net_solar_radiation_max":    ("surface_net_solar_radiation_max",  lambda v: v / 3600.0),
    # surface net thermal radiation (same convention as solar)
    "surface_net_thermal_radiation_mean": ("surface_net_thermal_radiation_sum", lambda v: v / 86400.0),
    "surface_net_thermal_radiation_min":  ("surface_net_thermal_radiation_min", lambda v: v / 3600.0),
    "surface_net_thermal_radiation_max":  ("surface_net_thermal_radiation_max", lambda v: v / 3600.0),
}


def fetch_era5land_year(ee, lat: float, lon: float, year: int) -> list[dict]:
    """
    Fetch daily ERA5-Land statistics for one year at a point via getRegion,
    using ECMWF/ERA5_LAND/DAILY_AGGR (365 images per year, pre-aggregated).

    Returns a list of dicts keyed by Caravan output column names.
    """
    start = f"{year}-01-01"
    end   = f"{year + 1}-01-01"

    point = ee.Geometry.Point([lon, lat])

    # Unique source bands needed (may have duplicates when _sum maps to mean)
    source_bands = list(dict.fromkeys(src for src, _ in BAND_MAP.values()))

    daily_col = (
        ee.ImageCollection(GEE_COLLECTION)
          .filterDate(start, end)
          .select(source_bands)
    )

    # getRegion returns [[header], [row], [row], ...]
    region = daily_col.getRegion(point, scale=9000).getInfo()
    if not region or len(region) < 2:
        return []

    header = region[0]   # ['id', 'longitude', 'latitude', 'time', band1, ...]
    rows   = region[1:]

    result = []
    for row in rows:
        if None in row:
            continue
        row_dict = dict(zip(header, row))
        ts_ms    = row_dict.get("time")
        if ts_ms is None:
            continue
        # timedelta-based conversion handles pre-1970 timestamps on Windows
        # (datetime.fromtimestamp() raises OSError for negative values there)
        from datetime import timedelta
        dt       = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ts_ms)
        date_str = dt.strftime("%Y-%m-%d")

        rec = {"date": date_str}
        for out_col, (src_band, converter) in BAND_MAP.items():
            val = row_dict.get(src_band)
            rec[out_col] = round(converter(val), 4) if val is not None else None

        result.append(rec)

    return result


def fetch_all_era5land(ee, gauge: dict, cache_path: Path) -> dict[str, dict]:
    """
    Fetch all ERA5-Land data for a gauge from ERA5_START_YEAR to present,
    year by year. Caches to JSON so re-runs skip the download.
    Returns a dict keyed by ISO date string.
    """
    if cache_path.exists():
        print(f"    Using cache: {cache_path.name}")
        print(f"    (Delete to force fresh download)")
        with open(cache_path) as f:
            rows = json.load(f)
        return {r["date"]: r for r in rows}

    all_rows = []
    end_year = date.today().year

    for year in range(ERA5_START_YEAR, end_year + 1):
        print(f"    {year} ...", end=" ", flush=True)
        try:
            rows = fetch_era5land_year(ee, gauge["lat"], gauge["lon"], year)
            print(f"{len(rows)} days")
            all_rows.extend(rows)
        except Exception as exc:
            print(f"ERROR -- {exc}")
        time.sleep(0.5)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(all_rows, f)
    print(f"    Cached -> {cache_path.name}")

    return {r["date"]: r for r in all_rows}


# ── Merge into timeseries CSV ─────────────────────────────────────────────────

# All output column names from ERA5-Land (33 columns)
ERA5_COLS = (
    [f"{v}_{s}" for v in INSTANT_VARS for s in ("mean", "min", "max")]
    + [f"{v}_{s}" for v in ACCUM_VARS  for s in ("mean", "min", "max")]
)


def merge_era5land(gauge: dict, era5_by_date: dict[str, dict]) -> None:
    """
    Rebuild the timeseries CSV so it covers the full ERA5-Land period (1950+).

    Rows are produced for every date in era5_by_date (entire 1950-present range).
    Streamflow values are merged in from the existing CSV where available.
    Pre-1950 streamflow dates (e.g. Keilor 1908-1949) are appended as rows
    with ERA5-Land columns left empty.

    This ensures meteorological forcings exist for the full date range, not
    just the period that overlaps with streamflow records (Caravan requirement).
    """
    gid     = gauge["gauge_id"]
    ts_path = TS_DIR / f"{gid}.csv"

    # Load existing streamflow keyed by ISO date
    sf_by_date: dict[str, str] = {}
    if ts_path.exists():
        with open(ts_path, newline="") as f:
            for row in csv.DictReader(f):
                sf_by_date[row["date"]] = row.get("streamflow", "")

    all_cols = ["date", "streamflow"] + ERA5_COLS
    era5_dates = set(era5_by_date.keys())

    # ── 1. ERA5 spine (1950+): streamflow merged in where available ───────────
    matched = 0
    merged: list[dict] = []
    for date_str in sorted(era5_dates):
        era5 = era5_by_date[date_str]
        sf   = sf_by_date.get(date_str, "")
        if sf:
            matched += 1
        new_row = {"date": date_str, "streamflow": sf}
        for col in ERA5_COLS:
            val = era5.get(col)
            new_row[col] = "" if val is None else val
        merged.append(new_row)

    # ── 2. Pre-ERA5 streamflow rows (e.g. Keilor 1908-1949) ──────────────────
    pre_era5 = [
        {"date": d, "streamflow": sf, **{c: "" for c in ERA5_COLS}}
        for d, sf in sorted(sf_by_date.items())
        if d not in era5_dates and sf
    ]
    merged = pre_era5 + merged   # pre-1950 first, then 1950+ (already sorted)

    print(f"    Streamflow days matched with ERA5: {matched} / {len(sf_by_date)}")
    print(f"    Pre-ERA5 streamflow rows: {len(pre_era5)}")
    print(f"    Total rows in output CSV: {len(merged)}")

    with open(ts_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols)
        writer.writeheader()
        writer.writerows(merged)
    print(f"    Timeseries written -> {ts_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching ERA5-Land variables via Google Earth Engine\n")

    ee = init_gee()

    for gauge in GAUGES:
        gid = gauge["gauge_id"]
        print(f"\n{'-' * 60}")
        print(f"ERA5-Land: {gauge['name']} ({gauge['station_id']})")
        print(f"{'-' * 60}")

        if gauge["lat"] is None or gauge["lon"] is None:
            print("  Skipping -- lat/lon not set in gauges_config.py")
            continue

        cache_path = OUT_DIR / f"era5land_cache_{gid}.json"
        print(f"  Fetching ERA5-Land at ({gauge['lat']}, {gauge['lon']}) "
              f"from {ERA5_START_YEAR} ...")

        era5_by_date = fetch_all_era5land(ee, gauge, cache_path)
        print(f"  Total ERA5-Land days: {len(era5_by_date)}")

        merge_era5land(gauge, era5_by_date)

    print(f"""
{'=' * 60}
 ERA5-Land merge complete.
 Next steps:
   python fetch_hydroatlas.py
   python fetch_catchments.py
   python write_netcdf.py
{'=' * 60}
""")


if __name__ == "__main__":
    main()
