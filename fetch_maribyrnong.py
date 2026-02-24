#!/usr/bin/env python3
"""
fetch_maribyrnong.py

Fetches historical daily streamflow for all gauges defined in gauges_config.py
and writes Caravan-format timeseries and attributes CSVs.

Supports two APIs:
  hydstra   — Victorian Water Monitoring (data.water.vic.gov.au)
  melbwater — Melbourne Water (api.melbournewater.com.au)

Usage:
    python fetch_maribyrnong.py

Output structure:
    caravan_maribyrnong/
        timeseries/csv/ausvic/
            ausvic_230200.csv
            ausvic_230106.csv
        attributes/ausvic/
            attributes_other_ausvic.csv   ← gauge metadata (this script)
            attributes_caravan_ausvic.csv ← climate stats (Caravan Part-2 notebook)
            attributes_hydroatlas_ausvic.csv ← basin attrs (fetch_hydroatlas.py)
"""

import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from gauges_config import GAUGES

# ── Output paths ──────────────────────────────────────────────────────────────
OUT_DIR   = Path("caravan_maribyrnong")
TS_DIR    = OUT_DIR / "timeseries" / "csv" / "ausvic"
ATTR_DIR  = OUT_DIR / "attributes" / "ausvic"

# ── Hydstra API ───────────────────────────────────────────────────────────────
HYDSTRA_BASE = "https://data.water.vic.gov.au/cgi/webservice.exe"

def fetch_hydstra_year(station_id: str, start: date, end: date,
                       retries: int = 3) -> list:
    """
    Fetch daily mean discharge (ML/day) from the Hydstra API for one year.
    Uses server-side rating table conversion: water level → discharge.
    """
    params = {
        "function":   "get_ts_traces",
        "version":    "2",
        "site_list":  station_id,
        "datasource": "PUBLISH",
        "varfrom":    "100.00",   # water level (m)
        "varto":      "141.00",   # discharge (ML/day)
        "start_time": start.strftime("%Y%m%d") + "000000",
        "end_time":   end.strftime("%Y%m%d")   + "235959",
        "interval":   "day",
        "multiplier": "1",
        "data_type":  "mean",
    }
    url = HYDSTRA_BASE + "?" + urllib.parse.urlencode(params)

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)

    if data.get("error_num", 0) != 0:
        raise RuntimeError(f"Hydstra API error {data['error_num']}: {data.get('error_msg')}")

    traces = data.get("return", {}).get("traces", [])
    if not traces:
        return []
    trace = traces[0]
    if trace.get("error_num", 0) != 0:
        raise RuntimeError(f"Hydstra trace error {trace['error_num']}: {trace.get('error_msg')}")
    return trace.get("trace", [])


def fetch_hydstra_all(gauge: dict) -> list[tuple[str, float]]:
    """Fetch full history from Hydstra year-by-year. Returns (ISO date, ML/day) pairs."""
    rows: list[tuple[str, float]] = []
    fetch_end = date.today()

    for year in range(gauge["fetch_start"].year, fetch_end.year + 1):
        chunk_start = max(gauge["fetch_start"], date(year, 1, 1))
        chunk_end   = min(fetch_end, date(year, 12, 31))
        print(f"  {year} ...", end=" ", flush=True)

        try:
            points = fetch_hydstra_year(gauge["station_id"], chunk_start, chunk_end)
        except Exception as exc:
            print(f"ERROR — {exc}")
            continue

        good = 0
        for pt in points:
            if pt.get("q") == 255 or pt.get("v") in ("", None):
                continue
            raw = float(pt["v"])
            if raw < 0:
                continue
            ts = str(pt["t"])
            if len(ts) < 8:           # Hydstra timestamp must be at least YYYYMMDD
                continue
            rows.append((f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", raw))
            good += 1

        print(f"{good} days")
        time.sleep(2)

    return rows


# ── Melbourne Water API ───────────────────────────────────────────────────────
MELBWATER_BASE = "https://api.melbournewater.com.au/rainfall-river-level"

def fetch_melbwater_year(station_id: str, start: date, end: date,
                         retries: int = 3) -> list:
    """
    Fetch daily mean flow (ML/day) from the Melbourne Water API for a date range.
    Returns a list of dicts from dailyRiverFlowsData.

    Note: Flow is only recorded when water level exceeds ~1 m (tidal influence).
    Days below this threshold have no record — they will appear as gaps in the
    timeseries CSV, which Caravan handles as missing data.
    """
    url = (
        f"{MELBWATER_BASE}/{station_id}/river-flow/daily/range"
        f"?fromDate={start.isoformat()}&toDate={end.isoformat()}"
    )

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept":     "application/json",
        "Origin":     "https://www.melbournewater.com.au",
        "Referer":    "https://www.melbournewater.com.au/",
    })

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)

    return data.get("dailyRiverFlowsData", [])


