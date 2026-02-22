#!/usr/bin/env python3
"""
test_run.py

One-day smoke test for the FloodHubMaribyrnong pipeline.
Tests real API calls (Hydstra, Melbourne Water, SILO) for a single recent day.
Does NOT require Google Earth Engine.

Usage:
    python test_run.py --username your@email.com
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

TEST_DATE      = date(2024, 6, 1)
TEST_DAY       = TEST_DATE.isoformat()
# Oct 2022 Maribyrnong flood — guaranteed flow above tidal threshold at Chifley Drive
FLOOD_DATE     = date(2022, 10, 14)
OUT_DIR        = Path("caravan_maribyrnong_test")
TS_DIR         = OUT_DIR / "timeseries" / "csv" / "aus_vic"
# Placeholder area for 230106A until fetch_hydroatlas.py fills it from HydroATLAS
CHIFLEY_AREA_KM2 = 630.0

PASS = "PASS"
FAIL = "FAIL"

def check(label, ok, detail=""):
    icon = PASS if ok else FAIL
    print(f"  [{icon}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def test_hydstra(username):
    print("\n-- Hydstra API (Gauge 230200, Keilor) --------------------------")
    from fetch_maribyrnong import fetch_hydstra_year, ml_day_to_mm_day, deduplicate
    try:
        points = fetch_hydstra_year("230200", TEST_DATE, TEST_DATE)
        ok = isinstance(points, list)
        check("API reachable", ok, f"{len(points)} point(s) returned")
        if not points:
            check("Data returned", False, f"No data for {TEST_DAY}")
            return None
        pt = points[0]
        val = float(pt["v"])
        mm  = ml_day_to_mm_day(val, 1305.4)
        check("Unit conversion", True, f"{val:.2f} ML/day -> {mm:.4f} mm/day")

        TS_DIR.mkdir(parents=True, exist_ok=True)
        ts_path = TS_DIR / "aus_vic_230200.csv"
        with open(ts_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "streamflow"])
            ts = str(pt["t"])
            w.writerow([f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", f"{mm:.4f}"])
        check("CSV written", ts_path.exists(), str(ts_path))
        return ts_path
    except Exception as e:
        check("Hydstra API", False, str(e))
        return None


def test_chifley(username):
    """Full pipeline test for gauge 230106A using a known flood date."""
    print("\n-- Melbourne Water + SILO (Gauge 230106A, Chifley Drive) -------")
    print(f"   Using flood date {FLOOD_DATE} to guarantee flow above tidal threshold")
    from fetch_maribyrnong import fetch_melbwater_year, ml_day_to_mm_day
    ts_path = None
    try:
        records = fetch_melbwater_year("230106A", FLOOD_DATE, FLOOD_DATE)
        check("API reachable", True, f"{len(records)} record(s) returned")
        if not records:
            check("Flow data returned", False, "No records — unexpected for flood date")
            return
        r = records[0]
        ok = "meanRiverFlow" in r
        check("Record structure", ok, f"flow={r.get('meanRiverFlow')} ML/day")
        if not ok:
            return

        flow_ml = float(r["meanRiverFlow"])
        mm = ml_day_to_mm_day(flow_ml, CHIFLEY_AREA_KM2)
        check("Unit conversion", True,
              f"{flow_ml:.1f} ML/day -> {mm:.4f} mm/day (area={CHIFLEY_AREA_KM2} km2 placeholder)")

        TS_DIR.mkdir(parents=True, exist_ok=True)
        ts_path = TS_DIR / "aus_vic_230106.csv"
        iso = r["dateTime"][:10]
        with open(ts_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "streamflow"])
            w.writerow([iso, f"{mm:.4f}"])
        check("CSV written", ts_path.exists(), str(ts_path))

    except Exception as e:
        check("Melbourne Water API", False, str(e))
        return

    # SILO merge for 230106A location
    from fetch_silo_met import fetch_silo_chunk, parse_silo_csv, merge_gauge
    LAT, LON = -37.76590000, 144.89500000
    try:
        raw = fetch_silo_chunk(LAT, LON, FLOOD_DATE, FLOOD_DATE, username)
        rows = parse_silo_csv(raw)
        check("SILO reachable", True, f"{len(rows)} row(s) for 230106A location")
    except Exception as e:
        check("SILO API", False, str(e))
        return

    import fetch_silo_met as fsm
    original = fsm.TS_DIR
    fsm.TS_DIR = TS_DIR
    try:
        result = merge_gauge({"gauge_id": "aus_vic_230106"}, rows)
        check("SILO merge succeeded", result is not None)
        with open(ts_path, newline="") as f:
            cols = set(next(csv.DictReader(f)).keys())
        required = {"date", "streamflow", "total_precipitation_sum",
                    "temperature_2m_max", "potential_evaporation_sum"}
        missing = required - cols
        check("Caravan column names", not missing,
              f"missing: {missing}" if missing else f"{len(cols)} columns written")
    finally:
        fsm.TS_DIR = original


def test_silo(ts_path, username):
    print("\n-- SILO DataDrill API ------------------------------------------")
    if ts_path is None:
        print("  [skipped] No timeseries file to merge into")
        return

    from fetch_silo_met import fetch_silo_chunk, parse_silo_csv, merge_gauge
    LAT, LON = -37.727706090, 144.836476100
    try:
        raw = fetch_silo_chunk(LAT, LON, TEST_DATE, TEST_DATE, username)
        rows = parse_silo_csv(raw)
        check("API reachable", True, f"{len(rows)} row(s) returned")
        if rows:
            r = rows[0]
            check("Rain column present",
                  any("rain" in k.lower() for k in r.keys()), str(list(r.keys())[:5]))
    except Exception as e:
        check("SILO API", False, str(e))
        return

    import fetch_silo_met as fsm
    original = fsm.TS_DIR
    fsm.TS_DIR = TS_DIR
    try:
        gauge = {"gauge_id": "aus_vic_230200"}
        result = merge_gauge(gauge, rows)
        check("Merge succeeded", result is not None)
        if result:
            check("Climate stats keys present",
                  "p_mean" in result and "aridity" in result,
                  f"p_mean={result.get('p_mean')}")

        # Verify CSV columns
        with open(ts_path, newline="") as f:
            cols = set(next(csv.DictReader(f)).keys())
        required = {"date", "streamflow", "total_precipitation_sum",
                    "temperature_2m_max", "potential_evaporation_sum"}
        missing  = required - cols
        check("Caravan column names", not missing,
              f"missing: {missing}" if missing else f"{len(cols)} columns written")
    finally:
        fsm.TS_DIR = original


def test_generate_license():
    print("\n-- generate_license.py -----------------------------------------")
    try:
        import generate_license
        orig = generate_license.LICENSE_DIR
        generate_license.LICENSE_DIR  = OUT_DIR / "licenses" / "aus_vic"
        generate_license.LICENSE_PATH = generate_license.LICENSE_DIR / "license_aus_vic.md"
        generate_license.main()
        check("License file written", generate_license.LICENSE_PATH.exists())
        generate_license.LICENSE_DIR  = orig
    except Exception as e:
        check("generate_license", False, str(e))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--username", required=True,
                        help="Any email address for SILO API")
    args = parser.parse_args()

    print(f"Smoke test — single day: {TEST_DAY}")
    print(f"Output dir: {OUT_DIR}/")

    ts_path = test_hydstra(args.username)
    test_silo(ts_path, args.username)
    test_chifley(args.username)
    test_generate_license()

    print("\n-- Done --------------------------------------------------------")
    print(f"GEE scripts (fetch_era5land, fetch_hydroatlas, fetch_catchments)")
    print(f"and write_netcdf.py require 'earthengine authenticate' — run separately.")


if __name__ == "__main__":
    main()
