#!/usr/bin/env python3
"""
verify_hydroatlas.py

Quick sanity check for attributes_hydroatlas_ausvic.csv after running
the official Caravan Part-1 Colab notebook.

Usage:
    python verify_hydroatlas.py
"""

import csv
from pathlib import Path

from gauges_config import GAUGES

CSV_PATH = Path("caravan_maribyrnong/attributes/ausvic/attributes_hydroatlas_ausvic.csv")

# Caravan standard: exactly these columns (gauge_id + 294 HydroATLAS attributes = 295 total)
CARAVAN_HYDROATLAS_COL_COUNT = 295   # gauge_id + 294 HydroATLAS attrs


def main():
    print(f"Verifying: {CSV_PATH}\n")

    if not CSV_PATH.exists():
        print("ERROR — file not found.")
        print("  1. Run the Caravan Part-1 Colab notebook.")
        print("  2. Download attributes.csv from Google Drive.")
        print(f"  3. Save it as: {CSV_PATH}")
        return

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = reader.fieldnames or []

    print(f"Rows:    {len(rows)}")
    print(f"Columns: {len(cols)}")

    # Check gauge_id column
    if "gauge_id" not in cols:
        print("\nERROR — 'gauge_id' column missing.")
    else:
        print("  [OK] 'gauge_id' column present")

    # Check column count
    if len(cols) == CARAVAN_HYDROATLAS_COL_COUNT:
        print(f"  [OK] {len(cols)} columns (Caravan standard: {CARAVAN_HYDROATLAS_COL_COUNT})")
    else:
        diff = len(cols) - CARAVAN_HYDROATLAS_COL_COUNT
        sign = "+" if diff > 0 else ""
        print(f"  [WARN] {len(cols)} columns (expected {CARAVAN_HYDROATLAS_COL_COUNT}, diff {sign}{diff})")
        print("         If the file came from the official Colab notebook this is OK.")
        print("         If it came from fetch_hydroatlas.py it has too many columns — re-run the notebook.")

    # Check all 10 gauges are present
    expected_ids = {g["gauge_id"] for g in GAUGES}
    present_ids  = {r.get("gauge_id", "") for r in rows}
    missing = expected_ids - present_ids
    extra   = present_ids - expected_ids

    if not missing:
        print(f"  [OK] All {len(expected_ids)} gauge IDs present")
    else:
        print(f"\nERROR — missing gauge IDs: {sorted(missing)}")

    if extra:
        print(f"  [WARN] Unexpected gauge IDs: {sorted(extra)}")

    # Check UP_AREA column (used to fill area_km2 in gauges_config.py)
    up_area_col = next((c for c in cols if c.lower() == "up_area"), None)
    if up_area_col:
        print(f"  [OK] '{up_area_col}' (upstream area) column found")
        for row in rows:
            gid = row.get("gauge_id", "")
            val = row.get(up_area_col, "")
            print(f"       {gid}: {val} km²")
    else:
        print("  [WARN] 'UP_AREA' column not found — check column names in the CSV")

    print("\nDone.")


if __name__ == "__main__":
    main()
