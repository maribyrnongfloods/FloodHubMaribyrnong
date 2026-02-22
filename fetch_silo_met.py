#!/usr/bin/env python3
"""
fetch_silo_met.py

Fetches daily meteorological data from the SILO DataDrill API for every
gauge defined in gauges_config.py, merges it with the corresponding
streamflow timeseries, and fills the climate attribute fields in the
Caravan attributes CSV.

SILO data portal:  https://www.longpaddock.qld.gov.au/silo/
No registration required — just supply any email address as --username.
The password is always the fixed string "apirequest".

Usage:
    python fetch_silo_met.py --username your@email.com

What it updates (for each gauge):
    caravan_maribyrnong/timeseries/csv/aus_vic/{gauge_id}.csv
        Adds columns: precipitation_mmd, temperature_2m_max,
                      temperature_2m_min, temperature_2m_mean,
                      pet_mmd, radiation_mj_m2_d, vapour_pressure_hpa

    caravan_maribyrnong/attributes/attributes_caravan_aus_vic.csv
        Fills: p_mean, pet_mean, aridity, frac_snow,
               high_prec_freq, low_prec_freq
"""

import argparse
import csv
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from gauges_config import GAUGES

# ── SILO API ──────────────────────────────────────────────────────────────────
SILO_BASE   = "https://www.longpaddock.qld.gov.au/cgi-bin/silo/DataDrillDataset.php"
SILO_START  = date(1889, 1, 1)    # SILO covers 1889-01-01 to near-present
CHUNK_YEARS = 10

# ── Paths ─────────────────────────────────────────────────────────────────────
OUT_DIR   = Path("caravan_maribyrnong")
TS_DIR    = OUT_DIR / "timeseries" / "csv" / "aus_vic"
ATTR_PATH = OUT_DIR / "attributes" / "attributes_caravan_aus_vic.csv"


# ── SILO fetch ────────────────────────────────────────────────────────────────

def fetch_silo_chunk(lat: float, lon: float, start: date, end: date,
                     username: str, retries: int = 3) -> str:
    """Call the SILO DataDrill API and return raw response text."""
    params = urllib.parse.urlencode({
        "start":    start.strftime("%Y%m%d"),
        "finish":   end.strftime("%Y%m%d"),
        "lat":      lat,
        "lon":      lon,
        "format":   "alldata",
        "username": username,
        "password": "apirequest",
    })
    url = f"{SILO_BASE}?{params}"

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"    Retry {attempt + 1} after {wait}s ...")
            time.sleep(wait)


