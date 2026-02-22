"""
tests/test_pipeline.py

Unit and integration tests for the FloodHubMaribyrnong pipeline.
No API calls — all tests use synthetic data.

Run with:
    pip install pytest
    pytest tests/
"""

import csv
import io
import sys
import tempfile
from pathlib import Path

import pytest

# Allow imports from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_maribyrnong import ml_day_to_mm_day, deduplicate
from fetch_silo_met import safe_float, detect_columns
from fetch_era5land import convert_units


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


# ── fetch_silo_met ────────────────────────────────────────────────────────────

class TestSafeFloat:
    def test_valid_number(self):
        assert safe_float("3.14") == pytest.approx(3.14)

    def test_integer_string(self):
        assert safe_float("42") == pytest.approx(42.0)

    def test_empty_string(self):
        assert safe_float("") is None

    def test_none_input(self):
        assert safe_float(None) is None

    def test_missing_value_sentinel(self):
        # Values <= -999 are treated as missing
        assert safe_float("-999.9") is None
        assert safe_float("-1000") is None

    def test_negative_valid(self):
        # Values > -999 are valid (e.g. negative temperatures)
        assert safe_float("-5.0") == pytest.approx(-5.0)

    def test_non_numeric(self):
        assert safe_float("N/A") is None


class TestDetectColumns:
    def test_exact_match(self):
        fields = ["Date", "daily_rain", "max_temp", "min_temp",
                  "et_morton_pot", "radiation", "vp"]
        result = detect_columns(fields)
        assert result["daily_rain"] == "daily_rain"
        assert result["max_temp"] == "max_temp"
        assert result["et_morton_pot"] == "et_morton_pot"

    def test_alias_match(self):
        # SILO sometimes uses alternate column names
        fields = ["Date", "rain", "maximum_temperature", "minimum_temperature",
                  "et_morton_potential", "solar_radiation", "vapour_pressure"]
        result = detect_columns(fields)
        assert result["daily_rain"] == "rain"
        assert result["max_temp"] == "maximum_temperature"
        assert result["et_morton_pot"] == "et_morton_potential"

    def test_missing_column_returns_none(self):
        result = detect_columns(["Date", "daily_rain"])
        assert result["max_temp"] is None

    def test_all_canonical_keys_present(self):
        result = detect_columns([])
        expected_keys = {"daily_rain", "max_temp", "min_temp",
                         "et_morton_pot", "radiation", "vp"}
        assert set(result.keys()) == expected_keys


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


# ── Climate stats (tested via merge_gauge with synthetic data) ────────────────

class TestClimateSats:
    """
    Tests climate statistics calculated inside merge_gauge() by running it
    with a synthetic timeseries CSV and SILO rows.
    """

    def _make_silo_rows(self, n_days: int, rain: float, pet: float) -> list[dict]:
        """Create synthetic SILO rows with constant rain and PET."""
        from datetime import date, timedelta
        rows = []
        start = date(2000, 1, 1)
        for i in range(n_days):
            d = start + timedelta(days=i)
            rows.append({
                "Date": d.strftime("%Y%m%d"),
                "daily_rain": str(rain),
                "max_temp": "25.0",
                "min_temp": "15.0",
                "et_morton_pot": str(pet),
                "radiation": "20.0",
                "vp": "12.0",
            })
        return rows

    def _run_merge(self, rain: float, pet: float, n_days: int = 365) -> dict | None:
        """Run merge_gauge with synthetic data and return climate stats."""
        from datetime import date, timedelta
        from fetch_silo_met import merge_gauge

        with tempfile.TemporaryDirectory() as tmpdir:
            ts_dir = Path(tmpdir) / "timeseries" / "csv" / "aus_vic"
            ts_dir.mkdir(parents=True)

            # Write synthetic streamflow CSV
            ts_path = ts_dir / "test_gauge.csv"
            with open(ts_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "streamflow"])
                start = date(2000, 1, 1)
                for i in range(n_days):
                    d = start + timedelta(days=i)
                    writer.writerow([d.isoformat(), "1.0"])

            # Patch TS_DIR to point to tmpdir
            import fetch_silo_met as fsm
            original = fsm.TS_DIR
            fsm.TS_DIR = ts_dir

            gauge = {"gauge_id": "test_gauge"}
            silo_rows = self._make_silo_rows(n_days, rain, pet)
            result = merge_gauge(gauge, silo_rows)

            fsm.TS_DIR = original
            return result

    def test_p_mean(self):
        result = self._run_merge(rain=5.0, pet=4.0)
        assert result is not None
        assert result["p_mean"] == pytest.approx(5.0, abs=1e-3)

    def test_pet_mean(self):
        result = self._run_merge(rain=5.0, pet=4.0)
        assert result["pet_mean"] == pytest.approx(4.0, abs=1e-3)

    def test_aridity(self):
        # aridity = PET/P
        result = self._run_merge(rain=4.0, pet=8.0)
        assert result["aridity"] == pytest.approx(2.0, abs=1e-3)

    def test_frac_snow_zero(self):
        # Victoria — always 0
        result = self._run_merge(rain=5.0, pet=4.0)
        assert result["frac_snow"] == 0.0

    def test_moisture_index_dry(self):
        # PET >> P → MI close to +1
        result = self._run_merge(rain=1.0, pet=10.0)
        # MI = (PET-P)/(PET+P) = 9/11 ≈ 0.818
        assert result["moisture_index"] == pytest.approx(9 / 11, abs=1e-2)

    def test_moisture_index_wet(self):
        # P >> PET → MI close to -1
        result = self._run_merge(rain=10.0, pet=1.0)
        # MI = (1-10)/(1+10) = -9/11 ≈ -0.818
        assert result["moisture_index"] == pytest.approx(-9 / 11, abs=1e-2)

    def test_low_prec_freq_all_dry(self):
        # All days < 1 mm → low_prec_freq = 1.0
        result = self._run_merge(rain=0.5, pet=2.0)
        assert result["low_prec_freq"] == pytest.approx(1.0)

    def test_high_prec_freq_all_normal(self):
        # Constant rain = mean → no day exceeds 5×mean → 0
        result = self._run_merge(rain=5.0, pet=4.0)
        assert result["high_prec_freq"] == pytest.approx(0.0)

    def test_result_has_all_required_keys(self):
        result = self._run_merge(rain=3.0, pet=4.0)
        required = {
            "gauge_id", "p_mean", "pet_mean", "aridity", "frac_snow",
            "moisture_index", "moisture_index_seasonality",
            "high_prec_freq", "high_prec_dur",
            "low_prec_freq", "low_prec_dur",
        }
        assert required.issubset(set(result.keys()))


