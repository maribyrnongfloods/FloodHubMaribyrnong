#!/usr/bin/env python3
"""
fetch_hydroatlas.py

Extracts HydroATLAS BasinATLAS level-12 attributes for every gauge defined
in gauges_config.py using the Google Earth Engine Python API, and writes
them in Caravan format.

No large file downloads required — GEE hosts the full HydroATLAS dataset.

Requirements:
    pip install earthengine-api

First-time setup (one-off, opens browser for Google sign-in):
    earthengine authenticate

Usage:
    python fetch_hydroatlas.py

Output:
    caravan_maribyrnong/attributes/attributes_hydroatlas_aus_vic.csv

If you prefer not to use GEE, see the fallback at the bottom of this file
for instructions on using the downloaded shapefile with geopandas instead.
"""

import csv
import json
import sys
from pathlib import Path

from gauges_config import GAUGES

# ── Constants ─────────────────────────────────────────────────────────────────
# GEE asset — HydroATLAS BasinATLAS level 12 (finest resolution)
GEE_ASSET = "WWF/HydroATLAS/v1/Basins/level12"

OUT_PATH  = Path("caravan_maribyrnong/attributes/attributes_hydroatlas_aus_vic.csv")


# ── GEE query ─────────────────────────────────────────────────────────────────

def init_gee() -> object:
    """Initialise GEE, authenticating if needed. Returns the ee module."""
    try:
        import ee
    except ImportError:
        print("ERROR: earthengine-api not installed.")
        print("       Run: pip install earthengine-api")
        print("       Then authenticate once with: earthengine authenticate")
        sys.exit(1)

    print("Initialising Google Earth Engine ...")
    try:
        ee.Initialize()
    except Exception:
        print("  Not authenticated — opening browser for Google sign-in ...")
        ee.Authenticate()
        ee.Initialize()

    return ee


def fetch_basin_props(ee, lat: float, lon: float) -> dict:
    """
    Find the level-12 HydroATLAS basin containing (lat, lon) and return
    all its attributes.
    """
    print(f"  Querying {GEE_ASSET} at ({lat}, {lon}) ...")
    point  = ee.Geometry.Point([lon, lat])
    basins = ee.FeatureCollection(GEE_ASSET)
    match  = basins.filterBounds(point).first()
    info   = match.getInfo()

    if info is None:
        raise RuntimeError(f"No HydroATLAS basin found at ({lat}, {lon})")

    props = info.get("properties", {})
    print(f"  Matched HYBAS_ID:    {props.get('HYBAS_ID', 'unknown')}")
    print(f"  Sub-basin area:      {props.get('SUB_AREA', 'unknown')} km²")
    print(f"  Upstream area:       {props.get('UP_AREA', 'unknown')} km²")
    print(f"  Attributes returned: {len(props)}")
    return props


# ── Write Caravan attributes CSV ──────────────────────────────────────────────

def build_attrs_row(gauge_id: str, props: dict) -> dict:
    """
    Build an attributes dict for one gauge: gauge_id first, then all
    HydroATLAS properties (sorted, lower-cased, geometry columns excluded).
    """
    skip = {"geometry", "shape_area", "shape_leng"}
    row  = {"gauge_id": gauge_id}
    for key in sorted(props.keys()):
        if key.lower() not in skip:
            row[key.lower()] = props[key]
    return row


def backfill_area_in_config(station_id: str, up_area: float) -> None:
    """
    If a gauge has area_km2=None in gauges_config.py, replace it with the
    HydroATLAS UP_AREA value and save the file.

    Finds the station block by station_id, then replaces the first
    'area_km2':     None  line that follows it.
    """
    config_path = Path(__file__).parent / "gauges_config.py"
    text = config_path.read_text(encoding="utf-8")

    # Locate the station_id marker and the area_km2 None line after it
    station_marker = f'"{station_id}"'
    station_pos = text.find(station_marker)
    if station_pos == -1:
        print(f"  WARNING: station_id {station_id} not found in gauges_config.py")
        return

    area_none = '"area_km2":     None,'
    none_pos = text.find(area_none, station_pos)
    if none_pos == -1:
        print(f"  area_km2 for {station_id} is already set — skipping auto-fill.")
        return

    replacement = f'"area_km2":     {up_area},  # from HydroATLAS UP_AREA'
    new_text = text[:none_pos] + replacement + text[none_pos + len(area_none):]
    config_path.write_text(new_text, encoding="utf-8")
    print(f"  gauges_config.py updated: area_km2 = {up_area} km²  (HydroATLAS UP_AREA)")


