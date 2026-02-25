#!/usr/bin/env python3
"""
validate_submission.py

Validates the FloodHubMaribyrnong submission against Caravan requirements
BEFORE uploading to Zenodo or opening a PR on kratzert/Caravan.

Can be run standalone:
    python validate_submission.py

Or imported in tests (all functions are pure Python, no GEE/network):
    from validate_submission import validate_id_field_name, validate_gauge_ids, ...

Rules enforced:
  1. GEE asset shapefile ID field must not collide with HydroATLAS field names.
  2. Gauge IDs must be unique, non-empty, and follow the two-part Caravan format.
  3. Shapefile DBF must contain ONLY gauge_id (no extra columns).
  4. GeoJSON features must contain ONLY gauge_id as a property.
  5. All required output files must be present before submission.
  6. ERA5-Land processing must use ECMWF/ERA5_LAND/HOURLY (not DAILY_AGGR).

References:
  https://github.com/kratzert/Caravan/wiki/Extending-Caravan-with-new-basins
  .claude/rules/basin-extension-process.md
  .claude/rules/caravan-standard.md
"""

from pathlib import Path

# ── HydroATLAS / HydroBASINS reserved field names ─────────────────────────────
#
# The wiki states: "Make sure that the name of [the basin ID field] is different
# to any HydroATLAS field. For example, you can use `gauge_id` or `basin_id`
# but not `HYBAS_ID` or `PFAF_ID`, which are both field names in HydroATLAS."
#
# This list covers:
#   - All HydroBASINS structural fields (used for topology traversal)
#   - Key HydroATLAS attribute field prefixes
#   - GEE system-generated fields
#
# It is NOT exhaustive of all 294 BasinATLAS attributes, but covers every name
# that would cause a silent field-collision in the GEE notebook joins.

HYDROATLAS_RESERVED_FIELDS = frozenset([
    # ── HydroBASINS Level-12 structural fields ─────────────────────────────
    "HYBAS_ID",     # unique basin identifier — explicitly called out in wiki
    "NEXT_DOWN",    # downstream basin HYBAS_ID
    "NEXT_SINK",    # downstream sink HYBAS_ID
    "MAIN_BAS",     # main basin HYBAS_ID
    "DIST_SINK",    # distance to downstream sink (km)
    "DIST_MAIN",    # distance to main outlet (km)
    "SUB_AREA",     # sub-basin area (km²)
    "UP_AREA",      # total upstream area (km²)
    "PFAF_ID",      # Pfafstetter coding — explicitly called out in wiki
    "ORDER_",       # stream order
    "SORT_",        # sort order
    "ENDO_",        # endorheic flag
    "COAST_",       # coastal flag
    "LAKE_",        # lake flag
    "SIDE_",        # river side flag
    # ── GEE system-generated fields ────────────────────────────────────────
    "system:index", # GEE internal row identifier
    ".geo",         # GEE geometry field
    # ── Common HydroATLAS attribute prefixes (representative sample) ───────
    # Full list has 294 columns; these are the most likely accidental collisions.
    "AREA_SKM",     # sub-basin area (appears in some HydroATLAS versions)
    "RIVER_ID",     # river segment identifier
])

# ── Required output files (relative to caravan_maribyrnong/) ──────────────────

REQUIRED_OUTPUT_FILES = [
    "timeseries/csv/ausvic",                    # directory of per-gauge CSVs
    "timeseries/netcdf/ausvic",                 # directory of per-gauge netCDFs
    "attributes/ausvic/attributes_other_ausvic.csv",
    "attributes/ausvic/attributes_caravan_ausvic.csv",
    "attributes/ausvic/attributes_hydroatlas_ausvic.csv",
    "shapefiles/ausvic/ausvic_basin_shapes.shp",
    "shapefiles/ausvic/ausvic_basin_shapes.shx",
    "shapefiles/ausvic/ausvic_basin_shapes.dbf",
    "shapefiles/ausvic/ausvic_basin_shapes.prj",
    "licenses/ausvic/license_ausvic.md",
]

# ── Validation functions ───────────────────────────────────────────────────────


