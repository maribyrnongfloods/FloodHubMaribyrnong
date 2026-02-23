"""
tests/test_pipeline.py

Unit and integration tests for the FloodHubMaribyrnong pipeline.
No API calls — all tests use synthetic data.

Run with:
    pip install pytest
    pytest tests/

Changes from original (Feb 2026 Caravan reviewer fixes):
  - Removed TestSafeFloat, TestDetectColumns, TestClimateSats (SILO removed)
  - Updated TestCaravanColumnNames: SILO cols gone, ERA5-Land cols tested
  - Added TestGaugeConfig: gauge ID format and count checks
"""

import csv
import tempfile
from datetime import date, timedelta
from pathlib import Path
import sys

import pytest

# Allow imports from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_maribyrnong import ml_day_to_mm_day, deduplicate
from fetch_era5land import convert_units, ERA5_COLS, merge_era5land


# ── fetch_maribyrnong ─────────────────────────────────────────────────────────

class TestMlDayToMmDay:
    def test_basic_conversion(self):
        # 1 ML/day over 1 km² = 1 mm/day
        assert ml_day_to_mm_day(1.0, 1.0) == 1.0

    def test_keilor_area(self):
        # 1305.4 km² catchment
        result = ml_day_to_mm_day(1305.4, 1305.4)
        assert abs(result - 1.0) < 1e-9

    def test_scales_with_volume(self):
        assert ml_day_to_mm_day(200.0, 100.0) == pytest.approx(2.0)

    def test_large_flow(self):
        # ~flood-level flow for Keilor
        result = ml_day_to_mm_day(50000.0, 1305.4)
        assert result == pytest.approx(50000.0 / 1305.4)

    def test_zero_flow(self):
        assert ml_day_to_mm_day(0.0, 1305.4) == 0.0


class TestDeduplicate:
    def test_removes_duplicates(self):
        rows = [("2020-01-01", 1.0), ("2020-01-01", 2.0), ("2020-01-02", 3.0)]
        result = deduplicate(rows)
        assert len(result) == 2
        # Keeps first occurrence after sorting
        assert result[0] == ("2020-01-01", 1.0)

    def test_sorts_by_date(self):
        rows = [("2020-01-03", 3.0), ("2020-01-01", 1.0), ("2020-01-02", 2.0)]
        result = deduplicate(rows)
        dates = [r[0] for r in result]
        assert dates == sorted(dates)

    def test_empty_input(self):
        assert deduplicate([]) == []

    def test_single_row(self):
        rows = [("2020-06-15", 42.0)]
        assert deduplicate(rows) == [("2020-06-15", 42.0)]

    def test_no_duplicates_unchanged(self):
        rows = [("2020-01-01", 1.0), ("2020-01-02", 2.0)]
        result = deduplicate(rows)
        assert result == rows


# ── fetch_era5land ────────────────────────────────────────────────────────────

class TestConvertUnits:
    def test_kelvin_to_celsius(self):
        assert convert_units("dewpoint_temperature_2m", 273.15) == pytest.approx(0.0)
        assert convert_units("dewpoint_temperature_2m", 300.0) == pytest.approx(26.85)

    def test_pascal_to_kilopascal(self):
        assert convert_units("surface_pressure", 101325.0) == pytest.approx(101.325)

    def test_metres_to_mm_snow(self):
        assert convert_units("snow_depth_water_equivalent", 0.05) == pytest.approx(50.0)

    def test_radiation_joules_to_watts(self):
        # J/m² per hour → W/m²: divide by 3600
        assert convert_units("surface_net_solar_radiation", 3600.0) == pytest.approx(1.0)
        assert convert_units("surface_net_thermal_radiation", 7200.0) == pytest.approx(2.0)

    def test_wind_unchanged(self):
        assert convert_units("u_component_of_wind_10m", 5.5) == pytest.approx(5.5)
        assert convert_units("v_component_of_wind_10m", -3.2) == pytest.approx(-3.2)

    def test_soil_moisture_unchanged(self):
        for layer in range(1, 5):
            var = f"volumetric_soil_water_layer_{layer}"
            assert convert_units(var, 0.35) == pytest.approx(0.35)


# ── Output column names (Caravan compliance) ──────────────────────────────────

