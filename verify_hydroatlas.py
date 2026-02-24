#!/usr/bin/env python3
"""
verify_hydroatlas.py

Sanity check for attributes_hydroatlas_ausvic.csv produced by
fetch_hydroatlas_polygon.py (faithful Caravan Part-1 notebook implementation).

Expected structure (after notebook-faithful filtering):
  - gauge_id + ~197 HydroATLAS attributes = ~198 total columns
  - Upstream properties excluded (aet_mm_uyr, ari_ix_uav, pre_mm_uyr, etc.)
  - 'area' column present (km², sum of all intersection fragments)
  - 'area_fraction_used_for_aggregation' column present
  - UP_AREA NOT present (it is an auxiliary field, excluded from output)
  - All 10 gauge IDs present

Usage:
    python verify_hydroatlas.py
"""

import csv
from pathlib import Path

from gauges_config import GAUGES

CSV_PATH = Path("caravan_maribyrnong/attributes/ausvic/attributes_hydroatlas_ausvic.csv")

# Upstream properties that must NOT appear in notebook-faithful output
MUST_BE_ABSENT = [
    'aet_mm_uyr', 'ari_ix_uav', 'pre_mm_uyr', 'pet_mm_uyr',
    'wet_pc_ug1', 'wet_pc_ug2', 'gad_id_smj',
    'up_area',   # auxiliary — used internally, excluded from output
]

# Columns the notebook adds beyond the filtered HydroATLAS properties
MUST_BE_PRESENT = ['area', 'area_fraction_used_for_aggregation']


def main():
    print(f"Verifying: {CSV_PATH}\n")

    if not CSV_PATH.exists():
        print("ERROR — file not found.")
        print("  Run: python fetch_hydroatlas_polygon.py")
        return

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = reader.fieldnames or []

    cols_lower = [c.lower() for c in cols]

    print(f"Rows:    {len(rows)}")
    print(f"Columns: {len(cols)}")

    # ── gauge_id ──────────────────────────────────────────────────────────────
    if "gauge_id" not in cols_lower:
        print("\n[FAIL] 'gauge_id' column missing")
    else:
        print("  [OK] 'gauge_id' column present")

    # ── Column count (notebook produces ~198 total) ────────────────────────────
    if 190 <= len(cols) <= 210:
        print(f"  [OK] {len(cols)} columns (expected ~198 for notebook-faithful output)")
    else:
        print(f"  [WARN] {len(cols)} columns — expected ~198.")
        if len(cols) == 295:
            print("         Looks like old fetch_hydroatlas_polygon.py output (all 294 props).")
            print("         Re-run:  python fetch_hydroatlas_polygon.py")

    # ── Upstream properties must NOT be present ───────────────────────────────
    present_upstream = [c for c in MUST_BE_ABSENT if c in cols_lower]
    if present_upstream:
        print(f"\n  [FAIL] Upstream properties present (should be excluded):")
        for c in present_upstream:
            print(f"         {c}")
        print("         Re-run:  python fetch_hydroatlas_polygon.py")
    else:
        print(f"  [OK] No upstream properties in output "
              f"(checked {len(MUST_BE_ABSENT)} sentinel columns)")

    # ── Required extra columns ─────────────────────────────────────────────────
    for col in MUST_BE_PRESENT:
        if col in cols_lower:
            print(f"  [OK] '{col}' column present")
        else:
            print(f"  [WARN] '{col}' column missing — re-run fetch_hydroatlas_polygon.py")

    # ── Area sanity check ─────────────────────────────────────────────────────
    area_col = next((c for c in cols if c.lower() == "area"), None)
    if area_col:
        print(f"\n  Basin areas from HydroATLAS intersection ('{area_col}' column):")
        for row in rows:
            gid = row.get("gauge_id", "?")
            val = row.get(area_col, "")
            try:
                print(f"       {gid}: {float(val):.1f} km²")
            except (ValueError, TypeError):
                print(f"       {gid}: {val!r}")

    # ── All 10 gauges present ─────────────────────────────────────────────────
    expected_ids = {g["gauge_id"] for g in GAUGES}
    present_ids  = {r.get("gauge_id", "") for r in rows}
    missing = expected_ids - present_ids
    extra   = present_ids - expected_ids

    if not missing:
        print(f"\n  [OK] All {len(expected_ids)} gauge IDs present")
    else:
        print(f"\n  [FAIL] Missing gauge IDs: {sorted(missing)}")

    if extra:
        print(f"  [WARN] Unexpected gauge IDs: {sorted(extra)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
