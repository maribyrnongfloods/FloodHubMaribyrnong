#!/usr/bin/env python3
"""
fetch_era5land.py

Fetches daily ERA5-Land meteorological variables at each gauge location via
Google Earth Engine and merges them into the existing timeseries CSVs.

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
    python fetch_silo_met.py --username your@email.com

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
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from gauges_config import GAUGES

# ── Paths ──────────────────────────────────────────────────────────────────────

OUT_DIR = Path("caravan_maribyrnong")
TS_DIR  = OUT_DIR / "timeseries" / "csv" / "aus_vic"

# ERA5-Land coverage starts 1950; fetch from 1981 to match Caravan standard
ERA5_START_YEAR = 1981

# ── ERA5-Land variable definitions ────────────────────────────────────────────

# Instantaneous variables: aggregate to daily mean/min/max
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

# Accumulated variables: represent hourly flux/radiation; aggregate to daily
# mean W/m² by averaging all 24 hourly J/m² values and dividing by 3600.
# (Each ERA5-Land image holds J/m² accumulated since the previous hour.)
ACCUM_VARS = [
    "surface_net_solar_radiation",
    "surface_net_thermal_radiation",
]

ALL_GEE_VARS = INSTANT_VARS + ACCUM_VARS

# ── Unit conversions applied after aggregation ────────────────────────────────

def convert_units(var: str, value: float) -> float:
    """Convert from ERA5-Land native units to Caravan output units."""
    if var in ("dewpoint_temperature_2m",):
        return value - 273.15                   # K → °C
    if var == "surface_pressure":
        return value / 1000.0                   # Pa → kPa
    if var == "snow_depth_water_equivalent":
        return value * 1000.0                   # m → mm
    if var in ("surface_net_solar_radiation", "surface_net_thermal_radiation"):
        return value / 3600.0                   # J/m² per hour → W/m²
    return value                                # m³/m³ and m/s — no change


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
        print("  Not authenticated — opening browser for Google sign-in ...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)

    return ee


def fetch_era5land_year(ee, lat: float, lon: float, year: int) -> list[dict]:
    """
    Fetch all ERA5-Land hourly records for one year at a point via getRegion,
    then aggregate client-side to daily mean/min/max.

    Returns a list of dicts keyed by Caravan output column names.
    """
    start = f"{year}-01-01"
    end   = f"{year + 1}-01-01"

    point = ee.Geometry.Point([lon, lat])
    era5  = (
        ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
          .filterDate(start, end)
          .select(ALL_GEE_VARS)
    )

    # getRegion returns [[header], [row], [row], ...]
    region = era5.getRegion(point, scale=9000).getInfo()
    if not region or len(region) < 2:
        return []

    header = region[0]   # ['id', 'longitude', 'latitude', 'time', var1, ...]
    rows   = region[1:]

    # Group hourly values by UTC date
    daily: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for row in rows:
        if None in row:
            continue
        row_dict = dict(zip(header, row))
        ts_ms    = row_dict.get("time")
        if ts_ms is None:
            continue
        dt       = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        for var in ALL_GEE_VARS:
            val = row_dict.get(var)
            if val is not None:
                daily[date_str][var].append(float(val))

    # Aggregate to daily and apply unit conversions
    result = []
    for date_str in sorted(daily):
        rec = {"date": date_str}
        hourly = daily[date_str]

        for var in INSTANT_VARS:
            vals = hourly.get(var, [])
            if vals:
                rec[f"{var}_mean"] = round(convert_units(var, sum(vals) / len(vals)), 4)
                rec[f"{var}_min"]  = round(convert_units(var, min(vals)), 4)
                rec[f"{var}_max"]  = round(convert_units(var, max(vals)), 4)
            else:
                rec[f"{var}_mean"] = None
                rec[f"{var}_min"]  = None
                rec[f"{var}_max"]  = None

        for var in ACCUM_VARS:
            vals = hourly.get(var, [])
            if vals:
                # Average W/m² over the day
                avg_wm2 = sum(convert_units(var, v) for v in vals) / len(vals)
                rec[f"{var}_mean"] = round(avg_wm2, 4)
                rec[f"{var}_min"]  = round(min(convert_units(var, v) for v in vals), 4)
                rec[f"{var}_max"]  = round(max(convert_units(var, v) for v in vals), 4)
            else:
                rec[f"{var}_mean"] = None
                rec[f"{var}_min"]  = None
                rec[f"{var}_max"]  = None

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
            print(f"ERROR — {exc}")
        time.sleep(1)

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
    """Merge ERA5-Land columns into the existing timeseries CSV for one gauge."""
    gid     = gauge["gauge_id"]
    ts_path = TS_DIR / f"{gid}.csv"

    if not ts_path.exists():
        print(f"    ERROR: {ts_path} not found — run fetch_maribyrnong.py first.")
        return

    with open(ts_path, newline="") as f:
        flow_rows = list(csv.DictReader(f))

    if not flow_rows:
        print("    WARNING: timeseries CSV is empty.")
        return

    # Determine existing columns (avoid duplicating ERA5 cols if re-run)
    existing_cols = list(flow_rows[0].keys())
    new_cols      = [c for c in ERA5_COLS if c not in existing_cols]
    all_cols      = existing_cols + new_cols

    matched = 0
    merged  = []
    for row in flow_rows:
        era5 = era5_by_date.get(row["date"], {})
        if era5:
            matched += 1
        new_row = dict(row)
        for col in new_cols:
            val = era5.get(col)
            new_row[col] = "" if val is None else val
        merged.append(new_row)

    print(f"    Rows matched with ERA5-Land: {matched} / {len(flow_rows)}")

    with open(ts_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols)
        writer.writeheader()
        writer.writerows(merged)
    print(f"    Timeseries updated -> {ts_path}")


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
            print("  Skipping — lat/lon not set in gauges_config.py")
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
