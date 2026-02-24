#!/usr/bin/env python3
"""
fetch_hydroatlas_polygon.py

Faithful command-line implementation of the HydroATLAS extraction step from
the official Caravan Part-1 Colab notebook:
  https://github.com/kratzert/Caravan/blob/main/code/Caravan_part1_Earth_Engine.ipynb

The algorithm is translated verbatim from the notebook (Jan 2025 version):

  - Property filtering: ignore_properties + upstream_properties excluded
  - MAJORITY_PROPERTIES: area-weighted majority vote (np.bincount)
  - POUR_POINT_PROPERTIES: sum taken from most-downstream sub-basin(s)
  - -999 sentinel values: excluded from averages; NaN if ALL values are -999
  - wet_cl_smj: -999 remapped to 13 (no-wetland class) before majority vote
  - Intersection areas computed server-side by GEE in km² (via ee.Join.inner
    + join_features) — matches notebook exactly, enables correct
    weights[i] / SUB_AREA[i] pour-point percentage comparison
  - Configuration: all our gauges < 2000 km² → Level-12, min_overlap = 0 km²
  - Output columns: gauge_id + ~197 HydroATLAS attributes (~198 total)

The catchment polygon for each gauge is derived first via BFS upstream tracing
through HydroBASINS Level-12 (same as fetch_catchments.py), then used as the
input basin polygon for the HydroATLAS intersection.

GEE project: floodhubmaribyrnong

Usage:
    python fetch_hydroatlas_polygon.py

Requirements:
    pip install earthengine-api numpy
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from gauges_config import GAUGES


def _to_float(v: object) -> float:
    """Convert a GEE property value to float, returning NaN for None."""
    if v is None:
        return float("nan")
    return float(v)  # type: ignore[arg-type]

# ── Constants ──────────────────────────────────────────────────────────────────

GEE_BASINS  = "WWF/HydroSHEDS/v1/Basins/hybas_12"
GEE_ATLAS   = "WWF/HydroATLAS/v1/Basins/level12"
GEE_PROJECT = "floodhubmaribyrnong"

OUT_PATH = Path(
    "caravan_maribyrnong/attributes/ausvic/attributes_hydroatlas_ausvic.csv"
)

# All Maribyrnong gauges are < 2000 km² → Level-12, threshold = 0 km²
MIN_OVERLAP_THRESHOLD = 0  # km²

# ── Property lists (copied verbatim from Caravan Part-1 notebook) ──────────────

# Area-weighted majority vote (class code with highest weighted count wins)
MAJORITY_PROPERTIES = [
    'clz_cl_smj',  # climate zones (18 classes)
    'cls_cl_smj',  # climate strata (125 classes)
    'glc_cl_smj',  # land cover (22 classes)
    'pnv_cl_smj',  # potential natural vegetation (15 classes)
    'wet_cl_smj',  # wetland (12 classes)
    'tbi_cl_smj',  # terrestrial biomes (14 classes)
    'tec_cl_smj',  # Terrestrial Ecoregions (846 classes)
    'fmh_cl_smj',  # Freshwater Major Habitat Types (13 classes)
    'fec_cl_smj',  # Freshwater Ecoregions (426 classes)
    'lit_cl_smj',  # Lithological classes (16 classes)
]

# Taken from the most-downstream sub-basin (summed if multiple tributaries)
POUR_POINT_PROPERTIES = [
    'dis_m3_pmn',  # natural discharge annual mean
    'dis_m3_pmx',  # natural discharge annual max
    'dis_m3_pyr',  # natural discharge annual min
    'lkv_mc_usu',  # lake volume
    'rev_mc_usu',  # reservoir volume
    'ria_ha_usu',  # river area
    'riv_tc_usu',  # river volume
    'pop_ct_usu',  # population count in upstream area
    'dor_pc_pva',  # degree of regulation in upstream area
]

# HydroSHEDS/RIVERS fields — ignored entirely
IGNORE_PROPERTIES = [
    'system:index',
    'COAST', 'DIST_MAIN', 'DIST_SINK', 'ENDO',
    'MAIN_BAS', 'NEXT_SINK', 'ORDER_', 'PFAF_ID', 'SORT',
]

# Used for pour-point traversal; excluded from final output
ADDITIONAL_PROPERTIES = ['HYBAS_ID', 'NEXT_DOWN', 'SUB_AREA', 'UP_AREA']

# Upstream-aggregated properties — excluded because per-polygon counterparts
# are already included (avoids redundancy with the sub-basin "ssu"/"smj" cols)
UPSTREAM_PROPERTIES = [
    'aet_mm_uyr',  # Actual evapotranspiration
    'ari_ix_uav',  # Global aridity index
    'cly_pc_uav',  # clay fraction soil
    'cmi_ix_uyr',  # Climate Moisture Index
    'crp_pc_use',  # Cropland Extent
    'ele_mt_uav',  # Elevation
    'ero_kh_uav',  # Soil erosion
    'for_pc_use',  # Forest cover extent
    'gdp_ud_usu',  # Gross Domestic Product
    'gla_pc_use',  # Glacier Extent
    'glc_pc_u01',  # Land cover extent percent per class (22)
    'glc_pc_u02',
    'glc_pc_u03',
    'glc_pc_u04',
    'glc_pc_u05',
    'glc_pc_u06',
    'glc_pc_u07',
    'glc_pc_u08',
    'glc_pc_u09',
    'glc_pc_u10',
    'glc_pc_u11',
    'glc_pc_u12',
    'glc_pc_u13',
    'glc_pc_u14',
    'glc_pc_u15',
    'glc_pc_u16',
    'glc_pc_u17',
    'glc_pc_u18',
    'glc_pc_u19',
    'glc_pc_u20',
    'glc_pc_u21',
    'glc_pc_u22',
    'hft_ix_u09',  # Human Footprint 2009
    'hft_ix_u93',  # Human Footprint 1993
    'inu_pc_ult',  # inundation extent long-term maximum
    'inu_pc_umn',  # inundation extent annual minimum
    'inu_pc_umx',  # inundation extent annual maximum
    'ire_pc_use',  # Irrigated Area Extent (Equipped)
    'kar_pc_use',  # Karst Area Extent
    'lka_pc_use',  # Limnicity (Percent Lake Area)
    'nli_ix_uav',  # Nighttime Lights
    'pac_pc_use',  # Protected Area Extent
    'pet_mm_uyr',  # Potential evapotranspiration
    'pnv_pc_u01',  # potential natural vegetation (15 classes)
    'pnv_pc_u02',
    'pnv_pc_u03',
    'pnv_pc_u04',
    'pnv_pc_u05',
    'pnv_pc_u06',
    'pnv_pc_u07',
    'pnv_pc_u08',
    'pnv_pc_u09',
    'pnv_pc_u10',
    'pnv_pc_u11',
    'pnv_pc_u12',
    'pnv_pc_u13',
    'pnv_pc_u14',
    'pnv_pc_u15',
    'pop_ct_ssu',  # population count (sub-unit)
    'ppd_pk_uav',  # population density
    'pre_mm_uyr',  # precipitation
    'prm_pc_use',  # Permafrost extent
    'pst_pc_use',  # Pasture extent
    'ria_ha_ssu',  # river area in sub polygon
    'riv_tc_ssu',  # river volume in sub polygon
    'rdd_mk_uav',  # Road density
    'slp_dg_uav',  # slope degree
    'slt_pc_uav',  # silt fraction
    'snd_pc_uav',  # sand fraction
    'snw_pc_uyr',  # snow cover percent
    'soc_th_uav',  # organic carbon content in soil
    'swc_pc_uyr',  # soil water content
    'tmp_dc_uyr',  # air temperature
    'urb_pc_use',  # urban extent
    'wet_pc_u01',  # wetland classes percent (9 classes)
    'wet_pc_u02',
    'wet_pc_u03',
    'wet_pc_u04',
    'wet_pc_u05',
    'wet_pc_u06',
    'wet_pc_u07',
    'wet_pc_u08',
    'wet_pc_u09',
    'wet_pc_ug1',  # wetland classes percent by grouping (2 classes)
    'wet_pc_ug2',
    'gad_id_smj',  # global administrative areas (country IDs)
]


# ── GEE initialisation ─────────────────────────────────────────────────────────

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
        print("  OK\n")
    except Exception:
        print("  Not authenticated — opening browser for Google sign-in ...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)
        print()

    return ee


# ── Step 1: BFS upstream trace → catchment polygon ────────────────────────────

def trace_catchment(ee, lat: float, lon: float) -> tuple:
    """
    BFS upstream trace through HydroBASINS Level-12.

    Returns
    -------
    catchment_geom_json : dict   GeoJSON geometry of the upstream union polygon
    up_area_km2         : float  HydroBASINS UP_AREA at outlet (km²)
    """
    basins = ee.FeatureCollection(GEE_BASINS)
    point  = ee.Geometry.Point([lon, lat])

    outlet_info = basins.filterBounds(point).first().getInfo()
    if outlet_info is None:
        raise RuntimeError(f"No HydroBASINS basin at ({lat}, {lon})")

    props     = outlet_info["properties"]
    outlet_id = props["HYBAS_ID"]
    up_area   = props["UP_AREA"]
    print(f"  Outlet HYBAS_ID : {outlet_id}")
    print(f"  UP_AREA         : {up_area:.1f} km²")

    all_ids  : set = {outlet_id}
    frontier : set = {outlet_id}
    iteration = 0
    while frontier:
        iteration += 1
        parents    = basins.filter(ee.Filter.inList("NEXT_DOWN", list(frontier)))
        parent_ids = set(parents.aggregate_array("HYBAS_ID").getInfo())
        new_ids    = parent_ids - all_ids
        print(f"    Iter {iteration}: +{len(new_ids)} basins "
              f"(running total {len(all_ids) + len(new_ids)})")
        if not new_ids:
            break
        all_ids.update(new_ids)
        frontier = new_ids

    print(f"  Total sub-basins in catchment: {len(all_ids)}")
    print("  Unioning polygons ...")
    upstream_fc = basins.filter(ee.Filter.inList("HYBAS_ID", list(all_ids)))
    merged      = upstream_fc.union(maxError=30).first()
    return merged.geometry().getInfo(), up_area


# ── Step 2: USE_PROPERTIES list ───────────────────────────────────────────────

def get_use_properties(ee) -> list:
    """
    Build USE_PROPERTIES list from HydroATLAS Level-12 property names,
    filtering exactly as the notebook does (ignore + upstream excluded).
    """
    hydro_atlas    = ee.FeatureCollection(GEE_ATLAS)
    property_names = hydro_atlas.first().propertyNames().getInfo()
    exclude        = set(IGNORE_PROPERTIES + UPSTREAM_PROPERTIES)
    use_properties = [p for p in property_names if p not in exclude]

    print(f"  Total HydroATLAS props : {len(property_names)}")
    print(f"  Ignored (HydroRIVERS)  : {len(IGNORE_PROPERTIES)}")
    print(f"  Ignored (upstream)     : {len(UPSTREAM_PROPERTIES)}")
    print(f"  USE_PROPERTIES         : {len(use_properties)}")
    # Mirrors notebook print:
    print(f"  Remaining (excl. aux)  : "
          f"{len(use_properties) - 1 - len(ADDITIONAL_PROPERTIES)}")
    return use_properties


# ── Step 3: GEE inner-join intersection (km² areas) ──────────────────────────

def _make_join_features(ee):
    """
    Returns a GEE-mapped function that computes km² intersection area between
    a primary (basin) and secondary (HydroATLAS) polygon.
    Translated verbatim from the notebook's join_features().
    """
    def join_features(poly):
        primary  = ee.Feature(poly.get("primary"))
        secondary = ee.Feature(poly.get("secondary"))
        new_poly  = primary.intersection(secondary)
        area      = new_poly.area().divide(1000 * 1000)   # m² → km²
        new_poly  = new_poly.copyProperties(primary).copyProperties(secondary)
        return ee.Feature(new_poly).set({"Intersect": area}).setGeometry(None)
    return join_features


def get_hydroatlas_intersections(ee, catchment_geom_json, gauge_id,
                                 hydroatlas_fc, use_properties,
                                 min_overlap_threshold):
    """
    Find all HydroATLAS Level-12 sub-basins intersecting the catchment polygon.
    Uses GEE inner join with spatial filter (identical to notebook) so that
    intersection areas are in km² — required for pour-point percentage logic.

    Returns
    -------
    basin_data : defaultdict(list)
        Keys: use_properties entries + 'weights' + 'area_fragments'
    """
    catchment_feat  = ee.Feature(ee.Geometry(catchment_geom_json),
                                 {"gauge_id": gauge_id})
    basin_fc        = ee.FeatureCollection([catchment_feat])

    spatial_filter  = ee.Filter.intersects(
        leftField=".geo", rightField=".geo", maxError=10
    )
    join            = ee.Join.inner()
    intersect_joined = join.apply(basin_fc, hydroatlas_fc, spatial_filter)
    intersected      = intersect_joined.map(_make_join_features(ee)).getInfo()

    print(f"  Candidate intersections : {len(intersected['features'])}")

    basin_data = defaultdict(list)

    for polygon in intersected["features"]:
        props          = polygon["properties"]
        intersect_area = props.get("Intersect") or 0.0
        sub_area       = props.get("SUB_AREA") or 1.0

        # Passes threshold OR covers > 50% of its HydroATLAS sub-basin
        qualifies = (
            (intersect_area > min_overlap_threshold)
            or (intersect_area / sub_area > 0.5)
        )

        if qualifies:
            # Deduplicate by Intersect area (notebook comment: returned twice)
            if intersect_area not in basin_data["weights"]:
                for prop in use_properties:
                    basin_data[prop].append(props.get(prop))
                basin_data["weights"].append(intersect_area)

        # area_fragments: ALL positive intersections (even tiny ones)
        if intersect_area > 0 and intersect_area not in basin_data["area_fragments"]:
            basin_data["area_fragments"].append(intersect_area)

    print(f"  Qualified sub-basins    : {len(basin_data['weights'])}")
    return basin_data


# ── Step 4: pour-point aggregation ────────────────────────────────────────────

def compute_pour_point_properties(basin_data, min_overlap_threshold,
                                  pour_point_properties):
    """
    Translated verbatim from Caravan Part-1 notebook.

    Finds the most-downstream HydroATLAS polygon still within the catchment
    (> 50% overlap) and sums pour-point properties from all polygons that
    drain directly into it.
    """
    percentage_overlap = [
        x / y
        for x, y in zip(basin_data["weights"], basin_data["SUB_AREA"])
    ]
    current_basin_pos = int(np.argmax(percentage_overlap))
    next_down_id      = basin_data["NEXT_DOWN"][current_basin_pos]

    while True:
        if next_down_id == 0:
            break
        if next_down_id not in basin_data["HYBAS_ID"]:
            break
        next_down_pos = basin_data["HYBAS_ID"].index(next_down_id)
        if percentage_overlap[next_down_pos] < 0.5:
            break
        next_down_id = basin_data["NEXT_DOWN"][next_down_pos]

    direct_upstream_polygons = []
    for i, next_down in enumerate(basin_data["NEXT_DOWN"]):
        if next_down == next_down_id and (
            (basin_data["weights"][i] > min_overlap_threshold)
            or (basin_data["weights"][i] / basin_data["SUB_AREA"][i] > 0.5)
        ):
            direct_upstream_polygons.append(i)

    aggregated = {}
    for prop in pour_point_properties:
        aggregated[prop] = sum(
            float(basin_data[prop][i] or 0)
            for i in direct_upstream_polygons
        )
    return aggregated


# ── Step 5: full aggregation (faithful to notebook) ───────────────────────────

def aggregate_hydroatlas_intersections(basin_data, min_overlap_threshold):
    """
    Translated verbatim from Caravan Part-1 notebook.

    Returns
    -------
    dict  {attribute_name: aggregated_value}
        Regular properties: area-weighted average (excluding -999)
        MAJORITY_PROPERTIES: area-weighted majority vote
        POUR_POINT_PROPERTIES: sum from most-downstream polygon
        'area': sum of ALL intersection area fragments (km²)
        'area_fraction_used_for_aggregation': fraction of area above threshold
    """
    weights        = np.array(basin_data["weights"], dtype=float)
    mask           = weights > min_overlap_threshold
    masked_weights = weights[mask]

    result = {}

    for key, val in basin_data.items():
        # Skip auxiliary keys (used for processing, not output)
        if key in ("weights", "UP_AREA", "area_fragments",
                   "HYBAS_ID", "NEXT_DOWN", "SUB_AREA"):
            continue
        # Pour-point properties handled separately below
        if key in POUR_POINT_PROPERTIES:
            continue

        # Convert to float array, treating None/missing as NaN
        val_arr    = np.array([_to_float(v) for v in val], dtype=float)
        masked_val = val_arr[mask]

        # Remap no-wetland sentinel to class 13 before majority vote
        if key == "wet_cl_smj":
            masked_val = masked_val.copy()
            masked_val[masked_val == -999] = 13

        if len(masked_val[masked_val == -999]) == len(masked_val):
            # All values are missing sentinel → NaN
            result[key] = float("nan")
        elif key in MAJORITY_PROPERTIES:
            valid       = masked_val > -999
            result[key] = int(
                np.bincount(
                    masked_val[valid].astype(int),
                    weights=masked_weights[valid],
                ).argmax()
            )
        else:
            valid       = masked_val > -999
            result[key] = float(
                np.average(masked_val[valid], weights=masked_weights[valid])
            )

    # Pour-point properties (sum from most-downstream polygon)
    pour_point = compute_pour_point_properties(
        basin_data, min_overlap_threshold, POUR_POINT_PROPERTIES
    )
    result.update(pour_point)

    # Basin area = sum of ALL intersecting fragment areas (km²)
    result["area"] = sum(basin_data["area_fragments"])

    # Fraction of area that passed the overlap threshold
    result["area_fraction_used_for_aggregation"] = (
        float(sum(masked_weights)) / sum(basin_data["area_fragments"])
        if basin_data["area_fragments"] else float("nan")
    )

    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("HydroATLAS polygon extraction")
    print("Faithful implementation of Caravan Part-1 notebook logic")
    print("=" * 65)
    print()

    ee = init_gee()

    print("Retrieving USE_PROPERTIES from HydroATLAS Level-12 ...")
    use_properties = get_use_properties(ee)
    print()

    hydroatlas_fc = ee.FeatureCollection(GEE_ATLAS)

    rows:          list = []
    failed_gauges: list = []

    for gauge in GAUGES:
        gid = gauge["gauge_id"]
        lat = gauge.get("lat")
        lon = gauge.get("lon")

        print(f"\n{'-' * 65}")
        print(f"Gauge: {gauge['name']} ({gauge['station_id']}) -> {gid}")
        print(f"{'-' * 65}")

        if lat is None or lon is None:
            print("  Skipping — lat/lon not set in gauges_config.py")
            failed_gauges.append(gid)
            continue

        try:
            # Step 1: derive catchment polygon via BFS upstream trace
            catchment_geom, _up_area = trace_catchment(ee, lat, lon)

            # Steps 2-3: GEE inner-join intersection (km² areas)
            basin_data = get_hydroatlas_intersections(
                ee, catchment_geom, gid,
                hydroatlas_fc, use_properties,
                MIN_OVERLAP_THRESHOLD,
            )

            # Steps 4-5: aggregate (majority vote, pour-point, -999 handling)
            attrs = aggregate_hydroatlas_intersections(
                basin_data, MIN_OVERLAP_THRESHOLD
            )

        except Exception as exc:
            print(f"  ERROR — {exc}")
            import traceback
            traceback.print_exc()
            failed_gauges.append(gid)
            continue

        # All keys from GEE are already lowercase; ensure consistency
        row = {"gauge_id": gid}
        row.update({str(k).lower(): v for k, v in attrs.items()})
        rows.append(row)
        print(f"  Attributes derived: {len(attrs)}")

    if not rows:
        print("\nNo gauges processed. Check errors above.")
        return

    # Column order: gauge_id first, then sorted attribute names
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
    print(f" Columns : {total_cols}")
    if failed_gauges:
        print(f" Failed  : {failed_gauges}")
    print(f"{'=' * 65}")
    print()
    print("Run  python verify_hydroatlas.py  to validate the output.")


if __name__ == "__main__":
    main()
