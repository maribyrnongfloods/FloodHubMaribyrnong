"""
gauges_config.py

Single source of truth for all gauge stations being contributed to Caravan.
All fetch_*.py scripts import GAUGES from here.

To add a new gauge: append a dict to GAUGES following the same structure.
Fields marked TODO must be filled in before running the scripts.

Catchment areas (area_km2=None):
  Melbourne Water API does not expose catchment area.
  Victorian Water Hydstra API also does not expose catchment area.
  Run fetch_hydroatlas.py — HydroATLAS UP_AREA will auto-fill these
  from the upstream drainage area at each gauge location.

Gauge network (13 gauges):

  MAINSTEM (Melbourne Water / melbwater API):
    230100A  Darraweit         upper mainstem, 1996+
    230211A  Clarkefield       upper mainstem, 2008+
    230104A  Sunbury           mid-upper mainstem, 1996+
    230107A  Konagaderra       Konagaderra Creek tributary, 1996+
    230200   Keilor            mid mainstem, 1907+ (Victorian Water/Hydstra)
    230106A  Chifley Drive     lower mainstem / tidal zone, 1996+

  TRIBUTARIES (Victorian Water / Hydstra API):
    Jacksons Creek system (joins Maribyrnong at Sunbury):
      230210  Bullengarook      upper Jacksons Creek, 1970+
      230206  Gisborne          Jacksons Creek, 1960+
      230202  Sunbury           Jacksons Creek at Sunbury confluence, 1960+
    Deep Creek system:
      230205  Bulla             Deep Creek D/S of Emu Creek Junction, 1960+
    Mt Macedon / Campaspe headwaters:
      230209  Barringo          Barringo Creek U/S diversion, 1970+
      230213  Mt Macedon        Turritable Creek headwater, 1980+
      230227  Kerrie            Main Creek, 1990+
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
        "area_km2":     682.7,  # from HydroATLAS UP_AREA      # filled by fetch_hydroatlas.py
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
        "area_km2":     177.9,  # from HydroATLAS UP_AREA
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
        "area_km2":     406.7,  # from HydroATLAS UP_AREA
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
        "area_km2":     682.7,  # from HydroATLAS UP_AREA
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
        "area_km2":     1413.6,  # from HydroATLAS UP_AREA
        "api":          "melbwater",
        "fetch_start":  date(1996, 1, 1),
        "notes":        (
            "Tidal influence: flow only reliable above ~1 m water level "
            "(>16,520 ML/day). Lower readings are absent/unreliable."
        ),
    },

    # ── Victorian Water / Hydstra gauges (tributaries) ──────────────────────
    # Coordinates and names from Hydstra site_details; area_km2 filled by
    # fetch_hydroatlas.py.  fetch_start = first year with discharge data.

    {
        # ── Jacksons Creek @ Bullengarook (upper Jacksons Creek) ───────────
        "station_id":   "230210",
        "gauge_id":     "aus_vic_230210",
        "name":         "Jacksons Creek at Bullengarook",
        "lat":          -37.471848020,
        "lon":          144.524312400,
        "area_km2":     154.1,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1970, 1, 1),
        "notes":        "Upper Jacksons Creek (major Maribyrnong tributary); discharge from 1970.",
    },
    {
        # ── Jackson Creek @ Gisborne (Jacksons Creek mid-upper) ────────────
        "station_id":   "230206",
        "gauge_id":     "aus_vic_230206",
        "name":         "Jackson Creek at Gisborne",
        "lat":          -37.475370480,
        "lon":          144.572443200,
        "area_km2":     154.1,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1960, 1, 1),
        "notes":        "Jacksons Creek at Gisborne township; discharge from 1960.",
    },
    {
        # ── Jackson Creek @ Sunbury (Jacksons Creek at confluence) ─────────
        "station_id":   "230202",
        "gauge_id":     "aus_vic_230202",
        "name":         "Jackson Creek at Sunbury",
        "lat":          -37.583217370,
        "lon":          144.742035600,
        "area_km2":     406.7,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1960, 1, 1),
        "notes":        "Jacksons Creek near Maribyrnong confluence at Sunbury; discharge from 1960.",
    },
    {
        # ── Deep Creek @ Bulla D/S of Emu Creek Junction ───────────────────
        "station_id":   "230205",
        "gauge_id":     "aus_vic_230205",
        "name":         "Deep Creek at Bulla",
        "lat":          -37.631372000,
        "lon":          144.800973700,
        "area_km2":     876.1,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1960, 1, 1),
        "notes":        "Deep Creek tributary downstream of Emu Creek Junction; discharge from 1960.",
    },
    {
        # ── Barringo Creek @ Barringo U/S of Diversion ─────────────────────
        "station_id":   "230209",
        "gauge_id":     "aus_vic_230209",
        "name":         "Barringo Creek at Barringo",
        "lat":          -37.410503870,
        "lon":          144.626055100,
        "area_km2":     109.9,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1970, 1, 1),
        "notes":        "Barringo Creek upstream of diversion works; discharge from 1970.",
    },
    {
        # ── Turritable Creek @ Mount Macedon (headwater) ────────────────────
        "station_id":   "230213",
        "gauge_id":     "aus_vic_230213",
        "name":         "Turritable Creek at Mount Macedon",
        "lat":          -37.418904970,
        "lon":          144.584809600,
        "area_km2":     109.9,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1980, 1, 1),
        "notes":        "Turritable Creek headwater at Mount Macedon; discharge from 1980.",
    },
    {
        # ── Main Creek @ Kerrie ──────────────────────────────────────────────
        "station_id":   "230227",
        "gauge_id":     "aus_vic_230227",
        "name":         "Main Creek at Kerrie",
        "lat":          -37.396121060,
        "lon":          144.660394900,
        "area_km2":     177.9,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1990, 1, 1),
        "notes":        "Main Creek tributary of Maribyrnong at Kerrie; discharge from 1990.",
    },
]
