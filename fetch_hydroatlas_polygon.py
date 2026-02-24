#!/usr/bin/env python3
"""
fetch_hydroatlas_polygon.py

Replicates the HydroATLAS extraction step from the official Caravan Part-1
Colab notebook (Caravan_part1_Earth_Engine.ipynb) entirely from the command
line via the Google Earth Engine Python API + shapely.

This script is the AUTHORITATIVE HydroATLAS step for the ausvic pipeline.
It replaces the old fetch_hydroatlas.py (which was point-based and produced
non-standard columns) and removes the need to run the Colab notebook manually.

Method (matches official notebook logic):
-----------------------------------------
1. For each gauge, derive the upstream catchment polygon via BFS upstream
   trace through HydroBASINS Level-12 (same method as fetch_catchments.py).
2. Find all BasinATLAS Level-12 features intersecting the catchment polygon.
3. Compute intersection area via shapely (WGS84 degrees — used as relative
   weight only, matching notebook's "Intersect" column semantics).
4. Area-weight all 294 BasinATLAS numeric properties across intersecting
   sub-basins.
5. Write attributes_hydroatlas_ausvic.csv:
       gauge_id  +  294 BasinATLAS properties  =  295 columns total
       (Caravan standard: CARAVAN_HYDROATLAS_COL_COUNT = 295)

Basin size configuration (per official notebook CONFIGURATION dict):
    All Maribyrnong gauges are < 2000 km², so:
        hydroatlas_level  = Level-12
        min_overlap_threshold = 0 km²  (include ALL intersecting sub-basins)

Requirements:
    pip install earthengine-api geopandas

GEE project: floodhubmaribyrnong

Usage:
    python fetch_hydroatlas_polygon.py
"""

import csv
import sys
from pathlib import Path

from gauges_config import GAUGES

# ── Constants ─────────────────────────────────────────────────────────────────

GEE_BASINS  = "WWF/HydroSHEDS/v1/Basins/hybas_12"   # for catchment tracing
GEE_ATLAS   = "WWF/HydroATLAS/v1/Basins/level12"    # for attribute extraction
GEE_PROJECT = "floodhubmaribyrnong"

OUT_PATH = Path(
    "caravan_maribyrnong/attributes/ausvic/attributes_hydroatlas_ausvic.csv"
)

# Per official notebook: catchments < 2000 km² → Level-12, threshold = 0 km²
MIN_OVERLAP_THRESHOLD_KM2 = 0


# ── GEE initialisation ────────────────────────────────────────────────────────

