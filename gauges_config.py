"""
gauges_config.py

Single source of truth for all gauge stations being contributed to Caravan.
All fetch_*.py scripts import GAUGES from here.

To add a new gauge: append a dict to GAUGES following the same structure.
Fields marked TODO must be filled in before running the scripts.

Catchment areas for Melbourne Water gauges (all area_km2=None):
  The Melbourne Water API does not expose catchment area.
  Run fetch_hydroatlas.py — HydroATLAS UP_AREA will auto-fill these
  from the upstream drainage area at each gauge location.

Gauge network (6 gauges, ordered upstream to downstream):
  230100A  Darraweit         upper mainstem, 1996+
  230211A  Clarkefield       upper mainstem, 2008+
  230104A  Sunbury           mid-upper mainstem, 1996+
  230107A  Konagaderra       Konagaderra Creek tributary, 1996+
  230200   Keilor            mid mainstem, 1907+ (Victorian Water/Hydstra)
  230106A  Chifley Drive     lower mainstem / tidal zone, 1996+
"""

from datetime import date

GAUGES = [
    {
        # ── Maribyrnong River @ Darraweit (upper mainstem) ─────────────────
        "station_id":   "230100A",
        "gauge_id":     "aus_vic_230100",
        "name":         "Maribyrnong River at Darraweit",
        "lat":          -37.4103,
        "lon":          144.9023,
        "area_km2":     None,      # filled by fetch_hydroatlas.py
        "api":          "melbwater",
        "fetch_start":  date(1996, 1, 1),
        "notes":        "Upper Maribyrnong mainstem; flow recorded from 1996.",
    },
    {
        # ── Maribyrnong River @ Clarkefield (upper mainstem) ───────────────
        "station_id":   "230211A",
        "gauge_id":     "aus_vic_230211",
        "name":         "Maribyrnong River at Clarkefield",
        "lat":          -37.4662,
        "lon":          144.7440,
        "area_km2":     None,
        "api":          "melbwater",
        "fetch_start":  date(2008, 1, 1),
        "notes":        "Upper Maribyrnong mainstem; flow recorded from 2008.",
    },
    {
        # ── Maribyrnong River @ Sunbury (mid-upper mainstem) ───────────────
        "station_id":   "230104A",
        "gauge_id":     "aus_vic_230104",
        "name":         "Maribyrnong River at Sunbury",
        "lat":          -37.5833,
        "lon":          144.7420,
        "area_km2":     None,
        "api":          "melbwater",
        "fetch_start":  date(1996, 1, 1),
        "notes":        "Mid-upper Maribyrnong mainstem; flow recorded from 1996.",
    },
    {
        # ── Konagaderra Creek @ Konagaderra (tributary) ────────────────────
        "station_id":   "230107A",
        "gauge_id":     "aus_vic_230107",
        "name":         "Konagaderra Creek at Konagaderra",
        "lat":          -37.5285,
        "lon":          144.8560,
        "area_km2":     None,
        "api":          "melbwater",
        "fetch_start":  date(1996, 1, 1),
        "notes":        "Konagaderra Creek tributary of Maribyrnong; flow from 1996.",
    },
    {
        # ── Maribyrnong River @ Keilor (mid mainstem) ──────────────────────
        "station_id":   "230200",
        "gauge_id":     "aus_vic_230200",          # Caravan identifier
        "name":         "Maribyrnong River at Keilor",
        "lat":          -37.727706090,
        "lon":          144.836476100,
        "area_km2":     1305.4,
        "api":          "hydstra",                 # data.water.vic.gov.au
        "fetch_start":  date(1907, 5, 20),         # monitoring began
        "notes":        "Artificial crump weir; 586 gaugings 1908-2025",
    },
    {
        # ── Maribyrnong River @ Chifley Drive (lower mainstem / tidal) ─────
        "station_id":   "230106A",
        "gauge_id":     "aus_vic_230106",          # Caravan identifier
        "name":         "Maribyrnong River at Chifley Drive",
        "lat":          -37.76590000,
        "lon":          144.89500000,
        "area_km2":     None,
        "api":          "melbwater",
        "fetch_start":  date(1996, 1, 1),
        "notes":        (
            "Tidal influence: flow only reliable above ~1 m water level "
            "(>16,520 ML/day). Lower readings are absent/unreliable."
        ),
    },
]
