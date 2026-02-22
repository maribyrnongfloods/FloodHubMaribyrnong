#!/usr/bin/env python3
"""
fetch_catchments.py

Derives upstream catchment boundary polygons for every gauge defined in
gauges_config.py using HydroBASINS Level 12, which is already hosted in
Google Earth Engine — no large downloads required.

Method
------
1. Find the Level-12 HydroBASINS cell containing each gauge point.
2. Iteratively trace upstream through NEXT_DOWN links to collect every
   basin cell that drains to that outlet.
3. Union those cells into a single catchment polygon per gauge.
4. Write results as GeoJSON files and print instructions for GEE upload.

The exported GeoJSON can be uploaded directly to GEE as an asset and used
with the Caravan ERA5-Land forcing notebook.

Requirements
------------
    pip install earthengine-api

First-time setup (one-off, opens browser):
    earthengine authenticate

Usage
-----
    python fetch_catchments.py
"""

import json
import sys
from pathlib import Path

from gauges_config import GAUGES

# ── Constants ─────────────────────────────────────────────────────────────────

GEE_BASINS = "WWF/HydroSHEDS/v1/Basins/hybas_12"
OUT_DIR    = Path("caravan_maribyrnong/shapefiles")


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


def trace_upstream(ee, lat: float, lon: float, gauge_id: str) -> dict:
    """
    Collect every HydroBASINS Level-12 cell upstream of (lat, lon),
    union them into one polygon, and return a GeoJSON Feature with
    gauge_id attached as a property.

    Uses client-side iteration over the NEXT_DOWN link graph.
    For a ~1300 km² catchment this typically takes 3-6 GEE round-trips.
    """
    basins = ee.FeatureCollection(GEE_BASINS)
    point  = ee.Geometry.Point([lon, lat])

    # ── 1. Find the outlet basin ───────────────────────────────────────────
    print(f"  Finding outlet basin at ({lat}, {lon}) ...")
    outlet      = basins.filterBounds(point).first()
    outlet_info = outlet.getInfo()

    if outlet_info is None:
        raise RuntimeError(f"No HydroBASINS basin found at ({lat}, {lon})")

    props     = outlet_info["properties"]
    outlet_id = props["HYBAS_ID"]
    up_area   = props["UP_AREA"]
    print(f"  Outlet HYBAS_ID : {outlet_id}")
    print(f"  Outlet UP_AREA  : {up_area:.1f} km²")

    # ── 2. Trace upstream iteratively ─────────────────────────────────────
    print("  Tracing upstream basins ...")
    all_ids: set[int] = {outlet_id}
    frontier: set[int] = {outlet_id}
    iteration = 0

    while frontier:
        iteration += 1
        parents    = basins.filter(ee.Filter.inList("NEXT_DOWN", list(frontier)))
        parent_ids = parents.aggregate_array("HYBAS_ID").getInfo()
        new_ids    = set(parent_ids) - all_ids

        print(f"    Iteration {iteration}: {len(new_ids)} new basin(s) "
              f"(running total: {len(all_ids) + len(new_ids)})")

        if not new_ids:
            break

        all_ids.update(new_ids)
        frontier = new_ids

    print(f"  Total basins in catchment: {len(all_ids)}")

    # ── 3. Union all upstream polygons ────────────────────────────────────
    print("  Unioning polygons (may take a moment) ...")
    upstream_fc = basins.filter(ee.Filter.inList("HYBAS_ID", list(all_ids)))
    merged      = upstream_fc.union(maxError=30).first()   # 30 m tolerance
    merged_info = merged.getInfo()

    # ── 4. Build GeoJSON feature ──────────────────────────────────────────
    feature = {
        "type": "Feature",
        "properties": {
            "gauge_id":        gauge_id,
            "hybas_id_outlet": outlet_id,
            "up_area_km2":     up_area,
            "num_level12":     len(all_ids),
        },
        "geometry": merged_info["geometry"],
    }

    return feature


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Deriving catchment boundaries from HydroBASINS Level 12\n")

    ee = init_gee()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_features: list[dict] = []

    for gauge in GAUGES:
        gid = gauge["gauge_id"]
        print(f"\n{'-' * 60}")
        print(f"Gauge: {gauge['name']} ({gauge['station_id']})")
        print(f"{'-' * 60}")

        if gauge["lat"] is None or gauge["lon"] is None:
            print("  Skipping — lat/lon not set in gauges_config.py")
            continue

        # Quick sanity check: compare HydroBASINS UP_AREA with known area
        known_area = gauge.get("area_km2")
        if known_area:
            print(f"  Known catchment area: {known_area} km²  "
                  f"(HydroBASINS UP_AREA will be close but not identical)")

        try:
            feature = trace_upstream(ee, gauge["lat"], gauge["lon"], gid)
        except Exception as exc:
            print(f"  ERROR — {exc}")
            continue

        hydrobasins_area = feature["properties"]["up_area_km2"]
        if known_area:
            diff_pct = abs(hydrobasins_area - known_area) / known_area * 100
            print(f"  Area check: HydroBASINS={hydrobasins_area:.1f} km²  "
                  f"known={known_area} km²  diff={diff_pct:.1f}%")

        # Save individual GeoJSON
        out_path = OUT_DIR / f"{gid}_catchment.geojson"
        out_path.write_text(json.dumps(feature, indent=2))
        print(f"  Saved -> {out_path}")

        all_features.append(feature)

    if not all_features:
        print("\nNo catchments processed — check lat/lon in gauges_config.py")
        return

    # Save combined FeatureCollection (for GEE asset upload)
    fc_path = OUT_DIR / "aus_vic_catchments.geojson"
    fc = {
        "type":     "FeatureCollection",
        "features": all_features,
    }
    fc_path.write_text(json.dumps(fc, indent=2))

    gids = [f["properties"]["gauge_id"] for f in all_features]

    # ── Export as ESRI shapefile (required by Caravan) ────────────────────────
    shp_written = False
    try:
        import geopandas as gpd
        gdf = gpd.read_file(str(fc_path))
        shp_path = OUT_DIR / "aus_vic_catchments.shp"
        gdf.to_file(str(shp_path))
        # Also write individual shapefiles per gauge
        for g in gids:
            single = gdf[gdf["gauge_id"] == g]
            if not single.empty:
                single.to_file(str(OUT_DIR / f"{g}_catchment.shp"))
        print(f"\n  Shapefile -> {OUT_DIR}/aus_vic_catchments.shp  (+ per-gauge .shp)")
        shp_written = True
    except ImportError:
        print("\n  NOTE: geopandas not installed — ESRI shapefile not written.")
        print("        Run:  pip install geopandas")
        print("        Then re-run this script, or convert the GeoJSON manually in QGIS.")

    print(f"""
{'=' * 60}
 Catchment boundaries written ({len(all_features)} gauge(s)):

   caravan_maribyrnong/shapefiles/
     aus_vic_catchments.geojson          ← combined FeatureCollection
""" + "\n".join(f"     {g}_catchment.geojson" for g in gids) + (f"""
     aus_vic_catchments.shp              ← combined shapefile (Caravan format)
""" if shp_written else "") + f"""

 Next — upload shapefile to GEE as an asset:
   1. Go to  https://code.earthengine.google.com/
   2. Assets tab → NEW → Shape files → upload aus_vic_catchments.shp
      (include the .dbf, .shx, .prj files in the same upload)
   3. Note the asset path (e.g. users/YOUR_NAME/aus_vic_catchments)
   4. Use that asset path in the Caravan ERA5-Land GEE notebooks to
      spatially average forcing data over these catchment polygons.

 Area check: compare the up_area_km2 field in each GeoJSON with the
 known catchment area in gauges_config.py.  A difference > 15% may
 indicate the gauge is near a confluence and the outlet basin cell
 captures a different sub-basin -- inspect the geometry in GEE Code
 Editor before proceeding.
{'=' * 60}
""")


if __name__ == "__main__":
    main()