def fetch_melbwater_all(gauge: dict) -> list[tuple[str, float]]:
    """
    Fetch full history from Melbourne Water year-by-year.
    Returns (ISO date, ML/day) pairs for days where flow was recorded.
    """
    rows: list[tuple[str, float]] = []
    fetch_end = date.today()

    for year in range(gauge["fetch_start"].year, fetch_end.year + 1):
        chunk_start = max(gauge["fetch_start"], date(year, 1, 1))
        chunk_end   = min(fetch_end, date(year, 12, 31))
        print(f"  {year} ...", end=" ", flush=True)

        try:
            records = fetch_melbwater_year(gauge["station_id"], chunk_start, chunk_end)
        except Exception as exc:
            print(f"ERROR — {exc}")
            continue

        good = 0
        for rec in records:
            flow = rec.get("meanRiverFlow")
            dt   = rec.get("dateTime", "")
            if flow is None or flow <= 0 or not dt:
                continue
            # dateTime is Melbourne local time "YYYY-MM-DD HH:MM:SS" — take date part only
            iso_date = dt[:10]
            rows.append((iso_date, float(flow)))
            good += 1

        print(f"{good} days with flow")
        time.sleep(2)

    return rows


# ── Conversion and deduplication ──────────────────────────────────────────────

def ml_day_to_mm_day(ml_day: float, area_km2: float) -> float:
    """
    Convert ML/day to mm/day.  Simplifies to: mm/day = ML/day / km²
    (1 ML over 1 km² = exactly 1 mm depth)
    """
    return ml_day / area_km2


def deduplicate(rows: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Sort by date and remove duplicate dates (keep first occurrence)."""
    seen: set[str] = set()
    result: list[tuple[str, float]] = []
    for day_str, val in sorted(rows, key=lambda r: r[0]):
        if day_str not in seen:
            seen.add(day_str)
            result.append((day_str, val))
    return result


# ── Per-gauge processing ──────────────────────────────────────────────────────

def process_gauge(gauge: dict) -> dict | None:
    """Fetch, convert, and write timeseries + attributes for one gauge."""
    gid  = gauge["gauge_id"]
    name = gauge["name"]
    area = gauge["area_km2"]

    print(f"\n{'-' * 60}")
    print(f"Gauge: {name} ({gauge['station_id']})")
    print(f"{'-' * 60}")

    if area is None:
        print("  ERROR: area_km2 is not set in gauges_config.py — skipping.")
        return
    if gauge["lat"] is None or gauge["lon"] is None:
        print("  ERROR: lat/lon not set in gauges_config.py — skipping.")
        return

    # ── Fetch raw ML/day values ───────────────────────────────────────────────
    if gauge["api"] == "hydstra":
        print(f"  API: Hydstra  |  from {gauge['fetch_start']}")
        raw_rows = fetch_hydstra_all(gauge)
    elif gauge["api"] == "melbwater":
        print(f"  API: Melbourne Water  |  from {gauge['fetch_start']}")
        print(f"  Note: {gauge['notes']}")
        raw_rows = fetch_melbwater_all(gauge)
    else:
        print(f"  ERROR: Unknown api '{gauge['api']}' — skipping.")
        return

    # ── Convert and deduplicate ───────────────────────────────────────────────
    converted = [(d, ml_day_to_mm_day(v, area)) for d, v in raw_rows]
    rows = deduplicate(converted)

    print(f"\n  Total valid daily records: {len(rows)}")
    if not rows:
        print("  WARNING: No data retrieved.")
        return

    # ── Write timeseries CSV ──────────────────────────────────────────────────
    ts_path = TS_DIR / f"{gid}.csv"
    with open(ts_path, "w") as f:
        f.write("date,streamflow\n")
        for day_str, mm_day in rows:
            f.write(f"{day_str},{mm_day:.4f}\n")
    print(f"  Timeseries -> {ts_path}")

    # ── Compute attributes ────────────────────────────────────────────────────
    period_str = f"{rows[0][0]}/{rows[-1][0]}"
    expected_days = (
        date.fromisoformat(rows[-1][0]) - date.fromisoformat(rows[0][0])
    ).days + 1
    missing_frac = round(1.0 - len(rows) / expected_days, 4)

    # attributes_other_aus_vic.csv — gauge metadata (Caravan "other" file)
    return {
        "gauge_id":           gid,
        "gauge_name":         name,
        "gauge_lat":          gauge["lat"],
        "gauge_lon":          gauge["lon"],
        "country":            "AUS",
        "basin_name":         "Maribyrnong",
        "area":               area,
        "unit_area":          "km2",
        "streamflow_period":  period_str,
        "streamflow_missing": missing_frac,
        "streamflow_units":   "mm/d",
        "source":             f"Melbourne Water (api.melbournewater.com.au), Station {gauge['station_id']}"
                              if gauge["api"] == "melbwater"
                              else f"Victorian Water Monitoring (data.water.vic.gov.au), Station {gauge['station_id']}",
        "license":            "Creative Commons Attribution 4.0",
        "note":               gauge["notes"],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    TS_DIR.mkdir(parents=True, exist_ok=True)
    ATTR_DIR.mkdir(parents=True, exist_ok=True)

    attr_rows  = []
    attr_fields = None

    for gauge in GAUGES:
        result = process_gauge(gauge)
        if result:
            attr_rows.append(result)
            if attr_fields is None:
                attr_fields = list(result.keys())

    # ── Write attributes_other CSV (gauge metadata) ───────────────────────────
    if attr_rows:
        import csv
        attr_path = ATTR_DIR / "attributes_other_ausvic.csv"
        with open(attr_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=attr_fields)
            writer.writeheader()
            writer.writerows(attr_rows)
        print(f"\nGauge metadata -> {attr_path}  ({len(attr_rows)} gauges)")

    print(f"""
{'=' * 60}
 Done. Next steps:
   python fetch_era5land.py
   python fetch_hydroatlas.py  (then replace with official Caravan Colab notebook)
{'=' * 60}
""")


if __name__ == "__main__":
    main()
