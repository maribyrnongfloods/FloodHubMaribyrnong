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
  - Updated column count to 41: date + streamflow + 39 ERA5-Land
    (added temperature_2m ×3, total_precipitation_sum, PET ERA5, PET FAO PM)
"""

import csv
import tempfile
from datetime import date, timedelta
from pathlib import Path
import sys

import pytest

# Allow imports from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

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
        assert convert_units("temperature_2m", 273.15) == pytest.approx(0.0)
        assert convert_units("temperature_2m", 293.15) == pytest.approx(20.0)

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
    CSV now has 41 columns: date + streamflow + 39 ERA5-Land:
      - 10 instantaneous vars × 3 (mean/min/max) = 30
      - 2  accumulated flux vars × 3             =  6
      - total_precipitation_sum                  =  1
      - potential_evaporation_sum_ERA5_LAND       =  1
      - potential_evaporation_sum_FAO_PENMAN_MONTEITH = 1
    """

    ERA5_LAND_COLS = frozenset(ERA5_COLS)

    # These are the SILO-specific column names that must NOT appear.
    # temperature_2m_* and total_precipitation_sum are now legitimate ERA5-Land
    # columns; only the truly SILO-only variables are banned.
    SILO_COLS = frozenset([
        "potential_evaporation_sum",   # Morton PET — SILO only (renamed in ERA5)
        "radiation_mj_m2_d",           # SILO shortwave radiation
        "vapour_pressure_hpa",         # SILO vapour pressure
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

            # Synthetic daily ERA5-Land DataFrame (new interface)
            start = date(2000, 1, 1)
            dates = pd.date_range(start, periods=n_era5_days, freq='D')
            daily = pd.DataFrame(
                {col: [0.1] * n_era5_days for col in ERA5_COLS},
                index=dates,
            )
            daily.index.name = "date"

            import fetch_era5land as fe5
            original_ts = fe5.TS_DIR
            fe5.TS_DIR = ts_dir
            merge_era5land({"gauge_id": "test_gauge"}, daily)
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
        # 41 cols: date + streamflow + 39 ERA5-Land
        cols = self._run_merge()
        assert len(cols) == 41, f"Expected 41 columns, got {len(cols)}"

    def test_era5_dates_form_spine(self):
        """Output CSV should have rows for all ERA5 dates, not just streamflow dates."""
        n = 10
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_dir = Path(tmpdir) / "timeseries" / "csv" / "ausvic"
            ts_dir.mkdir(parents=True)
            ts_path = ts_dir / "test_gauge.csv"
            with open(ts_path, "w", newline="") as f:
                csv.writer(f).writerow(["date", "streamflow"])
                csv.writer(f).writerow(["2000-01-05", "1.0"])

            start = date(2000, 1, 1)
            dates = pd.date_range(start, periods=n, freq='D')
            daily = pd.DataFrame(
                {col: [0.1] * n for col in ERA5_COLS},
                index=dates,
            )
            daily.index.name = "date"

            import fetch_era5land as fe5
            orig = fe5.TS_DIR
            fe5.TS_DIR = ts_dir
            merge_era5land({"gauge_id": "test_gauge"}, daily)
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
        """Extension must have exactly 12 gauges.
        Removed: 3 CAMELS AUS v2 duplicates (230210, 230205, 230209) + 1 agency duplicate
                 (230104A co-located with Hydstra 230202; 230202 kept, longer record).
        Added:   3 new gauges Feb 2026 (230102A Deep Creek at Bulla,
                 230237A Keilor North, 230119A Maribyrnong River at Lancefield).
        """
        from gauges_config import GAUGES
        assert len(GAUGES) == 12, (
            f"Expected 12 gauges, got {len(GAUGES)}"
        )

    def test_excluded_gauges_absent(self):
        """Stations 230205, 230209, 230210 must not appear (in CAMELS AUS v2).
        230104A must also be absent (duplicate of co-located Hydstra gauge 230202)."""
        from gauges_config import GAUGES
        ids = {g["station_id"] for g in GAUGES}
        for excluded in ("230205", "230209", "230210", "230104A"):
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


# ── fetch_hydroatlas_polygon (Caravan Part-1 notebook fidelity) ───────────────

class TestHydroatlasPropertyLists:
    """
    Verify that the property-list constants match the Caravan Part-1 notebook
    verbatim. These lists determine which HydroATLAS attributes appear in the
    final CSV and how each one is aggregated. A mistake here propagates to
    every value in attributes_hydroatlas_ausvic.csv.
    """

    def test_majority_properties_count(self):
        """10 class properties use area-weighted majority vote."""
        from fetch_hydroatlas_polygon import MAJORITY_PROPERTIES
        assert len(MAJORITY_PROPERTIES) == 10

    def test_majority_properties_content(self):
        from fetch_hydroatlas_polygon import MAJORITY_PROPERTIES
        expected = {
            'clz_cl_smj', 'cls_cl_smj', 'glc_cl_smj', 'pnv_cl_smj',
            'wet_cl_smj', 'tbi_cl_smj', 'tec_cl_smj', 'fmh_cl_smj',
            'fec_cl_smj', 'lit_cl_smj',
        }
        assert set(MAJORITY_PROPERTIES) == expected

    def test_pour_point_properties_count(self):
        """9 upstream-only properties taken from most-downstream sub-basin."""
        from fetch_hydroatlas_polygon import POUR_POINT_PROPERTIES
        assert len(POUR_POINT_PROPERTIES) == 9

    def test_pour_point_properties_content(self):
        from fetch_hydroatlas_polygon import POUR_POINT_PROPERTIES
        expected = {
            'dis_m3_pmn', 'dis_m3_pmx', 'dis_m3_pyr',
            'lkv_mc_usu', 'rev_mc_usu', 'ria_ha_usu', 'riv_tc_usu',
            'pop_ct_usu', 'dor_pc_pva',
        }
        assert set(POUR_POINT_PROPERTIES) == expected

    def test_ignore_properties_count(self):
        """10 HydroSHEDS/RIVERS fields ignored entirely."""
        from fetch_hydroatlas_polygon import IGNORE_PROPERTIES
        assert len(IGNORE_PROPERTIES) == 10

    def test_ignore_includes_system_index(self):
        from fetch_hydroatlas_polygon import IGNORE_PROPERTIES
        assert 'system:index' in IGNORE_PROPERTIES

    def test_upstream_properties_count(self):
        """86 upstream-aggregate properties excluded (per-polygon counterparts kept)."""
        from fetch_hydroatlas_polygon import UPSTREAM_PROPERTIES
        assert len(UPSTREAM_PROPERTIES) == 86

    def test_upstream_properties_sample(self):
        """Spot-check key upstream properties that the notebook explicitly excludes."""
        from fetch_hydroatlas_polygon import UPSTREAM_PROPERTIES
        must_exclude = [
            'aet_mm_uyr', 'ari_ix_uav', 'pre_mm_uyr', 'pet_mm_uyr',
            'wet_pc_ug1', 'wet_pc_ug2', 'gad_id_smj',
            'ele_mt_uav', 'slp_dg_uav', 'tmp_dc_uyr',
        ]
        for p in must_exclude:
            assert p in UPSTREAM_PROPERTIES, (
                f"'{p}' must be in UPSTREAM_PROPERTIES (excluded from output)"
            )

    def test_additional_properties(self):
        """Auxiliary processing fields: kept in USE_PROPERTIES for pour-point traversal."""
        from fetch_hydroatlas_polygon import ADDITIONAL_PROPERTIES
        assert set(ADDITIONAL_PROPERTIES) == {'HYBAS_ID', 'NEXT_DOWN', 'SUB_AREA', 'UP_AREA'}

    def test_no_overlap_between_ignore_and_upstream(self):
        from fetch_hydroatlas_polygon import IGNORE_PROPERTIES, UPSTREAM_PROPERTIES
        overlap = set(IGNORE_PROPERTIES) & set(UPSTREAM_PROPERTIES)
        assert not overlap, f"IGNORE and UPSTREAM must be disjoint, got: {overlap}"

    def test_pour_point_not_in_upstream(self):
        """Pour-point properties must NOT be excluded — they are in USE_PROPERTIES."""
        from fetch_hydroatlas_polygon import POUR_POINT_PROPERTIES, UPSTREAM_PROPERTIES
        in_both = set(POUR_POINT_PROPERTIES) & set(UPSTREAM_PROPERTIES)
        assert not in_both, (
            f"Pour-point props must be kept (in USE_PROPERTIES): {in_both}"
        )

    def test_pour_point_not_in_ignore(self):
        from fetch_hydroatlas_polygon import POUR_POINT_PROPERTIES, IGNORE_PROPERTIES
        assert not (set(POUR_POINT_PROPERTIES) & set(IGNORE_PROPERTIES))

    def test_additional_not_in_ignore_or_upstream(self):
        """HYBAS_ID, NEXT_DOWN, SUB_AREA, UP_AREA must survive into USE_PROPERTIES."""
        from fetch_hydroatlas_polygon import (
            ADDITIONAL_PROPERTIES, IGNORE_PROPERTIES, UPSTREAM_PROPERTIES,
        )
        for prop in ADDITIONAL_PROPERTIES:
            assert prop not in IGNORE_PROPERTIES, (
                f"'{prop}' must NOT be in IGNORE_PROPERTIES"
            )
            assert prop not in UPSTREAM_PROPERTIES, (
                f"'{prop}' must NOT be in UPSTREAM_PROPERTIES"
            )

    def test_use_properties_count_from_mock(self):
        """
        Simulate the notebook's property-name list (295 total) and verify
        that USE_PROPERTIES = 199 (295 − 10 ignore − 86 upstream).
        This mirrors the notebook's printed 'Remaining: 194' diagnostic.
        """
        from fetch_hydroatlas_polygon import (
            IGNORE_PROPERTIES, UPSTREAM_PROPERTIES, ADDITIONAL_PROPERTIES,
        )
        # Build a synthetic list representing HydroATLAS Level-12 propertyNames()
        remaining_real = 295 - len(IGNORE_PROPERTIES) - len(UPSTREAM_PROPERTIES)
        mock_all = (
            IGNORE_PROPERTIES
            + UPSTREAM_PROPERTIES
            + ADDITIONAL_PROPERTIES
            + [f'real_prop_{i}' for i in range(remaining_real - len(ADDITIONAL_PROPERTIES))]
        )
        assert len(mock_all) == 295, "Mock list must total 295 to match the notebook"

        exclude = set(IGNORE_PROPERTIES + UPSTREAM_PROPERTIES)
        use_props = [p for p in mock_all if p not in exclude]
        assert len(use_props) == 199, (
            f"USE_PROPERTIES must be 199 (got {len(use_props)}); "
            "notebook: 295 total − 10 ignore − 86 upstream = 199"
        )

        # The notebook prints: len(USE_PROPERTIES) - 1 - len(additional_properties) = 194
        notebook_display = len(use_props) - 1 - len(ADDITIONAL_PROPERTIES)
        assert notebook_display == 194, (
            f"Notebook 'Remaining' display must be 194, got {notebook_display}"
        )


class TestToFloat:
    """Verify the None-safe float conversion used during aggregation."""

    def test_none_returns_nan(self):
        import math
        from fetch_hydroatlas_polygon import _to_float
        assert math.isnan(_to_float(None))

    def test_integer_converted(self):
        from fetch_hydroatlas_polygon import _to_float
        assert _to_float(42) == 42.0

    def test_float_unchanged(self):
        from fetch_hydroatlas_polygon import _to_float
        assert _to_float(3.14) == pytest.approx(3.14)

    def test_negative_sentinel_preserved(self):
        """−999 must pass through as −999.0 (excluded later in aggregation)."""
        from fetch_hydroatlas_polygon import _to_float
        assert _to_float(-999) == -999.0

    def test_zero_preserved(self):
        from fetch_hydroatlas_polygon import _to_float
        assert _to_float(0) == 0.0


class TestComputePourPointProperties:
    """
    Tests for compute_pour_point_properties() — the pour-point downstream
    traversal logic translated verbatim from the Caravan Part-1 notebook.
    """

    def _make_basin_data(self, hybas_ids, next_downs, sub_areas, weights, prop_vals):
        from collections import defaultdict
        d = defaultdict(list)
        d['HYBAS_ID']  = list(hybas_ids)
        d['NEXT_DOWN'] = list(next_downs)
        d['SUB_AREA']  = list(sub_areas)
        d['weights']   = list(weights)
        d['test_prop'] = list(prop_vals)
        return d

    def test_single_basin_ocean_termination(self):
        """Single sub-basin draining to ocean (NEXT_DOWN=0): value taken directly."""
        from fetch_hydroatlas_polygon import compute_pour_point_properties
        d = self._make_basin_data(
            hybas_ids =[1001],
            next_downs=[0],
            sub_areas =[100],
            weights   =[80],
            prop_vals =[42.0],
        )
        result = compute_pour_point_properties(d, min_overlap_threshold=0,
                                               pour_point_properties=['test_prop'])
        assert result['test_prop'] == 42.0

    def test_traversal_stops_at_low_overlap(self):
        """
        Chain A→B→C(ocean). B has only 3% overlap → traversal stops before B.
        direct upstream of B is A → pour-point = A's value.
        """
        from fetch_hydroatlas_polygon import compute_pour_point_properties
        d = self._make_basin_data(
            hybas_ids =[1, 2, 3],
            next_downs=[2, 3, 0],
            sub_areas =[100, 1000, 500],
            weights   =[100, 30, 250],   # B = 3% overlap
            prop_vals =[10.0, 20.0, 30.0],
        )
        # percentage_overlap = [1.0, 0.03, 0.5]
        # argmax=0 (A), next_down=2 (B)
        # B: overlap=0.03 < 0.5 → STOP, next_down_id stays at 2
        # direct upstream of 2: A (NEXT_DOWN=2, weight=100>0) → qualifies
        result = compute_pour_point_properties(d, min_overlap_threshold=0,
                                               pour_point_properties=['test_prop'])
        assert result['test_prop'] == 10.0

    def test_traversal_continues_when_overlap_exactly_half(self):
        """
        Boundary case: overlap == 0.5 is NOT < 0.5, so traversal continues.
        """
        from fetch_hydroatlas_polygon import compute_pour_point_properties
        d = self._make_basin_data(
            hybas_ids =[1, 2],
            next_downs=[2, 0],
            sub_areas =[100, 200],
            weights   =[100, 100],   # B = 100/200 = 0.5 exactly
            prop_vals =[10.0, 20.0],
        )
        # percentage_overlap = [1.0, 0.5]
        # argmax=0, next_down=2; B: 0.5 not < 0.5 → continue
        # next_down=0 → stop; direct upstream of 0: B (NEXT_DOWN=0) → qualifies
        result = compute_pour_point_properties(d, min_overlap_threshold=0,
                                               pour_point_properties=['test_prop'])
        assert result['test_prop'] == 20.0

    def test_traversal_stops_when_next_down_outside_set(self):
        """Traversal stops when NEXT_DOWN points to an ID not in HYBAS_ID list."""
        from fetch_hydroatlas_polygon import compute_pour_point_properties
        d = self._make_basin_data(
            hybas_ids =[1],
            next_downs=[999],   # 999 is not in the set
            sub_areas =[100],
            weights   =[100],
            prop_vals =[7.0],
        )
        # next_down=999 not in [1] → stop immediately
        # direct upstream of 999: basin 0 (NEXT_DOWN=999) → qualifies
        result = compute_pour_point_properties(d, min_overlap_threshold=0,
                                               pour_point_properties=['test_prop'])
        assert result['test_prop'] == 7.0

    def test_sums_two_tributaries(self):
        """
        Two tributaries A and B both drain to junction C (NEXT_DOWN=4, outside
        set). pour-point = sum of A + B.
        """
        from fetch_hydroatlas_polygon import compute_pour_point_properties
        d = self._make_basin_data(
            hybas_ids =[1, 2, 3],
            next_downs=[4, 4, 0],
            sub_areas =[100, 100, 500],
            weights   =[100, 100, 10],   # A=100%, B=100%, C=2%
            prop_vals =[15.0, 25.0, 50.0],
        )
        # percentage_overlap = [1.0, 1.0, 0.02]
        # argmax=0, next_down=4; 4 not in [1,2,3] → stop
        # direct upstream of 4: A (NEXT_DOWN=4) and B (NEXT_DOWN=4), both qualify
        result = compute_pour_point_properties(d, min_overlap_threshold=0,
                                               pour_point_properties=['test_prop'])
        assert result['test_prop'] == 40.0   # 15 + 25

    def test_pour_point_returns_zero_for_unknown_prop(self):
        """Unknown pour-point prop sums over direct-upstream → 0 if values are 0."""
        from fetch_hydroatlas_polygon import compute_pour_point_properties
        d = self._make_basin_data(
            hybas_ids =[1],
            next_downs=[0],
            sub_areas =[100],
            weights   =[100],
            prop_vals =[0.0],
        )
        result = compute_pour_point_properties(d, min_overlap_threshold=0,
                                               pour_point_properties=['test_prop'])
        assert result['test_prop'] == 0.0


class TestAggregateHydroatlasIntersections:
    """
    Tests for aggregate_hydroatlas_intersections() — the notebook's aggregation
    step translated verbatim. Covers weighted average, majority vote, -999
    sentinel handling, area computation, and output column presence.
    """

    def _make_basin_data(self, weights, area_fragments=None, **kwargs):
        """
        Build a synthetic basin_data dict. Required fields (HYBAS_ID etc.) are
        auto-filled. Extra keyword args add named property lists.
        """
        from collections import defaultdict
        from fetch_hydroatlas_polygon import POUR_POINT_PROPERTIES
        n = len(weights)
        d = defaultdict(list)
        d['weights']        = list(weights)
        d['area_fragments'] = list(area_fragments if area_fragments is not None else weights)
        # Required auxiliary fields
        d['HYBAS_ID']  = list(range(1, n + 1))
        d['NEXT_DOWN'] = [0] * n        # all drain directly to ocean
        d['SUB_AREA']  = [float(w) if w > 0 else 1.0 for w in weights]
        d['UP_AREA']   = list(weights)
        # Ensure all pour-point props are present (zero by default)
        for p in POUR_POINT_PROPERTIES:
            d[p] = [0.0] * n
        # Add caller-supplied properties
        for k, v in kwargs.items():
            d[k] = list(v)
        return d

    # ── area columns ──────────────────────────────────────────────────────────

    def test_area_equals_sum_of_fragments(self):
        """'area' = sum of ALL area_fragments (including tiny sliver pieces)."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[10.0, 20.0],
                                  area_fragments=[10.0, 20.0, 5.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        assert result['area'] == pytest.approx(35.0)

    def test_area_fraction_correct(self):
        """area_fraction = sum(masked_weights) / sum(area_fragments)."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[10.0, 20.0],
                                  area_fragments=[10.0, 20.0, 5.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        # mask = weights > 0: both qualify → sum(masked) = 30; sum(fragments) = 35
        assert result['area_fraction_used_for_aggregation'] == pytest.approx(30.0 / 35.0)

    # ── weighted average ──────────────────────────────────────────────────────

    def test_weighted_average_basic(self):
        """Two sub-basins: (2.0 × 1 + 6.0 × 3) / (1 + 3) = 5.0."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[1.0, 3.0], my_prop=[2.0, 6.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        assert result['my_prop'] == pytest.approx(5.0)

    def test_weighted_average_equal_weights(self):
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[1.0, 1.0], my_prop=[4.0, 8.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        assert result['my_prop'] == pytest.approx(6.0)

    # ── -999 sentinel handling ────────────────────────────────────────────────

    def test_negative_999_excluded_from_average(self):
        """-999 sentinel values must be excluded from the weighted average."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(
            weights=[1.0, 2.0, 3.0],
            my_prop=[-999.0, 4.0, 6.0],
        )
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        # Only indices 1 and 2 contribute: (4*2 + 6*3) / (2+3) = 26/5 = 5.2
        assert result['my_prop'] == pytest.approx(5.2)

    def test_all_negative_999_gives_nan(self):
        """All -999 → NaN (per notebook: 'if all values are -999, set to NaN')."""
        import math
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[1.0, 2.0], my_prop=[-999.0, -999.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        assert math.isnan(result['my_prop'])

    def test_none_values_treated_as_missing(self):
        """None (missing GEE property) is treated like NaN — excluded from average."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[1.0, 2.0], my_prop=[None, 4.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        # Only index 1 (4.0, weight=2) contributes
        assert result['my_prop'] == pytest.approx(4.0)

    # ── majority vote ─────────────────────────────────────────────────────────

    def test_majority_vote_higher_weight_wins(self):
        """Class property: the class with higher total weight wins."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        # class 1 (weight 1) vs class 2 (weight 3) → class 2 wins
        d = self._make_basin_data(weights=[1.0, 3.0], clz_cl_smj=[1, 2])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        assert result['clz_cl_smj'] == 2

    def test_majority_vote_all_majority_props(self):
        """All 10 MAJORITY_PROPERTIES use weighted bincount, not average."""
        from fetch_hydroatlas_polygon import (
            aggregate_hydroatlas_intersections, MAJORITY_PROPERTIES,
        )
        # For each majority prop: class 5 (weight 1) vs class 9 (weight 3) → 9 wins
        kwargs = {p: [5, 9] for p in MAJORITY_PROPERTIES}
        d = self._make_basin_data(weights=[1.0, 3.0], **kwargs)
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        for p in MAJORITY_PROPERTIES:
            assert result[p] == 9, (
                f"MAJORITY_PROPERTY '{p}' should be 9 (higher weight), got {result[p]}"
            )

    def test_wet_cl_smj_remaps_negative_999_to_13(self):
        """
        wet_cl_smj: -999 (no wetland) must be remapped to class 13 before
        majority vote. This is the notebook's special case.
        """
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        # Basin A: -999 (→ 13) with weight 3; Basin B: class 5 with weight 1
        d = self._make_basin_data(weights=[3.0, 1.0], wet_cl_smj=[-999, 5])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        # class 13 (remapped): weight 3; class 5: weight 1 → class 13 wins
        assert result['wet_cl_smj'] == 13

    def test_wet_cl_smj_negative_999_not_excluded_by_sentinel_filter(self):
        """
        For wet_cl_smj, -999 is remapped to 13 BEFORE the -999 filter,
        so it must NOT be excluded (unlike all other properties where -999 is excluded).
        """
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        # Both basins have -999; after remap → both class 13
        d = self._make_basin_data(weights=[2.0, 3.0], wet_cl_smj=[-999, -999])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        # After remap: [13, 13]. Neither is still -999, so 'all -999' check fails.
        # Majority vote over [13, 13] → 13
        assert result['wet_cl_smj'] == 13

    # ── auxiliary keys excluded from output ───────────────────────────────────

    def test_auxiliary_keys_not_in_output(self):
        """HYBAS_ID, NEXT_DOWN, SUB_AREA, UP_AREA must be skipped, not output."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[10.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        for key in ('HYBAS_ID', 'NEXT_DOWN', 'SUB_AREA', 'UP_AREA'):
            assert key not in result, f"Auxiliary key '{key}' must not appear in output"

    def test_pour_point_properties_in_output(self):
        """All 9 pour-point properties must appear in output (computed separately)."""
        from fetch_hydroatlas_polygon import (
            aggregate_hydroatlas_intersections, POUR_POINT_PROPERTIES,
        )
        d = self._make_basin_data(weights=[10.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        for p in POUR_POINT_PROPERTIES:
            assert p in result, f"Pour-point property '{p}' must be in output"

    def test_area_and_fraction_keys_present(self):
        """'area' and 'area_fraction_used_for_aggregation' must always be output."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[10.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        assert 'area' in result
        assert 'area_fraction_used_for_aggregation' in result

    # ── min_overlap_threshold ─────────────────────────────────────────────────

    def test_threshold_filters_small_intersections(self):
        """
        Sub-basins with weight <= min_overlap_threshold are excluded from
        the weighted average (but still counted in area_fragments).
        """
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(
            weights=[3.0, 10.0],
            area_fragments=[3.0, 10.0],
            my_prop=[100.0, 2.0],
        )
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=5)
        # Only weight=10, value=2.0 qualifies for the average
        assert result['my_prop'] == pytest.approx(2.0)
        # area still sums ALL fragments
        assert result['area'] == pytest.approx(13.0)
        # area_fraction = 10 / 13
        assert result['area_fraction_used_for_aggregation'] == pytest.approx(10.0 / 13.0)

    def test_threshold_zero_includes_all(self):
        """With min_overlap_threshold=0 (our config), all positive-weight basins qualify."""
        from fetch_hydroatlas_polygon import aggregate_hydroatlas_intersections
        d = self._make_basin_data(weights=[0.001, 5.0], my_prop=[10.0, 20.0])
        result = aggregate_hydroatlas_intersections(d, min_overlap_threshold=0)
        # Both qualify; weighted avg = (10*0.001 + 20*5) / 5.001 ≈ 20.0
        expected = (10.0 * 0.001 + 20.0 * 5.0) / (0.001 + 5.0)
        assert result['my_prop'] == pytest.approx(expected)


# ── ERA5-Land notebook fidelity ───────────────────────────────────────────────

class TestEra5lNotebookFidelity:
    """
    Verify that the constants in fetch_era5land.py exactly match the notebook
    configuration (Caravan_part2_local_postprocessing.ipynb).

    A single wrong variable name here would silently corrupt the output.
    """

    def test_gee_collection_is_hourly(self):
        from fetch_era5land import GEE_COLLECTION
        assert GEE_COLLECTION == "ECMWF/ERA5_LAND/HOURLY", (
            f"Must use hourly collection, got {GEE_COLLECTION!r}. "
            "Daily aggregation must NOT be used — the notebook fetches raw hourly."
        )

    def test_mean_vars_count(self):
        """Notebook MEAN_VARS has exactly 12 variables (10 state + 2 radiation)."""
        from fetch_era5land import MEAN_VARS
        assert len(MEAN_VARS) == 12, f"Expected 12 MEAN_VARS, got {len(MEAN_VARS)}"

    def test_mean_vars_content(self):
        """MEAN_VARS must match notebook verbatim."""
        from fetch_era5land import MEAN_VARS
        expected = {
            'snow_depth_water_equivalent',
            'surface_net_solar_radiation',
            'surface_net_thermal_radiation',
            'surface_pressure',
            'temperature_2m',
            'dewpoint_temperature_2m',
            'u_component_of_wind_10m',
            'v_component_of_wind_10m',
            'volumetric_soil_water_layer_1',
            'volumetric_soil_water_layer_2',
            'volumetric_soil_water_layer_3',
            'volumetric_soil_water_layer_4',
        }
        assert set(MEAN_VARS) == expected

    def test_min_max_equal_mean(self):
        """MIN_VARS and MAX_VARS must be the same list as MEAN_VARS (notebook config)."""
        from fetch_era5land import MEAN_VARS, MIN_VARS, MAX_VARS
        assert MIN_VARS is MEAN_VARS or MIN_VARS == MEAN_VARS, "MIN_VARS must equal MEAN_VARS"
        assert MAX_VARS is MEAN_VARS or MAX_VARS == MEAN_VARS, "MAX_VARS must equal MEAN_VARS"

    def test_sum_vars_content(self):
        """SUM_VARS must be exactly ['total_precipitation', 'potential_evaporation']."""
        from fetch_era5land import SUM_VARS
        assert SUM_VARS == ['total_precipitation', 'potential_evaporation'], (
            f"SUM_VARS mismatch: {SUM_VARS!r}"
        )

    def test_era5l_bands_count(self):
        """ERA5L_BANDS should list exactly 14 hourly GEE band names."""
        from fetch_era5land import ERA5L_BANDS
        assert len(ERA5L_BANDS) == 14, f"Expected 14 ERA5L_BANDS, got {len(ERA5L_BANDS)}"

    def test_era5l_bands_includes_accumulated(self):
        """ERA5L_BANDS must include the 4 accumulated variables."""
        from fetch_era5land import ERA5L_BANDS
        for var in ('total_precipitation', 'potential_evaporation',
                    'surface_net_solar_radiation', 'surface_net_thermal_radiation'):
            assert var in ERA5L_BANDS, f"Accumulated variable '{var}' missing from ERA5L_BANDS"

    def test_era5_cols_count(self):
        """ERA5_COLS must produce exactly 39 output column names."""
        from fetch_era5land import ERA5_COLS
        assert len(ERA5_COLS) == 39, f"Expected 39 ERA5_COLS, got {len(ERA5_COLS)}: {ERA5_COLS}"

    def test_era5_cols_pet_names(self):
        """The two PET column names must use the exact Caravan-standard suffixes."""
        from fetch_era5land import ERA5_COLS
        assert "potential_evaporation_sum_ERA5_LAND" in ERA5_COLS
        assert "potential_evaporation_sum_FAO_PENMAN_MONTEITH" in ERA5_COLS

    def test_era5_cols_no_raw_pet(self):
        """'potential_evaporation_sum' (un-suffixed) must NOT appear in ERA5_COLS."""
        from fetch_era5land import ERA5_COLS
        assert "potential_evaporation_sum" not in ERA5_COLS, (
            "Raw potential_evaporation_sum must be renamed before output"
        )


# ── disaggregate_features ─────────────────────────────────────────────────────

class TestDisaggregateFeatures:
    """
    Verify the ERA5-Land hourly de-accumulation logic in disaggregate_features().

    ERA5-Land HOURLY (GEE) stores accumulated fluxes where val[00:00 UTC]
    equals the total from the previous 24-hour forecast period (forecast hour 24
    from the prior UTC day initialisation). After diff(1):
      - hour 00: correct  (= last hour of previous UTC day)
      - hour 01: WRONG    (= first_hour - prev_24h_total) → must be replaced
      - hour 02+: correct (consecutive hourly differences)
    """

    def _make_hourly_df(self, values: list, start: str = "2020-01-01 00:00") -> pd.DataFrame:
        """Build a single-column hourly DataFrame with a DatetimeIndex."""
        idx = pd.date_range(start, periods=len(values), freq='h')
        return pd.DataFrame({"total_precipitation": values}, index=idx)

    def test_diff_applied_to_accumulated_col(self):
        """After disaggregate, values should be hour-by-hour differences (not cumulative)."""
        from fetch_era5land import disaggregate_features
        # 3 days × 24 h; simple cumulative ramp 1, 2, 3, …
        # Use values that make the expected diffs obvious.
        # hour00=24, hour01=1, hour02=2, ..., hour23=23, hour24=24 (next day hour00)
        vals = list(range(1, 25)) + list(range(1, 25)) + list(range(1, 25))
        df = self._make_hourly_df(vals)
        result = disaggregate_features(df)
        col = result["total_precipitation"]
        # All hour==2..23 positions should be 1 (consecutive diffs of a ramp)
        for i in range(2, 24):
            assert col.iloc[i] == pytest.approx(1.0), (
                f"hour {i}: expected 1.0 (diff of ramp), got {col.iloc[i]}"
            )

    def test_hour_1_replaced_with_original(self):
        """Values at hour==01 UTC must be replaced with the original (not diff)."""
        from fetch_era5land import disaggregate_features
        # Build a sequence: 00:00=100, 01:00=2, 02:00=3, …
        # diff at 01:00 = 2 - 100 = -98 (wrong), should be replaced with 2
        vals = [100.0] + list(range(2, 25))   # 24 hours starting at 00:00
        df = self._make_hourly_df(vals, start="2020-01-01 00:00")
        result = disaggregate_features(df)
        # iloc[1] = hour 01:00
        assert result["total_precipitation"].iloc[1] == pytest.approx(2.0), (
            "hour 01 must be original value, not diff"
        )

    def test_first_row_replaced_with_original(self):
        """First row (diff = NaN) must be replaced with the original value."""
        from fetch_era5land import disaggregate_features
        vals = [5.0, 6.0, 7.0]
        df = self._make_hourly_df(vals, start="2020-01-01 00:00")
        result = disaggregate_features(df)
        assert result["total_precipitation"].iloc[0] == pytest.approx(5.0)
        assert not pd.isna(result["total_precipitation"].iloc[0])

    def test_non_accumulated_cols_unchanged(self):
        """Columns not in the accumulated list (e.g. temperature_2m) must not be touched."""
        from fetch_era5land import disaggregate_features
        idx = pd.date_range("2020-01-01 00:00", periods=24, freq='h')
        df = pd.DataFrame({
            "temperature_2m": [280.0 + i for i in range(24)],
            "total_precipitation": list(range(1, 25)),
        }, index=idx)
        original_temp = df["temperature_2m"].copy()
        result = disaggregate_features(df)
        pd.testing.assert_series_equal(result["temperature_2m"], original_temp)

    def test_output_shape_unchanged(self):
        """disaggregate_features must not change the shape of the DataFrame."""
        from fetch_era5land import disaggregate_features
        vals = list(range(1, 49))  # 48 rows
        df = self._make_hourly_df(vals)
        result = disaggregate_features(df)
        assert result.shape == df.shape


# ── era5l_unit_conversion ─────────────────────────────────────────────────────

class TestEra5lUnitConversion:
    """
    Verify that era5l_unit_conversion() applies the right multiplier/offset
    to each variable, and does NOT flip the PET sign (that happens before it
    in the notebook pipeline, not inside this function).
    """

    def _df(self, **kwargs) -> pd.DataFrame:
        """Build a one-row DataFrame from keyword args."""
        idx = pd.date_range("2020-01-01", periods=1, freq='h')
        return pd.DataFrame(kwargs, index=idx)

    def test_temperature_k_to_c(self):
        from fetch_era5land import era5l_unit_conversion
        df = self._df(temperature_2m=[273.15])
        result = era5l_unit_conversion(df)
        assert result["temperature_2m"].iloc[0] == pytest.approx(0.0)

    def test_dewpoint_k_to_c(self):
        from fetch_era5land import era5l_unit_conversion
        df = self._df(dewpoint_temperature_2m=[300.0])
        result = era5l_unit_conversion(df)
        assert result["dewpoint_temperature_2m"].iloc[0] == pytest.approx(300.0 - 273.15)

    def test_pressure_pa_to_kpa(self):
        from fetch_era5land import era5l_unit_conversion
        df = self._df(surface_pressure=[101325.0])
        result = era5l_unit_conversion(df)
        assert result["surface_pressure"].iloc[0] == pytest.approx(101.325)

    def test_snow_depth_m_to_mm(self):
        from fetch_era5land import era5l_unit_conversion
        df = self._df(snow_depth_water_equivalent=[0.005])
        result = era5l_unit_conversion(df)
        assert result["snow_depth_water_equivalent"].iloc[0] == pytest.approx(5.0)

    def test_solar_radiation_j_to_w(self):
        from fetch_era5land import era5l_unit_conversion
        df = self._df(surface_net_solar_radiation=[3600.0])
        result = era5l_unit_conversion(df)
        assert result["surface_net_solar_radiation"].iloc[0] == pytest.approx(1.0)

    def test_thermal_radiation_j_to_w(self):
        from fetch_era5land import era5l_unit_conversion
        df = self._df(surface_net_thermal_radiation=[7200.0])
        result = era5l_unit_conversion(df)
        assert result["surface_net_thermal_radiation"].iloc[0] == pytest.approx(2.0)

    def test_precipitation_m_to_mm(self):
        from fetch_era5land import era5l_unit_conversion
        df = self._df(total_precipitation=[0.002])
        result = era5l_unit_conversion(df)
        assert result["total_precipitation"].iloc[0] == pytest.approx(2.0)

    def test_pet_m_to_mm_no_sign_flip(self):
        """era5l_unit_conversion does m->mm on PET only; sign flip is NOT inside it."""
        from fetch_era5land import era5l_unit_conversion
        df = self._df(potential_evaporation=[0.003])
        result = era5l_unit_conversion(df)
        # 0.003 m * 1000 = 3.0 mm (positive stays positive — sign already flipped upstream)
        assert result["potential_evaporation"].iloc[0] == pytest.approx(3.0)

    def test_wind_components_unchanged(self):
        """u and v wind components have no unit conversion (already m/s)."""
        from fetch_era5land import era5l_unit_conversion
        df = self._df(u_component_of_wind_10m=[3.5], v_component_of_wind_10m=[-1.2])
        result = era5l_unit_conversion(df)
        assert result["u_component_of_wind_10m"].iloc[0] == pytest.approx(3.5)
        assert result["v_component_of_wind_10m"].iloc[0] == pytest.approx(-1.2)

    def test_soil_moisture_unchanged(self):
        """Volumetric soil water (all 4 layers) is already m3/m3, no conversion."""
        from fetch_era5land import era5l_unit_conversion
        df = self._df(
            volumetric_soil_water_layer_1=[0.3],
            volumetric_soil_water_layer_2=[0.25],
            volumetric_soil_water_layer_3=[0.2],
            volumetric_soil_water_layer_4=[0.15],
        )
        result = era5l_unit_conversion(df)
        for layer in range(1, 5):
            col = f"volumetric_soil_water_layer_{layer}"
            assert result[col].iloc[0] == pytest.approx(df[col].iloc[0])


# ── Basin extension process (wiki compliance) ─────────────────────────────────

class TestIdFieldName:
    """
    Enforce the wiki rule: the GEE asset shapefile must use a basin ID field
    whose name is NOT any HydroATLAS / HydroBASINS field name.

    Source: https://github.com/kratzert/Caravan/wiki/Extending-Caravan-with-new-basins
    "Make sure that the name of this field is different to any HydroATLAS field.
     For example, you can use `gauge_id` or `basin_id` but not `HYBAS_ID` or
     `PFAF_ID`, which are both field names in HydroATLAS."
    """

    def test_gauge_id_is_valid(self):
        """'gauge_id' is the recommended field name — must be accepted."""
        from validate_submission import validate_id_field_name
        validate_id_field_name("gauge_id")  # must not raise

    def test_basin_id_is_valid(self):
        """'basin_id' is another acceptable choice."""
        from validate_submission import validate_id_field_name
        validate_id_field_name("basin_id")

    def test_hybas_id_is_forbidden(self):
        """HYBAS_ID is explicitly called out in the wiki as forbidden."""
        from validate_submission import validate_id_field_name
        with pytest.raises(ValueError, match="HYBAS_ID"):
            validate_id_field_name("HYBAS_ID")

    def test_pfaf_id_is_forbidden(self):
        """PFAF_ID is explicitly called out in the wiki as forbidden."""
        from validate_submission import validate_id_field_name
        with pytest.raises(ValueError, match="PFAF_ID"):
            validate_id_field_name("PFAF_ID")

    def test_next_down_is_forbidden(self):
        """NEXT_DOWN is a HydroBASINS structural field — must be forbidden."""
        from validate_submission import validate_id_field_name
        with pytest.raises(ValueError):
            validate_id_field_name("NEXT_DOWN")

    def test_up_area_is_forbidden(self):
        """UP_AREA is a HydroBASINS structural field — must be forbidden."""
        from validate_submission import validate_id_field_name
        with pytest.raises(ValueError):
            validate_id_field_name("UP_AREA")

    def test_empty_string_is_rejected(self):
        """Empty field name is not valid."""
        from validate_submission import validate_id_field_name
        with pytest.raises(ValueError):
            validate_id_field_name("")

    def test_whitespace_only_is_rejected(self):
        from validate_submission import validate_id_field_name
        with pytest.raises(ValueError):
            validate_id_field_name("   ")


class TestGaugeIdValidation:
    """
    Enforce Caravan gauge_id format: exactly two parts when split on '_',
    all values unique, none empty.
    """

    def test_valid_ausvic_ids(self):
        from validate_submission import validate_gauge_ids
        ids = ["ausvic_230100", "ausvic_230200", "ausvic_230104"]
        validate_gauge_ids(ids)  # must not raise

    def test_single_valid_id(self):
        from validate_submission import validate_gauge_ids
        validate_gauge_ids(["ausvic_230200"])

    def test_three_part_id_rejected(self):
        """aus_vic_230100 has 3 parts — the old (wrong) format."""
        from validate_submission import validate_gauge_ids
        with pytest.raises(ValueError, match="3 part"):
            validate_gauge_ids(["aus_vic_230100"])

    def test_no_underscore_rejected(self):
        """A bare station ID with no prefix is not valid."""
        from validate_submission import validate_gauge_ids
        with pytest.raises(ValueError):
            validate_gauge_ids(["230200"])

    def test_duplicate_ids_rejected(self):
        from validate_submission import validate_gauge_ids
        with pytest.raises(ValueError, match="Duplicate"):
            validate_gauge_ids(["ausvic_230100", "ausvic_230200", "ausvic_230100"])

    def test_empty_string_in_list_rejected(self):
        from validate_submission import validate_gauge_ids
        with pytest.raises(ValueError):
            validate_gauge_ids(["ausvic_230100", ""])

    def test_empty_list_rejected(self):
        from validate_submission import validate_gauge_ids
        with pytest.raises(ValueError):
            validate_gauge_ids([])

    def test_trailing_underscore_rejected(self):
        """'ausvic_' has an empty station part after the underscore."""
        from validate_submission import validate_gauge_ids
        with pytest.raises(ValueError):
            validate_gauge_ids(["ausvic_"])

    def test_leading_underscore_rejected(self):
        """'_230200' has an empty prefix before the underscore."""
        from validate_submission import validate_gauge_ids
        with pytest.raises(ValueError):
            validate_gauge_ids(["_230200"])

    def test_all_10_config_gauges_are_valid(self):
        """Every gauge ID in gauges_config.py must pass validation."""
        from gauges_config import GAUGES
        from validate_submission import validate_gauge_ids
        ids = [g["gauge_id"] for g in GAUGES]
        validate_gauge_ids(ids)  # must not raise


class TestShapefileDbfColumns:
    """
    Caravan requires the combined shapefile DBF to contain ONLY 'gauge_id'.
    No extra columns allowed (reviewer requirement, Feb 2026).
    """

    def test_gauge_id_only_is_valid(self):
        from validate_submission import validate_shapefile_dbf_columns
        validate_shapefile_dbf_columns(["gauge_id"])  # must not raise

    def test_extra_column_rejected(self):
        from validate_submission import validate_shapefile_dbf_columns
        with pytest.raises(ValueError, match="extra"):
            validate_shapefile_dbf_columns(["gauge_id", "area_km2"])

    def test_missing_gauge_id_rejected(self):
        from validate_submission import validate_shapefile_dbf_columns
        with pytest.raises(ValueError, match="gauge_id"):
            validate_shapefile_dbf_columns(["name"])

    def test_empty_column_list_rejected(self):
        from validate_submission import validate_shapefile_dbf_columns
        with pytest.raises(ValueError):
            validate_shapefile_dbf_columns([])

    def test_up_area_column_rejected(self):
        """up_area_km2 is computed internally but must be stripped from output."""
        from validate_submission import validate_shapefile_dbf_columns
        with pytest.raises(ValueError):
            validate_shapefile_dbf_columns(["gauge_id", "up_area_km2"])

    def test_gauge_id_must_be_lowercase(self):
        """'GAUGE_ID' (uppercase) is wrong — Caravan uses lowercase 'gauge_id'."""
        from validate_submission import validate_shapefile_dbf_columns
        with pytest.raises(ValueError):
            validate_shapefile_dbf_columns(["GAUGE_ID"])


class TestGeoJsonFeatureProperties:
    """
    The output GeoJSON (ausvic_basin_shapes.geojson) must have exactly one
    property per feature: gauge_id. Internal fields (e.g. up_area_km2) must
    be stripped before writing.
    """

    def test_gauge_id_only_is_valid(self):
        from validate_submission import validate_geojson_feature_properties
        validate_geojson_feature_properties({"gauge_id": "ausvic_230200"})

    def test_extra_property_rejected(self):
        from validate_submission import validate_geojson_feature_properties
        with pytest.raises(ValueError, match="extra"):
            validate_geojson_feature_properties({
                "gauge_id": "ausvic_230200",
                "up_area_km2": 1305.4,
            })

    def test_missing_gauge_id_rejected(self):
        from validate_submission import validate_geojson_feature_properties
        with pytest.raises(ValueError, match="gauge_id"):
            validate_geojson_feature_properties({"name": "Keilor"})

    def test_empty_properties_rejected(self):
        from validate_submission import validate_geojson_feature_properties
        with pytest.raises(ValueError):
            validate_geojson_feature_properties({})

    def test_empty_gauge_id_value_rejected(self):
        from validate_submission import validate_geojson_feature_properties
        with pytest.raises(ValueError):
            validate_geojson_feature_properties({"gauge_id": ""})


class TestOutputFiles:
    """
    Verify that validate_output_files() correctly identifies missing files
    and returns an empty list when all required paths exist.
    """

    def test_all_present_returns_empty_list(self):
        """When every required path exists, no missing files are reported."""
        from validate_submission import validate_output_files, REQUIRED_OUTPUT_FILES
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for rel in REQUIRED_OUTPUT_FILES:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.touch()
            result = validate_output_files(root)
            assert result == [], f"Expected no missing files, got: {result}"

    def test_missing_file_detected(self):
        """A missing required file must appear in the returned list."""
        from validate_submission import validate_output_files
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_output_files(tmpdir)
            assert len(result) > 0

    def test_missing_license_detected(self):
        from validate_submission import validate_output_files, REQUIRED_OUTPUT_FILES
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create all files except the license
            for rel in REQUIRED_OUTPUT_FILES:
                if "license" in rel:
                    continue
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.touch()
            result = validate_output_files(root)
            assert any("license" in m for m in result), (
                "Missing license file must be reported"
            )

    def test_missing_shapefile_detected(self):
        from validate_submission import validate_output_files, REQUIRED_OUTPUT_FILES
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for rel in REQUIRED_OUTPUT_FILES:
                if "shapefiles" in rel:
                    continue
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.touch()
            result = validate_output_files(root)
            assert any("shapefiles" in m for m in result)
