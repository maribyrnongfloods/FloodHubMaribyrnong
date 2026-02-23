"""
fetch_silo_met.py — REMOVED

SILO DataDrill is an Australian-only dataset. Caravan requires all
meteorological forcing data to be globally available so that every
subdataset uses the same source and large-scale intercomparisons are valid.

Per Caravan reviewer feedback (Kratzert, Feb 2026, GitHub issue #51):
  "Please note that the entire idea of Caravan is to include data that is
   available globally. From my understanding, SILO is an Australian dataset,
   hence all data from SILO should be removed from Caravan."

Replacement:
  - ERA5-Land (ECMWF/ERA5_LAND/DAILY_AGGR) via fetch_era5land.py covers
    all meteorological forcing globally from 1950-01-01 onwards.
  - Climate attribute statistics (p_mean, pet_mean, aridity, etc.) must now
    be computed using the official Caravan Part-2 Colab notebook:
    https://github.com/kratzert/Caravan/blob/main/code/

This file is kept as a placeholder so the import error is informative
rather than a generic ModuleNotFoundError.
"""

raise ImportError(
    "fetch_silo_met has been removed. SILO is not globally available and "
    "must not be included in Caravan. Use fetch_era5land.py instead. "
    "See the docstring in this file for details."
)