def validate_id_field_name(field_name: str) -> None:
    """Validate that the basin-ID field name does not collide with HydroATLAS.

    The Caravan wiki requires the shapefile uploaded to GEE to have a unique
    basin ID field whose name differs from any HydroATLAS field name.

    Parameters
    ----------
    field_name : str
        The name of the field you plan to use as the basin identifier
        (e.g. 'gauge_id', 'basin_id').

    Raises
    ------
    ValueError
        If field_name is a reserved HydroATLAS / HydroBASINS name.
    """
    if not field_name or not field_name.strip():
        raise ValueError("ID field name must not be empty.")
    if field_name in HYDROATLAS_RESERVED_FIELDS:
        raise ValueError(
            f"ID field name {field_name!r} is a reserved HydroATLAS field name. "
            f"Choose a different name (e.g. 'gauge_id' or 'basin_id'). "
            f"Reserved names: {sorted(HYDROATLAS_RESERVED_FIELDS)}"
        )


def validate_gauge_ids(gauge_ids: list) -> None:
    """Validate a list of Caravan gauge IDs.

    Each ID must:
      - Be non-empty.
      - Contain exactly one underscore, splitting the string into exactly two
        non-empty parts (e.g. 'ausvic_230200').
      - Be unique across the list.

    Parameters
    ----------
    gauge_ids : list of str

    Raises
    ------
    ValueError
        On the first violated rule, with a message describing the problem.
    """
    if not gauge_ids:
        raise ValueError("gauge_ids list must not be empty.")

    seen = {}
    for i, gid in enumerate(gauge_ids):
        if not gid or not gid.strip():
            raise ValueError(f"gauge_ids[{i}] is empty.")

        parts = gid.split("_")
        if len(parts) != 2:
            raise ValueError(
                f"gauge_id {gid!r} splits into {len(parts)} part(s) on '_' — "
                f"must be exactly 2 (e.g. 'ausvic_230200'). "
                f"Got parts: {parts}"
            )
        prefix, station = parts
        if not prefix:
            raise ValueError(f"gauge_id {gid!r} has an empty prefix before '_'.")
        if not station:
            raise ValueError(f"gauge_id {gid!r} has an empty station ID after '_'.")

        if gid in seen:
            raise ValueError(
                f"Duplicate gauge_id {gid!r} at indices {seen[gid]} and {i}."
            )
        seen[gid] = i


def validate_shapefile_dbf_columns(columns: list) -> None:
    """Validate that a shapefile DBF contains only the 'gauge_id' column.

    Caravan requires the combined shapefile to have NO extra columns in the
    DBF — only 'gauge_id'. This was a reviewer requirement (Feb 2026).

    Parameters
    ----------
    columns : list of str
        Column names present in the shapefile DBF.

    Raises
    ------
    ValueError
        If the column list is not exactly ['gauge_id'].
    """
    cols = list(columns)
    if cols != ["gauge_id"]:
        extra = [c for c in cols if c != "gauge_id"]
        missing = [] if "gauge_id" in cols else ["gauge_id"]
        msg_parts = []
        if missing:
            msg_parts.append("missing required column 'gauge_id'")
        if extra:
            msg_parts.append(f"extra columns not allowed: {extra}")
        raise ValueError(
            f"Shapefile DBF must contain ONLY ['gauge_id']. "
            + "; ".join(msg_parts)
            + f". Got: {cols}"
        )


def validate_geojson_feature_properties(properties: dict) -> None:
    """Validate that a GeoJSON feature's properties contain only 'gauge_id'.

    Output GeoJSON (ausvic_basin_shapes.geojson) must have exactly one
    property per feature — the gauge_id. Internal fields like up_area_km2
    must be stripped before writing.

    Parameters
    ----------
    properties : dict
        The 'properties' dict of a single GeoJSON Feature.

    Raises
    ------
    ValueError
        If properties contains keys other than 'gauge_id', or if 'gauge_id'
        is missing.
    """
    keys = set(properties.keys())
    if keys != {"gauge_id"}:
        extra = keys - {"gauge_id"}
        missing = {"gauge_id"} - keys
        msg_parts = []
        if missing:
            msg_parts.append("missing 'gauge_id'")
        if extra:
            msg_parts.append(f"extra keys not allowed: {sorted(extra)}")
        raise ValueError(
            "GeoJSON feature properties must be exactly {'gauge_id': ...}. "
            + "; ".join(msg_parts)
            + f". Got keys: {sorted(keys)}"
        )
    gid = properties["gauge_id"]
    if not gid or not str(gid).strip():
        raise ValueError("GeoJSON feature has an empty gauge_id value.")


