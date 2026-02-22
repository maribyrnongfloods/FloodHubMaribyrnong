"""
gauges_config.py

Single source of truth for all gauge stations being contributed to Caravan.
All fetch_*.py scripts import GAUGES from here.

To add a new gauge: append a dict to GAUGES following the same structure.
Fields marked TODO must be filled in before running the scripts.

Catchment area for 230106A (still needed):
  The Melbourne Water API does not expose catchment area. Options:
  1. Ask Melbourne Water directly — they provided the API access so may share it
  2. Run fetch_hydroatlas.py first — HydroATLAS UP_AREA attribute will give a
     close approximation (upstream drainage area in km²) for the Chifley Drive
     gauge location at (-37.7659, 144.8950)
  3. Check the Victorian Water Monitoring site (data.water.vic.gov.au) under
     station 230106 — some Hydstra stations share the same numeric ID
"""

from datetime import date

GAUGES = [
    {
        # ── Maribyrnong River @ Keilor ─────────────────────────────────────
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
        # ── Maribyrnong River @ Chifley Drive ──────────────────────────────
        "station_id":   "230106A",
        "gauge_id":     "aus_vic_230106",          # Caravan identifier
        "name":         "Maribyrnong River at Chifley Drive",
        "lat":          -37.76590000,              # from api.melbournewater.com.au/rainfall-river-level/locations
        "lon":          144.89500000,              # from api.melbournewater.com.au/rainfall-river-level/locations
        "area_km2":     None,     # TODO — catchment area not in Melbourne Water API; see note below
        "api":          "melbwater",               # api.melbournewater.com.au
        "fetch_start":  date(1996, 1, 1),          # minYear=1996 from /230106A/summary
        "notes":        (
            "Tidal influence: flow only reliable above ~1 m water level "
            "(>16,520 ML/day). Lower readings are absent/unreliable."
        ),
    },
]