def parse_silo_csv(raw_text: str) -> list[dict]:
    """
    Parse SILO alldata response. Skips comment lines at the top and finds
    the header row containing 'Date', then parses as CSV.
    """
    lines = raw_text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("date"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Could not find 'Date' header in SILO response")
    reader = csv.DictReader(lines[header_idx:])
    return list(reader)


def fetch_all_silo(lat: float, lon: float, username: str,
                   cache_path: Path) -> list[dict]:
    """
    Fetch all SILO data in CHUNK_YEARS-year chunks. Caches raw text so
    re-runs don't re-download. Delete the cache file to force a refresh.
    """
    if cache_path.exists():
        print(f"    Using cache: {cache_path.name}")
        print(f"    (Delete to force fresh download)")
        return parse_silo_csv(cache_path.read_text(encoding="utf-8"))

    all_rows: list[dict] = []
    header_line: str | None = None
    data_lines:  list[str] = []

    year = SILO_START.year
    while year <= date.today().year:
        chunk_start = max(SILO_START, date(year, 1, 1))
        chunk_end   = min(date.today(), date(year + CHUNK_YEARS - 1, 12, 31))
        print(f"    {chunk_start} → {chunk_end} ...", end=" ", flush=True)

        try:
            raw = fetch_silo_chunk(lat, lon, chunk_start, chunk_end, username)
        except Exception as exc:
            print(f"ERROR — {exc}")
            year += CHUNK_YEARS
            continue

        rows = parse_silo_csv(raw)
        print(f"{len(rows)} rows")
        all_rows.extend(rows)

        # Build cache: keep header from first chunk, data lines from all chunks
        lines = raw.splitlines()
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("date"):
                if header_line is None:
                    header_line = "\n".join(lines[:i + 1])
                data_lines.extend(lines[i + 1:])
                break

        year += CHUNK_YEARS
        time.sleep(1)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if header_line:
        cache_path.write_text(header_line + "\n" + "\n".join(data_lines),
                              encoding="utf-8")
    print(f"    Cached → {cache_path.name}")
    return all_rows


# ── Column detection ──────────────────────────────────────────────────────────

SILO_COL_MAP = {
    "daily_rain":    ["daily_rain", "rain"],
    "max_temp":      ["max_temp", "maximum_temperature"],
    "min_temp":      ["min_temp", "minimum_temperature"],
    "et_morton_pot": ["et_morton_potential", "et_morton_pot"],
    "radiation":     ["radiation", "solar_radiation"],
    "vp":            ["vp", "vapour_pressure"],
}

def detect_columns(fieldnames: list[str]) -> dict[str, str | None]:
    detected: dict[str, str | None] = {}
    for canonical, aliases in SILO_COL_MAP.items():
        for alias in aliases:
            if alias in fieldnames:
                detected[canonical] = alias
                break
        if canonical not in detected:
            for fn in fieldnames:
                for alias in aliases:
                    if alias.lower() in fn.lower():
                        detected[canonical] = fn
                        break
                if canonical in detected:
                    break
        if canonical not in detected:
            print(f"    WARNING: no column found for '{canonical}' "
                  f"in {fieldnames}")
            detected[canonical] = None
    return detected


def safe_float(val: str) -> float | None:
    try:
        v = float(val)
        return v if v > -999 else None
    except (ValueError, TypeError):
        return None


# ── Merge and update ──────────────────────────────────────────────────────────

def merge_gauge(gauge: dict, silo_rows: list[dict]) -> dict | None:
    """
    Merge SILO met data into the gauge's timeseries CSV.
    Returns computed climate stats, or None if the timeseries file is missing.
    """
    gid      = gauge["gauge_id"]
    ts_path  = TS_DIR / f"{gid}.csv"

    if not ts_path.exists():
        print(f"    ERROR: {ts_path} not found — run fetch_maribyrnong.py first.")
        return None

    fieldnames = list(silo_rows[0].keys()) if silo_rows else []
    col_map    = detect_columns(fieldnames)

    # Find date column
    date_col = next((c for c in ["Date", "date", "DATE"] if c in fieldnames),
                    fieldnames[0] if fieldnames else None)

    # Index SILO by ISO date
    silo_by_date: dict[str, dict] = {}
    for row in silo_rows:
        raw = row.get(date_col, "").strip()
        if not raw:
            continue
        iso = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}" if (len(raw) == 8 and raw.isdigit()) else raw[:10]
        silo_by_date[iso] = row

    with open(ts_path, newline="") as f:
        flow_rows = list(csv.DictReader(f))

    merged     = []
    rain_vals: list[float] = []
    pet_vals:  list[float] = []
    matched    = 0

    for flow_row in flow_rows:
        d   = flow_row["date"]
        met = silo_by_date.get(d, {})

        def get(key: str) -> float | None:
            col = col_map.get(key)
            return safe_float(met[col]) if col and col in met else None

        rain  = get("daily_rain")
        tmax  = get("max_temp")
        tmin  = get("min_temp")
        pet   = get("et_morton_pot")
        rad   = get("radiation")
        vp    = get("vp")
        tmean = round((tmax + tmin) / 2, 3) if tmax is not None and tmin is not None else None

        merged.append({
            "date":                flow_row["date"],
            "streamflow_mmd":      flow_row["streamflow_mmd"],
            "precipitation_mmd":   "" if rain  is None else round(rain,  3),
            "temperature_2m_max":  "" if tmax  is None else round(tmax,  3),
            "temperature_2m_min":  "" if tmin  is None else round(tmin,  3),
            "temperature_2m_mean": "" if tmean is None else tmean,
            "pet_mmd":             "" if pet   is None else round(pet,   3),
            "radiation_mj_m2_d":   "" if rad   is None else round(rad,   3),
            "vapour_pressure_hpa": "" if vp    is None else round(vp,    3),
        })
        if met:
            matched += 1
        if rain is not None:
            rain_vals.append(rain)
        if pet is not None:
            pet_vals.append(pet)

    print(f"    Rows merged with SILO data: {matched} / {len(flow_rows)}")

    with open(ts_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(merged[0].keys()))
        writer.writeheader()
        writer.writerows(merged)
    print(f"    Timeseries updated → {ts_path}")

    # Compute climate stats
    if rain_vals and pet_vals:
        p_mean   = round(sum(rain_vals) / len(rain_vals), 4)
        pet_mean = round(sum(pet_vals)  / len(pet_vals),  4)
        aridity  = round(pet_mean / p_mean, 4) if p_mean > 0 else ""
        n = len(rain_vals)
        high_prec_freq = round(sum(1 for r in rain_vals if r > 5 * p_mean) / n, 4)
        low_prec_freq  = round(sum(1 for r in rain_vals if r < 1.0)         / n, 4)
        print(f"    p_mean={p_mean}  pet_mean={pet_mean}  aridity={aridity}")
        return {
            "gauge_id":        gid,
            "p_mean":          p_mean,
            "pet_mean":        pet_mean,
            "aridity":         aridity,
            "frac_snow":       0.0,
            "high_prec_freq":  high_prec_freq,
            "low_prec_freq":   low_prec_freq,
        }
    return None