def write_csv(rows: list[dict]) -> None:
    """Write all gauge rows to the Caravan HydroATLAS attributes CSV."""
    # Union of all column names (gauges may have slightly different sets)
    all_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWritten -> {OUT_PATH}")
    print(f"  {len(rows)} gauge(s), {len(all_keys) - 1} HydroATLAS columns")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching HydroATLAS attributes via Google Earth Engine\n")

    ee = init_gee()

    attr_rows:  list[dict] = []
    json_dir = OUT_PATH.parent

    for gauge in GAUGES:
        gid = gauge["gauge_id"]
        print(f"\n{'─' * 60}")
        print(f"Gauge: {gauge['name']} ({gauge['station_id']})")
        print(f"{'─' * 60}")

        if gauge["lat"] is None or gauge["lon"] is None:
            print("  Skipping — lat/lon not set in gauges_config.py")
            continue

        try:
            props = fetch_basin_props(ee, gauge["lat"], gauge["lon"])
        except Exception as exc:
            print(f"  ERROR — {exc}")
            continue

        attr_rows.append(build_attrs_row(gid, props))

        # Auto-fill area_km2 in gauges_config.py if it was None
        if gauge.get("area_km2") is None:
            up_area = props.get("UP_AREA")
            if up_area is not None:
                backfill_area_in_config(gauge["station_id"], up_area)
            else:
                print("  WARNING: UP_AREA not in HydroATLAS response — "
                      "set area_km2 manually in gauges_config.py")

        # Save raw JSON per gauge for reference
        json_dir.mkdir(parents=True, exist_ok=True)
        raw_path = json_dir / f"hydroatlas_raw_{gid}.json"
        raw_path.write_text(json.dumps(props, indent=2))
        print(f"  Raw JSON -> {raw_path.name}")

    if attr_rows:
        write_csv(attr_rows)

    print(f"""
{'═' * 60}
 HydroATLAS extraction complete ({len(attr_rows)} gauge(s)).

 All three Caravan attribute files are now ready:
   attributes_caravan_aus_vic.csv     ← core attributes
   attributes_hydroatlas_aus_vic.csv  ← HydroATLAS (just written)

 Caravan submission checklist:
   ✓  fetch_maribyrnong.py  (streamflow timeseries)
   ✓  fetch_silo_met.py     (met data + climate attributes)
   ✓  fetch_hydroatlas.py   (this script)
   ☐  Fork https://github.com/kratzert/Caravan
   ☐  Copy caravan_maribyrnong/ into the repo structure
   ☐  Open a pull request
{'═' * 60}
""")


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════════
# FALLBACK: geopandas approach (if you prefer not to use GEE)
# ══════════════════════════════════════════════════════════════════════════════
#
# 1. Download BasinATLAS_Data_v10_shp.zip (~4 GB) from:
#    https://www.hydrosheds.org/products/hydroatlas
#    (free account required)
#
# 2. Unzip it and note the path to BasinATLAS_v10_lev12_v10.shp
#
# 3. Install geopandas:
#    pip install geopandas
#
# 4. Replace main() with:
#
#   import geopandas as gpd
#   from shapely.geometry import Point
#
#   shp = "path/to/BasinATLAS_v10_lev12_v10.shp"
#   gdf = gpd.read_file(shp)
#   if gdf.crs.to_epsg() != 4326:
#       gdf = gdf.to_crs(epsg=4326)
#   pt = Point(LON, LAT)
#   match = gdf[gdf.contains(pt)]
#   if match.empty:
#       match = gdf.iloc[[gdf.geometry.distance(pt).argmin()]]
#   props = match.iloc[0].drop("geometry").to_dict()
#   write_csv(props)
#
# ══════════════════════════════════════════════════════════════════════════════
