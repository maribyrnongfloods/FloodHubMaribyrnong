#!/usr/bin/env python3
"""
compute_attributes.py

Reads the merged timeseries CSVs (produced by fetch_era5land.py) and computes
Caravan-standard climate attribute statistics, writing:

    caravan_maribyrnong/attributes/ausvic/attributes_caravan_ausvic.csv

Climate indices are computed over the standard Caravan period:
    1981-01-01 to 2020-12-31

Index definitions follow the official Caravan caravan_utils.py exactly:
    https://github.com/kratzert/Caravan/blob/main/code/caravan_utils.py

Must be run after:
    python fetch_maribyrnong.py
    python fetch_era5land.py

Requirements:
    pip install pandas numpy

Usage:
    python compute_attributes.py
"""

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from gauges_config import GAUGES

# ── Paths ─────────────────────────────────────────────────────────────────────

OUT_DIR  = Path("caravan_maribyrnong")
TS_DIR   = OUT_DIR / "timeseries" / "csv" / "ausvic"
ATTR_DIR = OUT_DIR / "attributes" / "ausvic"
OUT_PATH = ATTR_DIR / "attributes_caravan_ausvic.csv"

# ── Caravan standard period (keep these dates — required for cross-dataset
#    comparability; see Kratzert et al. 2023 and caravan_utils.py) ─────────────

CARAVAN_START = "1981-01-01"
CARAVAN_END   = "2020-12-31"

# ── Required input columns ────────────────────────────────────────────────────

REQUIRED_COLS = [
    "total_precipitation_sum",
    "potential_evaporation_sum_ERA5_LAND",
    "potential_evaporation_sum_FAO_PENMAN_MONTEITH",
    "temperature_2m_mean",
]

# ── Output fields (matches caravan_utils.calculate_climate_indices keys) ──────

