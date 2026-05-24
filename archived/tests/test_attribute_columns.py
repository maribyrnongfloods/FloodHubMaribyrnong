"""
Test: attribute CSV column names and order.

Checks all three attribute files produced by notebook 5:
  - attributes_other_ausvic.csv      (14 cols)
  - attributes_caravan_ausvic.csv    (15 cols, alpha-sorted by official notebook)
  - attributes_hydroatlas_ausvic.csv (196 cols, alpha-sorted, no upstream/ignore leakage)

Tests skip gracefully if caravan_maribyrnong/ output doesn't exist.
Run: pytest tests/test_attribute_columns.py -v
"""

import csv
import pytest
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ATTR_DIR = (
    Path(__file__).parent.parent
    / "caravan_maribyrnong" / "attributes" / "ausvic"
)

OTHER_CSV    = ATTR_DIR / "attributes_other_ausvic.csv"
CARAVAN_CSV  = ATTR_DIR / "attributes_caravan_ausvic.csv"
HYDROATLAS_CSV = ATTR_DIR / "attributes_hydroatlas_ausvic.csv"


def _header(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


# ---------------------------------------------------------------------------
# Ground-truth column specs
# ---------------------------------------------------------------------------

# attributes_other — 14 columns, fixed order (Caravan standard)
EXPECTED_OTHER = [
    "gauge_id", "gauge_name", "gauge_lat", "gauge_lon", "country",
    "basin_name", "area", "unit_area", "streamflow_period",
    "streamflow_missing", "streamflow_units", "source", "license", "note",
]

# attributes_caravan — 15 columns, alpha-sorted (notebook 5 sort_index call)
# Order comes from calculate_climate_indices() dict, then sort_index(axis='columns')
EXPECTED_CARAVAN = [
    "gauge_id",
    "aridity_ERA5_LAND", "aridity_FAO_PM", "frac_snow",
    "high_prec_dur", "high_prec_freq",
    "low_prec_dur", "low_prec_freq",
    "moisture_index_ERA5_LAND", "moisture_index_FAO_PM",
    "p_mean", "pet_mean_ERA5_LAND", "pet_mean_FAO_PM",
    "seasonality_ERA5_LAND", "seasonality_FAO_PM",
]

# attributes_hydroatlas — 196 columns (gauge_id + 195 BasinATLAS attrs, alpha-sorted)
# Generated from the GEE output with area + area_fraction_used_for_aggregation dropped.
EXPECTED_HYDROATLAS = [
    "gauge_id",
    "aet_mm_s01", "aet_mm_s02", "aet_mm_s03", "aet_mm_s04", "aet_mm_s05",
    "aet_mm_s06", "aet_mm_s07", "aet_mm_s08", "aet_mm_s09", "aet_mm_s10",
    "aet_mm_s11", "aet_mm_s12", "aet_mm_syr",
    "ari_ix_sav",
    "cls_cl_smj", "cly_pc_sav", "clz_cl_smj",
    "cmi_ix_s01", "cmi_ix_s02", "cmi_ix_s03", "cmi_ix_s04", "cmi_ix_s05",
    "cmi_ix_s06", "cmi_ix_s07", "cmi_ix_s08", "cmi_ix_s09", "cmi_ix_s10",
    "cmi_ix_s11", "cmi_ix_s12", "cmi_ix_syr",
    "crp_pc_sse",
    "dis_m3_pmn", "dis_m3_pmx", "dis_m3_pyr", "dor_pc_pva",
    "ele_mt_sav", "ele_mt_smn", "ele_mt_smx", "ero_kh_sav",
    "fec_cl_smj", "fmh_cl_smj", "for_pc_sse",
    "gdp_ud_sav", "gdp_ud_ssu", "gla_pc_sse", "glc_cl_smj",
    "glc_pc_s01", "glc_pc_s02", "glc_pc_s03", "glc_pc_s04", "glc_pc_s05",
    "glc_pc_s06", "glc_pc_s07", "glc_pc_s08", "glc_pc_s09", "glc_pc_s10",
    "glc_pc_s11", "glc_pc_s12", "glc_pc_s13", "glc_pc_s14", "glc_pc_s15",
    "glc_pc_s16", "glc_pc_s17", "glc_pc_s18", "glc_pc_s19", "glc_pc_s20",
    "glc_pc_s21", "glc_pc_s22",
    "gwt_cm_sav", "hdi_ix_sav",
    "hft_ix_s09", "hft_ix_s93",
    "inu_pc_slt", "inu_pc_smn", "inu_pc_smx", "ire_pc_sse",
    "kar_pc_sse", "lit_cl_smj", "lka_pc_sse", "lkv_mc_usu",
    "nli_ix_sav", "pac_pc_sse",
    "pet_mm_s01", "pet_mm_s02", "pet_mm_s03", "pet_mm_s04", "pet_mm_s05",
    "pet_mm_s06", "pet_mm_s07", "pet_mm_s08", "pet_mm_s09", "pet_mm_s10",
    "pet_mm_s11", "pet_mm_s12", "pet_mm_syr",
    "pnv_cl_smj",
    "pnv_pc_s01", "pnv_pc_s02", "pnv_pc_s03", "pnv_pc_s04", "pnv_pc_s05",
    "pnv_pc_s06", "pnv_pc_s07", "pnv_pc_s08", "pnv_pc_s09", "pnv_pc_s10",
    "pnv_pc_s11", "pnv_pc_s12", "pnv_pc_s13", "pnv_pc_s14", "pnv_pc_s15",
    "pop_ct_usu", "ppd_pk_sav",
    "pre_mm_s01", "pre_mm_s02", "pre_mm_s03", "pre_mm_s04", "pre_mm_s05",
    "pre_mm_s06", "pre_mm_s07", "pre_mm_s08", "pre_mm_s09", "pre_mm_s10",
    "pre_mm_s11", "pre_mm_s12", "pre_mm_syr",
    "prm_pc_sse", "pst_pc_sse",
    "rdd_mk_sav", "rev_mc_usu", "ria_ha_usu", "riv_tc_usu", "run_mm_syr",
    "sgr_dk_sav", "slp_dg_sav", "slt_pc_sav", "snd_pc_sav",
    "snw_pc_s01", "snw_pc_s02", "snw_pc_s03", "snw_pc_s04", "snw_pc_s05",
    "snw_pc_s06", "snw_pc_s07", "snw_pc_s08", "snw_pc_s09", "snw_pc_s10",
    "snw_pc_s11", "snw_pc_s12", "snw_pc_smx", "snw_pc_syr",
    "soc_th_sav",
    "swc_pc_s01", "swc_pc_s02", "swc_pc_s03", "swc_pc_s04", "swc_pc_s05",
    "swc_pc_s06", "swc_pc_s07", "swc_pc_s08", "swc_pc_s09", "swc_pc_s10",
    "swc_pc_s11", "swc_pc_s12", "swc_pc_syr",
    "tbi_cl_smj", "tec_cl_smj",
    "tmp_dc_s01", "tmp_dc_s02", "tmp_dc_s03", "tmp_dc_s04", "tmp_dc_s05",
    "tmp_dc_s06", "tmp_dc_s07", "tmp_dc_s08", "tmp_dc_s09", "tmp_dc_s10",
    "tmp_dc_s11", "tmp_dc_s12", "tmp_dc_smn", "tmp_dc_smx", "tmp_dc_syr",
    "urb_pc_sse", "wet_cl_smj",
    "wet_pc_s01", "wet_pc_s02", "wet_pc_s03", "wet_pc_s04", "wet_pc_s05",
    "wet_pc_s06", "wet_pc_s07", "wet_pc_s08", "wet_pc_s09",
    "wet_pc_sg1", "wet_pc_sg2",
]

# Columns that must NEVER appear (upstream aggregates, HydroSHEDS internals, artifacts)
BANNED_HYDROATLAS = {
    "area", "area_fraction_used_for_aggregation",
    "HYBAS_ID", "NEXT_DOWN", "SUB_AREA", "UP_AREA",
    "system:index", "COAST", "DIST_MAIN", "DIST_SINK", "ENDO",
    "MAIN_BAS", "NEXT_SINK", "ORDER_", "PFAF_ID", "SORT",
}

# Quick sanity on the spec itself
assert len(EXPECTED_OTHER)      == 14,  f"spec error: {len(EXPECTED_OTHER)}"
assert len(EXPECTED_CARAVAN)    == 15,  f"spec error: {len(EXPECTED_CARAVAN)}"
assert len(EXPECTED_HYDROATLAS) == 196, f"spec error: {len(EXPECTED_HYDROATLAS)}"


# ---------------------------------------------------------------------------
# Skip helper
# ---------------------------------------------------------------------------

def _require(path: Path):
    if not path.exists():
        pytest.skip(f"Output file not found: {path}")


# ---------------------------------------------------------------------------
# attributes_other tests
# ---------------------------------------------------------------------------

class TestAttributesOther:
    def test_file_exists(self):
        _require(OTHER_CSV)

    def test_column_count(self):
        _require(OTHER_CSV)
        assert len(_header(OTHER_CSV)) == 14

    def test_column_names_and_order(self):
        _require(OTHER_CSV)
        assert _header(OTHER_CSV) == EXPECTED_OTHER, (
            f"attributes_other columns differ.\n"
            f"  Got:      {_header(OTHER_CSV)}\n"
            f"  Expected: {EXPECTED_OTHER}"
        )


# ---------------------------------------------------------------------------
# attributes_caravan tests
# ---------------------------------------------------------------------------

class TestAttributesCaravan:
    def test_file_exists(self):
        _require(CARAVAN_CSV)

    def test_column_count(self):
        _require(CARAVAN_CSV)
        assert len(_header(CARAVAN_CSV)) == 15

    def test_column_names_and_order(self):
        _require(CARAVAN_CSV)
        assert _header(CARAVAN_CSV) == EXPECTED_CARAVAN, (
            f"attributes_caravan columns differ.\n"
            f"  Got:      {_header(CARAVAN_CSV)}\n"
            f"  Expected: {EXPECTED_CARAVAN}"
        )


# ---------------------------------------------------------------------------
# attributes_hydroatlas tests
# ---------------------------------------------------------------------------

class TestAttributesHydroatlas:
    def test_file_exists(self):
        _require(HYDROATLAS_CSV)

    def test_column_count(self):
        _require(HYDROATLAS_CSV)
        assert len(_header(HYDROATLAS_CSV)) == 196

    def test_column_names_and_order(self):
        _require(HYDROATLAS_CSV)
        assert _header(HYDROATLAS_CSV) == EXPECTED_HYDROATLAS, (
            f"attributes_hydroatlas columns differ.\n"
            f"  Got:      {_header(HYDROATLAS_CSV)}\n"
            f"  Expected: {EXPECTED_HYDROATLAS}"
        )

    def test_no_banned_columns(self):
        """Upstream aggregates and HydroSHEDS internals must not appear."""
        _require(HYDROATLAS_CSV)
        cols = set(_header(HYDROATLAS_CSV))
        leaked = cols & BANNED_HYDROATLAS
        assert not leaked, f"Banned columns present: {leaked}"

    def test_gauge_id_is_first(self):
        _require(HYDROATLAS_CSV)
        assert _header(HYDROATLAS_CSV)[0] == "gauge_id"