def init_gee():
    try:
        import ee
    except ImportError:
        print("ERROR: earthengine-api not installed.")
        print("       Run: pip install earthengine-api")
        sys.exit(1)

    print("Initialising Google Earth Engine ...")
    try:
        ee.Initialize(project=GEE_PROJECT)
        print("  OK")
    except Exception:
        print("  Not authenticated - opening browser for Google sign-in ...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)

    return ee


# ── Step 1: BFS upstream trace → catchment polygon ───────────────────────────

def trace_catchment(ee, lat: float, lon: float) -> tuple:
    """
    BFS upstream trace through HydroBASINS Level-12.

    Returns
    -------
    catchment_geom_json : dict
        GeoJSON geometry of the upstream union polygon.
    up_area_km2 : float
        HydroBASINS UP_AREA at the outlet (km²).
    """
    basins = ee.FeatureCollection(GEE_BASINS)
    point  = ee.Geometry.Point([lon, lat])

    # Outlet basin
    outlet_info = basins.filterBounds(point).first().getInfo()
    if outlet_info is None:
        raise RuntimeError(f"No HydroBASINS basin found at ({lat}, {lon})")

    props     = outlet_info["properties"]
    outlet_id = props["HYBAS_ID"]
    up_area   = props["UP_AREA"]
    print(f"  Outlet HYBAS_ID : {outlet_id}")
    print(f"  UP_AREA         : {up_area:.1f} km2")

    # BFS
    all_ids:  set = {outlet_id}
    frontier: set = {outlet_id}
    iteration = 0
    while frontier:
        iteration += 1
        parents    = basins.filter(
            ee.Filter.inList("NEXT_DOWN", list(frontier))
        )
        parent_ids = set(parents.aggregate_array("HYBAS_ID").getInfo())
        new_ids    = parent_ids - all_ids
        print(f"    Iter {iteration}: +{len(new_ids)} basins "
              f"(running total {len(all_ids) + len(new_ids)})")
        if not new_ids:
            break
        all_ids.update(new_ids)
        frontier = new_ids

    print(f"  Total sub-basins in catchment: {len(all_ids)}")

    # Union
    print("  Unioning polygons ...")
    upstream_fc = basins.filter(ee.Filter.inList("HYBAS_ID", list(all_ids)))
    merged      = upstream_fc.union(maxError=30).first()
    return merged.geometry().getInfo(), up_area


# ── Step 2-4: BasinATLAS intersection + area-weighted averages ───────────────

def hydroatlas_weighted_attrs(ee, catchment_geom_json: dict) -> dict:
    """
    Find all BasinATLAS Level-12 features that intersect the catchment polygon,
    compute relative intersection areas (shapely, WGS84 degrees), and return
    area-weighted averages for all 294 BasinATLAS properties.

    Returns
    -------
    dict  {lowercase_property_name: area_weighted_value}  — 294 entries
    """
    try:
        from shapely.geometry import shape as to_shape
    except ImportError:
        print("ERROR: shapely not installed. Run: pip install geopandas")
        sys.exit(1)

    catchment_ee = ee.Geometry(catchment_geom_json)
    atlas        = ee.FeatureCollection(GEE_ATLAS)

    # Pull all overlapping BasinATLAS features (geometry + properties)
    print("  Querying BasinATLAS Level-12 for intersecting sub-basins ...")
    overlapping = atlas.filterBounds(catchment_ee).getInfo()["features"]
    print(f"  Candidate BasinATLAS features: {len(overlapping)}")

    if not overlapping:
        raise RuntimeError("No BasinATLAS Level-12 features intersect catchment")

    catchment_shape = to_shape(catchment_geom_json)

    weights:   list = []
    all_props: list = []

    for feat in overlapping:
        atlas_shape  = to_shape(feat["geometry"])
        intersection = catchment_shape.intersection(atlas_shape)
        area         = intersection.area   # square degrees — relative weight

        # Apply MIN_OVERLAP_THRESHOLD (0 for small catchments → keep all)
        if area <= 0:
            continue

        weights.append(area)
        all_props.append(feat["properties"])

    print(f"  Features with positive intersection: {len(weights)}")

    if not weights:
        raise RuntimeError("Zero intersection area — check gauge coordinates")

    total_weight = sum(weights)

    # All BasinATLAS Level-12 features share the same 294 properties
    prop_names = sorted(all_props[0].keys())

    result: dict = {}
    for prop in prop_names:
        values = []
        for p in all_props:
            v = p.get(prop)
            values.append(float(v) if v is not None else 0.0)
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        result[prop.lower()] = round(weighted_sum / total_weight, 6)

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("HydroATLAS polygon extraction")
    print("Replicating Caravan Part-1 Colab notebook via GEE Python API")
    print("=" * 65)
    print()

    ee = init_gee()

    rows:         list = []
    failed_gauges: list = []

    for gauge in GAUGES:
        gid = gauge["gauge_id"]
        lat = gauge.get("lat")
        lon = gauge.get("lon")

        print(f"\n{'-' * 65}")
        print(f"Gauge: {gauge['name']} ({gauge['station_id']}) -> {gid}")
        print(f"{'-' * 65}")

        if lat is None or lon is None:
            print("  Skipping - lat/lon not set in gauges_config.py")
            failed_gauges.append(gid)
            continue

        try:
            catchment_geom, up_area = trace_catchment(ee, lat, lon)
            attrs = hydroatlas_weighted_attrs(ee, catchment_geom)
        except Exception as exc:
            print(f"  ERROR - {exc}")
            failed_gauges.append(gid)
            continue

        row = {"gauge_id": gid}
        row.update(attrs)
        rows.append(row)

        n_attrs = len(attrs)
        print(f"  Area-weighted attributes: {n_attrs}")
        if n_attrs != 294:
            print(f"  [WARN] Expected 294 BasinATLAS properties, got {n_attrs}")

    if not rows:
        print("\nNo gauges processed successfully. Check errors above.")
        return

    # Column order: gauge_id first, then sorted lowercase BasinATLAS properties
    attr_cols  = sorted(set(k for row in rows for k in row if k != "gauge_id"))
    fieldnames = ["gauge_id"] + attr_cols
    total_cols = len(fieldnames)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=fieldnames, extrasaction="ignore", restval=""
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'=' * 65}")
    print(f" Written -> {OUT_PATH}")
    print(f" Rows    : {len(rows)}")
    print(f" Columns : {total_cols}  "
          f"({'OK' if total_cols == 295 else 'WARNING: expected 295'})")
    if failed_gauges:
        print(f" Failed  : {failed_gauges}")
    print(f"{'=' * 65}")
    print()
    print("Run  python verify_hydroatlas.py  to validate the output.")


if __name__ == "__main__":
    main()