OUTPUT_FIELDS = [
    "gauge_id",
    "p_mean",
    "pet_mean_ERA5_LAND",
    "pet_mean_FAO_PM",
    "aridity_ERA5_LAND",
    "aridity_FAO_PM",
    "frac_snow",
    "moisture_index_ERA5_LAND",
    "seasonality_ERA5_LAND",
    "moisture_index_FAO_PM",
    "seasonality_FAO_PM",
    "high_prec_freq",
    "high_prec_dur",
    "low_prec_freq",
    "low_prec_dur",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_lengths(mask: np.ndarray) -> list[int]:
    """
    Return the length of each consecutive run of True values in a bool array.
    Pure Python equivalent of caravan_utils._split_list (which uses numba).
    """
    runs: list[int] = []
    count = 0
    for val in mask:
        if val:
            count += 1
        elif count:
            runs.append(count)
            count = 0
    if count:
        runs.append(count)
    return runs


def _moisture_seasonality(precip: pd.Series, pet: pd.Series) -> tuple[float, float]:
    """
    Monthly moisture index (Knoben et al.) and seasonality.
    Matches _get_moisture_and_seasonality_index() in caravan_utils.py.
    """
    mmp  = precip.groupby(precip.index.month).mean()
    mmPET = pet.groupby(pet.index.month).mean()

    monthly_mi = pd.Series(0.0, index=mmp.index, dtype=float)
    for m in mmp.index:
        p = mmp[m]
        e = mmPET[m]
        if p > e:
            monthly_mi[m] = 1.0 - e / p
        elif p < e:
            monthly_mi[m] = p / e - 1.0
        # else p == e → 0.0 (already initialised)

    annual_mi  = float(monthly_mi.mean())
    seasonality = float(monthly_mi.max() - monthly_mi.min())
    return annual_mi, seasonality


def calculate_climate_indices(df: pd.DataFrame) -> dict | None:
    """
    Compute Caravan climate indices for one gauge from its daily timeseries.

    Slices df to CARAVAN_START–CARAVAN_END before any calculation.
    Returns a dict of named indices, or None if there is no data in that period.

    Required columns:
        total_precipitation_sum               mm/d
        potential_evaporation_sum_ERA5_LAND   mm/d
        potential_evaporation_sum_FAO_PENMAN_MONTEITH  mm/d
        temperature_2m_mean                   degC
    """
    df = df.loc[CARAVAN_START:CARAVAN_END].copy()
    if df.empty:
        return None

    precip = pd.to_numeric(df["total_precipitation_sum"],                errors="coerce").dropna()
    pet_e  = pd.to_numeric(df["potential_evaporation_sum_ERA5_LAND"],    errors="coerce").dropna()
    pet_f  = pd.to_numeric(df["potential_evaporation_sum_FAO_PENMAN_MONTEITH"],
                           errors="coerce").dropna()
    temp   = pd.to_numeric(df["temperature_2m_mean"],                    errors="coerce").dropna()

    if precip.empty or pet_e.empty or pet_f.empty or temp.empty:
        return None

    p_mean     = float(precip.mean())
    pet_mean_e = float(pet_e.mean())
    pet_mean_f = float(pet_f.mean())

    aridity_e = pet_mean_e / p_mean if p_mean > 0 else float("nan")
    aridity_f = pet_mean_f / p_mean if p_mean > 0 else float("nan")

    mi_e, seas_e = _moisture_seasonality(precip, pet_e)
    mi_f, seas_f = _moisture_seasonality(precip, pet_f)

    # Fraction of precip falling as snow (months with mean temp < 0°C)
    mmp = precip.groupby(precip.index.month).mean()
    mmt = temp.groupby(temp.index.month).mean()
    snow_precip = mmp.loc[mmt < 0].sum()
    frac_snow = float(snow_precip / mmp.sum()) if mmp.sum() > 0 else 0.0

    # High-precip frequency and duration (≥ 5 × p_mean)
    high_mask = (precip >= 5.0 * p_mean).values
    high_prec_freq = float(high_mask.sum() / len(precip))
    hi_runs = _run_lengths(high_mask)
    high_prec_dur = float(np.mean(hi_runs)) if hi_runs else 0.0

    # Low-precip frequency and duration (< 1 mm/d)
    low_mask = (precip < 1.0).values
    low_prec_freq = float(low_mask.sum() / len(precip))
    lo_runs = _run_lengths(low_mask)
    low_prec_dur = float(np.mean(lo_runs)) if lo_runs else 0.0

    return {
        "p_mean":                   round(p_mean,      4),
        "pet_mean_ERA5_LAND":       round(pet_mean_e,  4),
        "pet_mean_FAO_PM":          round(pet_mean_f,  4),
        "aridity_ERA5_LAND":        round(aridity_e,   4),
        "aridity_FAO_PM":           round(aridity_f,   4),
        "frac_snow":                round(frac_snow,   4),
        "moisture_index_ERA5_LAND": round(mi_e,        4),
        "seasonality_ERA5_LAND":    round(seas_e,      4),
        "moisture_index_FAO_PM":    round(mi_f,        4),
        "seasonality_FAO_PM":       round(seas_f,      4),
        "high_prec_freq":           round(high_prec_freq, 4),
        "high_prec_dur":            round(high_prec_dur,  4),
        "low_prec_freq":            round(low_prec_freq,  4),
        "low_prec_dur":             round(low_prec_dur,   4),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Computing Caravan climate indices "
          f"({CARAVAN_START} to {CARAVAN_END})\n")

    ATTR_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    for gauge in GAUGES:
        gid     = gauge["gauge_id"]
        ts_path = TS_DIR / f"{gid}.csv"

        print(f"{'-' * 60}")
        print(f"Gauge: {gauge['name']} ({gauge['station_id']})")

        if not ts_path.exists():
            print(f"  SKIP — timeseries CSV not found: {ts_path}")
            print(f"         Run fetch_maribyrnong.py and fetch_era5land.py first.")
            continue

        try:
            df = pd.read_csv(ts_path, index_col="date", parse_dates=True)
        except Exception as exc:
            print(f"  ERROR reading {ts_path}: {exc}")
            continue

        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            print(f"  SKIP — required columns missing: {missing}")
            print(f"         Run fetch_era5land.py to add ERA5-Land forcing.")
            continue

        indices = calculate_climate_indices(df)
        if indices is None:
            print(f"  SKIP — no data in Caravan standard period "
                  f"{CARAVAN_START}–{CARAVAN_END}")
            continue

        # Sanity check: warn if PET looks negative (wrong ERA5 sign convention)
        if indices["pet_mean_ERA5_LAND"] < 0:
            print(f"  WARNING — pet_mean_ERA5_LAND is negative "
                  f"({indices['pet_mean_ERA5_LAND']:.3f} mm/d). "
                  f"Update potential_evaporation lambda in fetch_era5land.py "
                  f"to `lambda v: v * -1000.0`.")

        row = {"gauge_id": gid, **indices}
        results.append(row)

        print(f"  p_mean={indices['p_mean']:.3f} mm/d  "
              f"pet_fao={indices['pet_mean_FAO_PM']:.3f} mm/d  "
              f"aridity_fao={indices['aridity_FAO_PM']:.3f}  "
              f"frac_snow={indices['frac_snow']:.3f}")

    print(f"\n{'=' * 60}")
    if results:
        with open(OUT_PATH, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            w.writeheader()
            w.writerows(results)
        print(f" {len(results)} gauge records written -> {OUT_PATH}")
    else:
        print(" No results — no gauges had data in the Caravan standard period.")

    print(f"""
 Next steps:
   python write_netcdf.py
   python fetch_catchments.py    (catchment shapefiles)
   python generate_license.py    (license markdown)
{'=' * 60}
""")


if __name__ == "__main__":
    main()