# ── Output column names (Caravan compliance) ──────────────────────────────────

class TestCaravanColumnNames:
    """Verify that output CSV column names match the Caravan specification."""

    REQUIRED_TIMESERIES_COLS = {
        "date",
        "streamflow",
        "total_precipitation_sum",
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "potential_evaporation_sum",
        "radiation_mj_m2_d",
        "vapour_pressure_hpa",
    }

    REQUIRED_CARAVAN_ATTR_COLS = {
        "gauge_id", "p_mean", "pet_mean", "aridity", "frac_snow",
        "moisture_index", "moisture_index_seasonality",
        "high_prec_freq", "high_prec_dur",
        "low_prec_freq", "low_prec_dur",
    }

    REQUIRED_OTHER_ATTR_COLS = {
        "gauge_id", "gauge_name", "gauge_lat", "gauge_lon",
        "country", "area", "streamflow_period", "streamflow_missing",
    }

    def _merge_output_cols(self, rain: float = 3.0, pet: float = 4.0,
                           n_days: int = 365) -> list[str]:
        """Return column names from the timeseries CSV after a SILO merge."""
        from datetime import date, timedelta
        from fetch_silo_met import merge_gauge

        with tempfile.TemporaryDirectory() as tmpdir:
            ts_dir = Path(tmpdir) / "timeseries" / "csv" / "aus_vic"
            ts_dir.mkdir(parents=True)
            ts_path = ts_dir / "test_gauge.csv"

            with open(ts_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "streamflow"])
                start = date(2000, 1, 1)
                for i in range(n_days):
                    d = start + timedelta(days=i)
                    writer.writerow([d.isoformat(), "1.0"])

            silo_rows = []
            start = date(2000, 1, 1)
            for i in range(n_days):
                d = start + timedelta(days=i)
                silo_rows.append({
                    "Date": d.strftime("%Y%m%d"),
                    "daily_rain": str(rain),
                    "max_temp": "25.0",
                    "min_temp": "15.0",
                    "et_morton_pot": str(pet),
                    "radiation": "20.0",
                    "vp": "12.0",
                })

            import fetch_silo_met as fsm
            original = fsm.TS_DIR
            fsm.TS_DIR = ts_dir
            merge_gauge({"gauge_id": "test_gauge"}, silo_rows)
            fsm.TS_DIR = original

            with open(ts_path, newline="") as f:
                return list(csv.DictReader(f))[0].keys()

    def test_timeseries_has_required_columns(self):
        cols = set(self._merge_output_cols())
        assert self.REQUIRED_TIMESERIES_COLS.issubset(cols), (
            f"Missing columns: {self.REQUIRED_TIMESERIES_COLS - cols}"
        )

    def test_no_old_column_names(self):
        cols = set(self._merge_output_cols())
        old_names = {"streamflow_mmd", "precipitation_mmd", "pet_mmd"}
        assert not cols.intersection(old_names), (
            f"Old column names still present: {cols.intersection(old_names)}"
        )

    def test_caravan_attr_keys(self):
        from datetime import date, timedelta
        from fetch_silo_met import merge_gauge

        with tempfile.TemporaryDirectory() as tmpdir:
            ts_dir = Path(tmpdir) / "timeseries" / "csv" / "aus_vic"
            ts_dir.mkdir(parents=True)
            ts_path = ts_dir / "test_gauge.csv"

            n_days = 365
            with open(ts_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "streamflow"])
                start = date(2000, 1, 1)
                for i in range(n_days):
                    d = start + timedelta(days=i)
                    writer.writerow([d.isoformat(), "1.0"])

            silo_rows = []
            start = date(2000, 1, 1)
            for i in range(n_days):
                d = start + timedelta(days=i)
                silo_rows.append({
                    "Date": d.strftime("%Y%m%d"),
                    "daily_rain": "3.0", "max_temp": "25.0",
                    "min_temp": "15.0", "et_morton_pot": "4.0",
                    "radiation": "20.0", "vp": "12.0",
                })

            import fetch_silo_met as fsm
            original = fsm.TS_DIR
            fsm.TS_DIR = ts_dir
            result = merge_gauge({"gauge_id": "test_gauge"}, silo_rows)
            fsm.TS_DIR = original

        assert result is not None
        assert self.REQUIRED_CARAVAN_ATTR_COLS.issubset(set(result.keys())), (
            f"Missing keys: {self.REQUIRED_CARAVAN_ATTR_COLS - set(result.keys())}"
        )
