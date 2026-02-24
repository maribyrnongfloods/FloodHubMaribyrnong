#!/usr/bin/env python3
"""
write_netcdf.py

Reads the merged timeseries CSVs produced by fetch_maribyrnong.py +
fetch_era5land.py and writes Caravan-format netCDF4 files, one per gauge.

Must be run AFTER:
    python fetch_maribyrnong.py
    python fetch_era5land.py

Output structure:
    caravan_maribyrnong/
        timeseries/netcdf/ausvic/
            ausvic_230200.nc
            ausvic_230106.nc

Requirements
------------
    pip install xarray netCDF4 numpy

Usage
-----
    python write_netcdf.py
"""

import csv
from datetime import datetime
from pathlib import Path

from gauges_config import GAUGES

# ── Paths ─────────────────────────────────────────────────────────────────────

OUT_DIR          = Path("caravan_maribyrnong")
CSV_DIR          = OUT_DIR / "timeseries" / "csv"    / "ausvic"
NETCDF_DIR       = OUT_DIR / "timeseries" / "netcdf" / "ausvic"
CARAVAN_ATTR     = OUT_DIR / "attributes" / "ausvic" / "attributes_caravan_ausvic.csv"
OTHER_ATTR       = OUT_DIR / "attributes" / "ausvic" / "attributes_other_ausvic.csv"

# ── Variable metadata (units + long names for netCDF attributes) ───────────────