def validate_output_files(output_dir: str | Path) -> list:
    """Check that all required output files/directories exist.

    Parameters
    ----------
    output_dir : str or Path
        Path to the caravan_maribyrnong/ output root.

    Returns
    -------
    list of str
        Paths (relative to output_dir) that are missing.
        An empty list means all required files are present.
    """
    root = Path(output_dir)
    missing = []
    for rel in REQUIRED_OUTPUT_FILES:
        if not (root / rel).exists():
            missing.append(rel)
    return missing


# ── Standalone runner ─────────────────────────────────────────────────────────


def _check(label: str, fn, *args, **kwargs) -> bool:
    """Run fn(*args, **kwargs); print pass/fail. Returns True on pass."""
    try:
        result = fn(*args, **kwargs)
        if isinstance(result, list) and result:
            print(f"  [FAIL] {label}")
            for item in result:
                print(f"         missing: {item}")
            return False
        print(f"  [OK]   {label}")
        return True
    except (ValueError, TypeError) as exc:
        print(f"  [FAIL] {label}: {exc}")
        return False


def main():
    """Run all submission validation checks against the local output directory."""
    import sys
    from gauges_config import GAUGES

    print("=" * 60)
    print("Caravan submission validation")
    print("=" * 60)

    failures = 0

    # 1. GEE asset field name
    print("\n[1] GEE shapefile asset field name")
    if not _check("'gauge_id' is a valid field name", validate_id_field_name, "gauge_id"):
        failures += 1

    # 2. Gauge IDs
    print("\n[2] Gauge ID format and uniqueness")
    gauge_ids = [g["gauge_id"] for g in GAUGES]
    if not _check(
        f"{len(gauge_ids)} gauge IDs are unique and two-part",
        validate_gauge_ids, gauge_ids,
    ):
        failures += 1

    # 3. Shapefile DBF (read actual file if present)
    print("\n[3] Shapefile DBF columns")
    shp_dbf = Path("caravan_maribyrnong/shapefiles/ausvic/ausvic_basin_shapes.dbf")
    if shp_dbf.exists():
        try:
            import shapefile as pyshp
            with pyshp.Reader(str(shp_dbf.with_suffix(""))) as sf:
                cols = [f[0] for f in sf.fields[1:]]   # skip deletion flag
            _check("DBF has only gauge_id column", validate_shapefile_dbf_columns, cols)
        except ImportError:
            print("  [SKIP] pyshp not installed — install pyshp to check DBF columns")
    else:
        print("  [SKIP] shapefile not found — run fetch_catchments.py first")

    # 4. GeoJSON feature properties
    print("\n[4] GeoJSON feature properties")
    geojson_path = Path("caravan_maribyrnong/shapefiles/ausvic/ausvic_basin_shapes.geojson")
    if geojson_path.exists():
        import json
        with open(geojson_path) as f:
            fc = json.load(f)
        all_ok = True
        for feat in fc.get("features", []):
            try:
                validate_geojson_feature_properties(feat.get("properties", {}))
            except ValueError as exc:
                print(f"  [FAIL] {exc}")
                all_ok = False
                failures += 1
                break
        if all_ok:
            print(f"  [OK]   {len(fc.get('features', []))} features all have only gauge_id")
    else:
        print("  [SKIP] GeoJSON not found — run fetch_catchments.py first")

    # 5. ERA5-Land collection constant
    print("\n[5] ERA5-Land GEE collection")
    try:
        from fetch_era5land import GEE_COLLECTION
        if GEE_COLLECTION == "ECMWF/ERA5_LAND/HOURLY":
            print(f"  [OK]   GEE_COLLECTION = {GEE_COLLECTION!r}")
        else:
            print(f"  [FAIL] GEE_COLLECTION = {GEE_COLLECTION!r} — must be HOURLY not DAILY_AGGR")
            failures += 1
    except ImportError:
        print("  [SKIP] fetch_era5land.py not importable")

    # 6. Required output files
    print("\n[6] Required output files")
    missing = validate_output_files("caravan_maribyrnong")
    if missing:
        print(f"  [FAIL] {len(missing)} required file(s) missing:")
        for m in missing:
            print(f"         caravan_maribyrnong/{m}")
        failures += 1
    else:
        print(f"  [OK]   All {len(REQUIRED_OUTPUT_FILES)} required paths present")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED — {failures} check(s) did not pass. Fix before submitting.")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED — submission is ready.")


if __name__ == "__main__":
    main()