def update_attributes(climate_stats: list[dict]) -> None:
    """Write climate stats back into the shared attributes CSV."""
    if not ATTR_PATH.exists():
        print(f"  WARNING: {ATTR_PATH} not found — skipping attribute update.")
        return

    with open(ATTR_PATH, newline="") as f:
        reader    = csv.DictReader(f)
        attr_rows = list(reader)
        fields    = reader.fieldnames

    stats_by_id = {s["gauge_id"]: s for s in climate_stats}
    for row in attr_rows:
        stats = stats_by_id.get(row.get("gauge_id"))
        if stats:
            for k in ("p_mean", "pet_mean", "aridity", "frac_snow",
                      "high_prec_freq", "low_prec_freq"):
                if k in row:
                    row[k] = stats[k]

    with open(ATTR_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(attr_rows)
    print(f"\n  Attributes updated → {ATTR_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--username", required=True,
        help="Any email address — no registration needed. "
             "Used by SILO for attribution only.",
    )
    args = parser.parse_args()

    climate_stats = []

    for gauge in GAUGES:
        gid = gauge["gauge_id"]
        print(f"\n{'─' * 60}")
        print(f"SILO met: {gauge['name']}")
        print(f"{'─' * 60}")

        if gauge["lat"] is None or gauge["lon"] is None:
            print("  Skipping — lat/lon not set in gauges_config.py")
            continue

        cache_path = OUT_DIR / f"silo_cache_{gid}.csv"
        print(f"  Fetching SILO at ({gauge['lat']}, {gauge['lon']}) ...")
        silo_rows = fetch_all_silo(
            gauge["lat"], gauge["lon"], args.username, cache_path
        )
        print(f"  Total SILO rows: {len(silo_rows)}")

        stats = merge_gauge(gauge, silo_rows)
        if stats:
            climate_stats.append(stats)

    if climate_stats:
        update_attributes(climate_stats)

    print(f"""
{'═' * 60}
 SILO merge complete for {len(climate_stats)} gauge(s).
 Next step:
   python fetch_hydroatlas.py
{'═' * 60}
""")


if __name__ == "__main__":
    main()