VAR_META = {
    # ── Streamflow ────────────────────────────────────────────────────────────
    "streamflow": {
        "units":      "mm/d",
        "long_name":  "Observed daily streamflow (depth over catchment area)",
        "_FillValue": -9999.0,
    },
    # ── ERA5-Land forcing (added by fetch_era5land.py) ────────────────────────
    # SILO columns have been removed per Caravan reviewer feedback (Feb 2026):
    # SILO is an Australian-only product; Caravan requires globally available data.
    # ── 2m air temperature ────────────────────────────────────────────────────
    "temperature_2m_mean": {
        "units":      "degC",
        "long_name":  "Daily mean 2-m air temperature (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "temperature_2m_min": {
        "units":      "degC",
        "long_name":  "Daily minimum 2-m air temperature (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "temperature_2m_max": {
        "units":      "degC",
        "long_name":  "Daily maximum 2-m air temperature (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    # ── 2m dewpoint temperature ───────────────────────────────────────────────
    "dewpoint_temperature_2m_mean": {
        "units":      "degC",
        "long_name":  "Daily mean 2-m dewpoint temperature (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "dewpoint_temperature_2m_min": {
        "units":      "degC",
        "long_name":  "Daily minimum 2-m dewpoint temperature (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "dewpoint_temperature_2m_max": {
        "units":      "degC",
        "long_name":  "Daily maximum 2-m dewpoint temperature (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_net_solar_radiation_mean": {
        "units":      "W/m2",
        "long_name":  "Daily mean surface net solar radiation (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_net_solar_radiation_min": {
        "units":      "W/m2",
        "long_name":  "Daily minimum surface net solar radiation (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_net_solar_radiation_max": {
        "units":      "W/m2",
        "long_name":  "Daily maximum surface net solar radiation (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_net_thermal_radiation_mean": {
        "units":      "W/m2",
        "long_name":  "Daily mean surface net thermal radiation (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_net_thermal_radiation_min": {
        "units":      "W/m2",
        "long_name":  "Daily minimum surface net thermal radiation (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_net_thermal_radiation_max": {
        "units":      "W/m2",
        "long_name":  "Daily maximum surface net thermal radiation (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_pressure_mean": {
        "units":      "kPa",
        "long_name":  "Daily mean surface pressure (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_pressure_min": {
        "units":      "kPa",
        "long_name":  "Daily minimum surface pressure (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "surface_pressure_max": {
        "units":      "kPa",
        "long_name":  "Daily maximum surface pressure (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "u_component_of_wind_10m_mean": {
        "units":      "m/s",
        "long_name":  "Daily mean 10-m U-component of wind (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "u_component_of_wind_10m_min": {
        "units":      "m/s",
        "long_name":  "Daily minimum 10-m U-component of wind (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "u_component_of_wind_10m_max": {
        "units":      "m/s",
        "long_name":  "Daily maximum 10-m U-component of wind (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "v_component_of_wind_10m_mean": {
        "units":      "m/s",
        "long_name":  "Daily mean 10-m V-component of wind (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "v_component_of_wind_10m_min": {
        "units":      "m/s",
        "long_name":  "Daily minimum 10-m V-component of wind (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "v_component_of_wind_10m_max": {
        "units":      "m/s",
        "long_name":  "Daily maximum 10-m V-component of wind (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "snow_depth_water_equivalent_mean": {
        "units":      "mm",
        "long_name":  "Daily mean snow depth water equivalent (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "snow_depth_water_equivalent_min": {
        "units":      "mm",
        "long_name":  "Daily minimum snow depth water equivalent (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "snow_depth_water_equivalent_max": {
        "units":      "mm",
        "long_name":  "Daily maximum snow depth water equivalent (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_1_mean": {
        "units":      "m3/m3",
        "long_name":  "Daily mean volumetric soil water layer 1 0-7 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_1_min": {
        "units":      "m3/m3",
        "long_name":  "Daily minimum volumetric soil water layer 1 0-7 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_1_max": {
        "units":      "m3/m3",
        "long_name":  "Daily maximum volumetric soil water layer 1 0-7 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_2_mean": {
        "units":      "m3/m3",
        "long_name":  "Daily mean volumetric soil water layer 2 7-28 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_2_min": {
        "units":      "m3/m3",
        "long_name":  "Daily minimum volumetric soil water layer 2 7-28 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_2_max": {
        "units":      "m3/m3",
        "long_name":  "Daily maximum volumetric soil water layer 2 7-28 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_3_mean": {
        "units":      "m3/m3",
        "long_name":  "Daily mean volumetric soil water layer 3 28-100 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_3_min": {
        "units":      "m3/m3",
        "long_name":  "Daily minimum volumetric soil water layer 3 28-100 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_3_max": {
        "units":      "m3/m3",
        "long_name":  "Daily maximum volumetric soil water layer 3 28-100 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_4_mean": {
        "units":      "m3/m3",
        "long_name":  "Daily mean volumetric soil water layer 4 100-289 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_4_min": {
        "units":      "m3/m3",
        "long_name":  "Daily minimum volumetric soil water layer 4 100-289 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "volumetric_soil_water_layer_4_max": {
        "units":      "m3/m3",
        "long_name":  "Daily maximum volumetric soil water layer 4 100-289 cm (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    # ── Precipitation and evaporation (daily totals) ──────────────────────────
    "total_precipitation_sum": {
        "units":      "mm/d",
        "long_name":  "Daily total precipitation (ERA5-Land)",
        "_FillValue": -9999.0,
    },
    "potential_evaporation_sum_ERA5_LAND": {
        "units":      "mm/d",
        "long_name":  "Daily potential evaporation (ERA5-Land, original)",
        "_FillValue": -9999.0,
    },
    "potential_evaporation_sum_FAO_PENMAN_MONTEITH": {
        "units":      "mm/d",
        "long_name":  "Daily reference ET (FAO-56 Penman-Monteith, computed from ERA5-Land)",
        "_FillValue": -9999.0,
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_attributes() -> dict[str, dict]:
    """
    Load and merge caravan + other attribute CSVs, keyed by gauge_id.
    caravan attrs hold climate stats; other attrs hold gauge metadata
    including streamflow_period and streamflow_missing.
    """
    merged: dict[str, dict] = {}
    for path in (CARAVAN_ATTR, OTHER_ATTR):
        if path.exists():
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    gid = row.get("gauge_id", "")
                    if gid:
                        merged.setdefault(gid, {}).update(row)
    return merged


def read_csv(csv_path: Path) -> tuple[list, dict[str, list]]:
    """
    Read a merged timeseries CSV.
    Returns (dates_as_datetime, {column_name: [float|None, ...]}).
    """
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"Empty CSV: {csv_path}")

    dates = [datetime.strptime(r["date"], "%Y-%m-%d") for r in rows]
    data_cols = {k: [] for k in rows[0] if k != "date"}

    for row in rows:
        for col in data_cols:
            raw = row.get(col, "")
            try:
                data_cols[col].append(float(raw))
            except (ValueError, TypeError):
                data_cols[col].append(None)   # becomes _FillValue in netCDF

    return dates, data_cols


def write_nc(gauge: dict, attrs: dict) -> Path:
    """Write one netCDF file for the given gauge. Returns the output path."""
    try:
        import numpy as np
        import xarray as xr
    except ImportError:
        print("ERROR: xarray and numpy are required.")
        print("       Run: pip install xarray netCDF4 numpy")
        raise SystemExit(1)

    gid      = gauge["gauge_id"]
    csv_path = CSV_DIR / f"{gid}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Timeseries CSV not found: {csv_path}\n"
            "Run fetch_maribyrnong.py and fetch_era5land.py first."
        )

    dates, data_cols = read_csv(csv_path)

    # Build xarray data variables
    data_vars = {}
    for col, values in data_cols.items():
        meta    = VAR_META.get(col, {})
        fill    = meta.get("_FillValue", -9999.0)
        arr     = np.array(
            [fill if v is None else v for v in values],
            dtype=np.float32,
        )
        da = xr.DataArray(
            arr,
            dims=["date"],
            attrs={
                k: v for k, v in meta.items() if k != "_FillValue"
            },
        )
        data_vars[col] = da

    ds = xr.Dataset(data_vars, coords={"date": dates})

    # Global attributes (Caravan convention)
    ds.attrs = {
        "gauge_id":          gid,
        "gauge_name":        gauge["name"],
        "gauge_lat":         gauge["lat"],
        "gauge_lon":         gauge["lon"],
        "area_km2":          gauge["area_km2"] if gauge["area_km2"] else "unknown",
        "country":           "AUS",
        "streamflow_source": (
            f"Melbourne Water public API (api.melbournewater.com.au), "
            f"Station {gauge['station_id']}"
            if gauge["api"] == "melbwater"
            else f"Victorian Water Monitoring (data.water.vic.gov.au), "
                 f"Station {gauge['station_id']}"
        ),
        "met_source":        "ERA5-Land via Google Earth Engine (ECMWF/ERA5_LAND/DAILY_AGGR)",
        "license":           "CC-BY-4.0",
        "notes":             gauge.get("notes", ""),
        "created":           datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Conventions":       "CF-1.8",
    }

    # Merge computed climate indices (from compute_attributes.py) and gauge
    # metadata (from fetch_maribyrnong.py) into global netCDF attributes.
    if gid in attrs:
        caravan_keys = (
            "p_mean", "pet_mean_ERA5_LAND", "pet_mean_FAO_PM",
            "aridity_ERA5_LAND", "aridity_FAO_PM",
            "frac_snow",
            "moisture_index_ERA5_LAND", "seasonality_ERA5_LAND",
            "moisture_index_FAO_PM",    "seasonality_FAO_PM",
            "high_prec_freq", "high_prec_dur",
            "low_prec_freq",  "low_prec_dur",
            "streamflow_period", "streamflow_missing",
        )
        for key in caravan_keys:
            val = attrs[gid].get(key, "")
            if val:
                ds.attrs[key] = val

    out_path = NETCDF_DIR / f"{gid}.nc"
    ds.to_netcdf(
        out_path,
        encoding={
            col: {"dtype": "float32", "_FillValue": VAR_META.get(col, {}).get("_FillValue", -9999.0)}
            for col in data_vars
        },
    )
    return out_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Writing Caravan netCDF timeseries files\n")

    NETCDF_DIR.mkdir(parents=True, exist_ok=True)

    attrs   = load_attributes()
    written = []

    for gauge in GAUGES:
        gid = gauge["gauge_id"]
        print(f"{'-' * 60}")
        print(f"Gauge: {gauge['name']} ({gauge['station_id']})")

        try:
            out_path = write_nc(gauge, attrs)
            print(f"  Written -> {out_path}")
            written.append(out_path)
        except FileNotFoundError as exc:
            print(f"  SKIP — {exc}")
        except Exception as exc:
            print(f"  ERROR — {exc}")

    print(f"""
{'=' * 60}
 netCDF files written: {len(written)}
""" + "\n".join(f"   {p}" for p in written) + f"""

 Next steps:
   python fetch_catchments.py         (catchment boundary shapefiles)
   python generate_license.py         (license markdown file)
   -> then upload everything to Zenodo and open a GitHub issue at
     https://github.com/kratzert/Caravan
{'=' * 60}
""")


if __name__ == "__main__":
    main()
