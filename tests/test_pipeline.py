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
        # 41 cols: date + streamflow + 39 ERA5-Land
        cols = self._run_merge()
        assert len(cols) == 41, f"Expected 41 columns, got {len(cols)}"

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
