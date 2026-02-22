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
        Adds columns: total_precipitation_sum, temperature_2m_max,
                      temperature_2m_min, temperature_2m_mean,
                      potential_evaporation_sum, radiation_mj_m2_d,
                      vapour_pressure_hpa

    caravan_maribyrnong/attributes/attributes_caravan_aus_vic.csv  (created fresh)
        Writes: p_mean, pet_mean, aridity, frac_snow, moisture_index,
                moisture_index_seasonality, high_prec_freq, high_prec_dur,
                low_prec_freq, low_prec_dur
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
    Parse SILO alldata response (space-delimited).
    Skips comment/metadata lines, finds the header row starting with 'Date',
    skips the units row that follows it, then parses data rows.
    """
    lines = raw_text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith("date") and not stripped.startswith('"'):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Could not find 'Date' header in SILO response")

    headers = lines[header_idx].split()
    result = []
    for line in lines[header_idx + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("(") or stripped.startswith('"'):
            continue   # skip units row and comment lines
        values = stripped.split()
        if len(values) >= len(headers):
            result.append(dict(zip(headers, values)))
    return result


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
        print(f"    {chunk_start} -> {chunk_end} ...", end=" ", flush=True)

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
    print(f"    Cached -> {cache_path.name}")
    return all_rows


# ── Column detection ──────────────────────────────────────────────────────────

SILO_COL_MAP = {
    "daily_rain":    ["Rain", "daily_rain", "rain"],
    "max_temp":      ["T.Max", "max_temp", "maximum_temperature"],
    "min_temp":      ["T.Min", "min_temp", "minimum_temperature"],
    "et_morton_pot": ["Mpot", "et_morton_potential", "et_morton_pot"],
    "radiation":     ["Radn", "radiation", "solar_radiation"],
    "vp":            ["VP", "vp", "vapour_pressure"],
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

    merged:    list[dict] = []
    met_pairs: list[tuple[str, float, float]] = []   # (date, rain, pet)
    rain_vals: list[float] = []
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

        # Support timeseries files written with either column name
        sf = flow_row.get("streamflow", flow_row.get("streamflow_mmd", ""))

        merged.append({
            "date":                    d,
            "streamflow":              sf,
            "total_precipitation_sum": "" if rain  is None else round(rain,  3),
            "temperature_2m_max":      "" if tmax  is None else round(tmax,  3),
            "temperature_2m_min":      "" if tmin  is None else round(tmin,  3),
            "temperature_2m_mean":     "" if tmean is None else tmean,
            "potential_evaporation_sum": "" if pet is None else round(pet,   3),
            "radiation_mj_m2_d":       "" if rad  is None else round(rad,   3),
            "vapour_pressure_hpa":     "" if vp   is None else round(vp,    3),
        })
        if met:
            matched += 1
        if rain is not None:
            rain_vals.append(rain)
        if rain is not None and pet is not None:
            met_pairs.append((d, rain, pet))

    print(f"    Rows merged with SILO data: {matched} / {len(flow_rows)}")

    with open(ts_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(merged[0].keys()))
        writer.writeheader()
        writer.writerows(merged)
    print(f"    Timeseries updated -> {ts_path}")

    # ── Compute climate stats ─────────────────────────────────────────────────
    if not met_pairs:
        return None

    pair_rain = [r for _, r, _ in met_pairs]
    pair_pet  = [e for _, _, e in met_pairs]
    n         = len(met_pairs)

    p_mean   = round(sum(pair_rain) / n, 4)
    pet_mean = round(sum(pair_pet)  / n, 4)
    aridity  = round(pet_mean / p_mean, 4) if p_mean > 0 else ""

    # Moisture index: (PET − P) / (PET + P), averaged daily
    mi_daily = [
        (e - r) / (e + r) if (e + r) > 0 else 0.0
        for r, e in zip(pair_rain, pair_pet)
    ]
    moisture_index = round(sum(mi_daily) / n, 4)

    # Moisture index seasonality: range of monthly mean MI values
    from collections import defaultdict
    monthly_mi: dict[str, list[float]] = defaultdict(list)
    for (d, r, e), mi in zip(met_pairs, mi_daily):
        monthly_mi[d[5:7]].append(mi)          # key = "MM"
    monthly_means = [sum(v) / len(v) for v in monthly_mi.values() if v]
    moisture_index_seasonality = (
        round(max(monthly_means) - min(monthly_means), 4)
        if len(monthly_means) >= 2 else 0.0
    )

    # Precipitation frequency stats (use all days with rain data)
    high_prec_freq = round(sum(1 for r in rain_vals if r > 5 * p_mean) / len(rain_vals), 4)
    low_prec_freq  = round(sum(1 for r in rain_vals if r < 1.0)         / len(rain_vals), 4)

    # Mean consecutive-day run lengths
    def mean_run_length(vals: list[float], condition) -> float:
        runs, curr = [], 0
        for v in vals:
            if condition(v):
                curr += 1
            elif curr > 0:
                runs.append(curr)
                curr = 0
        if curr > 0:
            runs.append(curr)
        return round(sum(runs) / len(runs), 4) if runs else 0.0

    high_prec_dur = mean_run_length(rain_vals, lambda r: r > 5 * p_mean)
    low_prec_dur  = mean_run_length(rain_vals, lambda r: r < 1.0)

    print(f"    p_mean={p_mean}  pet_mean={pet_mean}  aridity={aridity}  "
          f"moisture_index={moisture_index}")

    return {
        "gauge_id":                    gid,
        "p_mean":                      p_mean,
        "pet_mean":                    pet_mean,
        "aridity":                     aridity,
        "frac_snow":                   0.0,
        "moisture_index":              moisture_index,
        "moisture_index_seasonality":  moisture_index_seasonality,
        "high_prec_freq":              high_prec_freq,
        "high_prec_dur":               high_prec_dur,
        "low_prec_freq":               low_prec_freq,
        "low_prec_dur":                low_prec_dur,
    }


def write_caravan_attributes(climate_stats: list[dict]) -> None:
    """Write attributes_caravan_aus_vic.csv with climate stats for all gauges."""
    if not climate_stats:
        return
    attr_path = OUT_DIR / "attributes" / "aus_vic" / "attributes_caravan_aus_vic.csv"
    attr_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(climate_stats[0].keys())
    with open(attr_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(climate_stats)
    print(f"\n  Caravan attributes -> {attr_path}  ({len(climate_stats)} gauges)")


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
        print(f"\n{'-' * 60}")
        print(f"SILO met: {gauge['name']}")
        print(f"{'-' * 60}")

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
        write_caravan_attributes(climate_stats)

    print(f"""
{'=' * 60}
 SILO merge complete for {len(climate_stats)} gauge(s).
 Next steps:
   python fetch_era5land.py
   python fetch_hydroatlas.py
{'=' * 60}
""")


if __name__ == "__main__":
    main()
