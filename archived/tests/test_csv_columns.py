"""
Test: timeseries CSV column names and order.

Verifies that every ausvic CSV in caravan_maribyrnong/timeseries/csv/ausvic/
has exactly the 41 columns that the official Caravan Part-2 notebook produces,
in the exact order produced by aggregate_df_to_daily() + the streamflow merge.

Column order source:
  - MEAN_VARS / MIN_VARS / MAX_VARS from notebook 5 cell 6 (same list × 3 suffixes)
  - SUM_VARS: total_precipitation_sum, potential_evaporation_sum_ERA5_LAND
  - FAO PET: potential_evaporation_sum_FAO_PENMAN_MONTEITH  (added after rename)
  - streamflow: appended last in cell 22

Tests are skipped if the output directory does not exist (e.g. fresh clone).
Run: pytest tests/test_csv_columns.py -v
"""

import csv
import pytest
from pathlib import Path

# ---------------------------------------------------------------------------
# Ground-truth column spec — derived from the official notebook
# ---------------------------------------------------------------------------

# Matches MEAN_VARS in notebook 5 cell 6 (and MIN_VARS / MAX_VARS use the same list)
_ERA5_VARS = [
    "snow_depth_water_equivalent",
    "surface_net_solar_radiation",
    "surface_net_thermal_radiation",
    "surface_pressure",
    "temperature_2m",
    "dewpoint_temperature_2m",
    "u_component_of_wind_10m",
    "v_component_of_wind_10m",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4",
]

EXPECTED_COLUMNS = (
    ["date"]
    + [f"{v}_mean" for v in _ERA5_VARS]   # 12 mean cols
    + [f"{v}_min"  for v in _ERA5_VARS]   # 12 min cols
    + [f"{v}_max"  for v in _ERA5_VARS]   # 12 max cols
    + [
        "total_precipitation_sum",
        "potential_evaporation_sum_ERA5_LAND",
        "potential_evaporation_sum_FAO_PENMAN_MONTEITH",
        "streamflow",                       # appended last by notebook cell 22
    ]
)

assert len(EXPECTED_COLUMNS) == 41, f"Expected 41 columns, got {len(EXPECTED_COLUMNS)}"

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

CSV_DIR = Path(__file__).parent.parent / "caravan_maribyrnong" / "timeseries" / "csv" / "ausvic"


def _csv_header(path: Path):
    """Read only the header row of a CSV without loading the whole file."""
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def csv_files():
    if not CSV_DIR.is_dir():
        return []
    return sorted(CSV_DIR.glob("*.csv"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_csv_dir_exists():
    """Output directory must exist. Skip instead of fail on a fresh clone."""
    if not CSV_DIR.is_dir():
        pytest.skip(f"Output directory not found: {CSV_DIR}")


@pytest.mark.parametrize("csv_path", csv_files(), ids=lambda p: p.stem)
def test_column_count(csv_path):
    """Each CSV must have exactly 41 columns."""
    header = _csv_header(csv_path)
    assert len(header) == 41, (
        f"{csv_path.name}: expected 41 columns, got {len(header)}\n"
        f"  columns: {header}"
    )


@pytest.mark.parametrize("csv_path", csv_files(), ids=lambda p: p.stem)
def test_column_names_and_order(csv_path):
    """Each CSV must have the exact column names in the exact order."""
    header = _csv_header(csv_path)
    assert header == EXPECTED_COLUMNS, (
        f"{csv_path.name}: column mismatch.\n"
        f"  First difference at index "
        f"{next(i for i,(a,b) in enumerate(zip(header,EXPECTED_COLUMNS)) if a!=b) if header!=EXPECTED_COLUMNS else '?'}\n"
        f"  Got:      {header}\n"
        f"  Expected: {EXPECTED_COLUMNS}"
    )


@pytest.mark.parametrize("csv_path", csv_files(), ids=lambda p: p.stem)
def test_gauge_id_format(csv_path):
    """Filename must follow ausvic_XXXXXX format."""
    stem = csv_path.stem
    parts = stem.split("_")
    assert len(parts) == 2, f"Expected two-part gauge_id, got: {stem}"
    assert parts[0] == "ausvic", f"Expected 'ausvic' prefix, got: {parts[0]}"
    assert parts[1].isdigit(), f"Station part is not numeric: {parts[1]}"