class TestCaravanColumnNames:
    """
    Verify that the timeseries CSV column names match the Caravan specification
    after merge_era5land() rewrites the file.

    SILO columns have been removed (Feb 2026 reviewer feedback — SILO is
    Australian-only; Caravan requires globally available data).
    CSV now has 35 columns: date + streamflow + 33 ERA5-Land.
    """

    ERA5_LAND_COLS = frozenset(ERA5_COLS)

    SILO_COLS = frozenset([
        "total_precipitation_sum",
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "potential_evaporation_sum",
        "radiation_mj_m2_d",
        "vapour_pressure_hpa",
    ])

    def _run_merge(self, n_era5_days: int = 10) -> set:
        """Run merge_era5land with synthetic data; return set of output column names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_dir = Path(tmpdir) / "timeseries" / "csv" / "ausvic"
            ts_dir.mkdir(parents=True)
            ts_path = ts_dir / "test_gauge.csv"

            # Minimal streamflow CSV — one date in the ERA5 range
            with open(ts_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "streamflow"])
                writer.writerow(["2000-01-05", "1.23"])

            # Synthetic ERA5-Land data
            start = date(2000, 1, 1)
            era5_by_date = {}
            for i in range(n_era5_days):
                d = (start + timedelta(days=i)).isoformat()
                rec = {"date": d}
                for col in ERA5_COLS:
                    rec[col] = 0.1
                era5_by_date[d] = rec

            import fetch_era5land as fe5
            original_ts = fe5.TS_DIR
            fe5.TS_DIR = ts_dir
            merge_era5land({"gauge_id": "test_gauge"}, era5_by_date)
            fe5.TS_DIR = original_ts

            with open(ts_path, newline="") as f:
                rows = list(csv.DictReader(f))
            return set(rows[0].keys()) if rows else set()

    def test_timeseries_has_all_era5land_columns(self):
        cols = self._run_merge()
        assert self.ERA5_LAND_COLS.issubset(cols), (
            f"Missing ERA5-Land columns: {self.ERA5_LAND_COLS - cols}"
        )

    def test_timeseries_has_date_and_streamflow(self):
        cols = self._run_merge()
        assert "date" in cols
        assert "streamflow" in cols

    def test_no_silo_columns(self):
        cols = self._run_merge()
        present_silo = cols & self.SILO_COLS
        assert not present_silo, (
            f"SILO columns must be removed per Caravan reviewer: {present_silo}"
        )

    def test_no_old_column_names(self):
        cols = self._run_merge()
        old_names = {"streamflow_mmd", "precipitation_mmd", "pet_mmd"}
        assert not cols.intersection(old_names)

    def test_total_column_count(self):
        # 35 cols: date + streamflow + 33 ERA5-Land
        cols = self._run_merge()
        assert len(cols) == 35, f"Expected 35 columns, got {len(cols)}"

    def test_era5_dates_form_spine(self):
        """Output CSV should have rows for all ERA5 dates, not just streamflow dates."""
        n = 10
        cols_unused = self._run_merge(n_era5_days=n)  # triggers the merge
        # Re-run and count rows
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_dir = Path(tmpdir) / "timeseries" / "csv" / "ausvic"
            ts_dir.mkdir(parents=True)
            ts_path = ts_dir / "test_gauge.csv"
            with open(ts_path, "w", newline="") as f:
                csv.writer(f).writerow(["date", "streamflow"])
                csv.writer(f).writerow(["2000-01-05", "1.0"])
            start = date(2000, 1, 1)
            era5_by_date = {
                (start + timedelta(days=i)).isoformat(): {
                    "date": (start + timedelta(days=i)).isoformat(),
                    **{col: 0.1 for col in ERA5_COLS}
                }
                for i in range(n)
            }
            import fetch_era5land as fe5
            orig = fe5.TS_DIR
            fe5.TS_DIR = ts_dir
            merge_era5land({"gauge_id": "test_gauge"}, era5_by_date)
            fe5.TS_DIR = orig
            with open(ts_path, newline="") as f:
                row_count = sum(1 for _ in csv.DictReader(f))
        assert row_count == n, f"Expected {n} rows (ERA5 spine), got {row_count}"


# ── Gauge configuration ───────────────────────────────────────────────────────

class TestGaugeConfig:
    """Verify gauge_id format and count after Caravan reviewer changes."""

    def test_gauge_id_format(self):
        """All gauge IDs must be ausvic_XXXXXX (exactly two parts on _ split)."""
        from gauges_config import GAUGES
        for g in GAUGES:
            parts = g["gauge_id"].split("_")
            assert len(parts) == 2, (
                f"gauge_id {g['gauge_id']!r} has {len(parts)} parts — must be exactly 2"
            )
            assert parts[0] == "ausvic", (
                f"gauge_id {g['gauge_id']!r} must start with 'ausvic', not '{parts[0]}'"
            )

    def test_gauge_count(self):
        """Extension must have exactly 10 gauges (3 removed as CAMELS AUS v2 duplicates)."""
        from gauges_config import GAUGES
        assert len(GAUGES) == 10, (
            f"Expected 10 gauges, got {len(GAUGES)}"
        )

    def test_excluded_gauges_absent(self):
        """Stations 230205, 230209, 230210 must not appear (in CAMELS AUS v2)."""
        from gauges_config import GAUGES
        ids = {g["station_id"] for g in GAUGES}
        for excluded in ("230205", "230209", "230210"):
            assert excluded not in ids, (
                f"Station {excluded} is in CAMELS AUS v2 and must be excluded"
            )

    def test_all_gauges_have_area(self):
        from gauges_config import GAUGES
        for g in GAUGES:
            assert g["area_km2"] is not None, (
                f"area_km2 not set for {g['gauge_id']}"
            )
            assert g["area_km2"] > 0
