"""
gauges_config.py

Single source of truth for all gauge stations being contributed to Caravan.
All fetch_*.py scripts import GAUGES from here.

To add a new gauge: append a dict to GAUGES following the same structure.

Catchment areas (area_km2=None):
  Melbourne Water API does not expose catchment area.
  Victorian Water Hydstra API also does not expose catchment area.
  Run fetch_hydroatlas.py — HydroATLAS UP_AREA will auto-fill these
  from the upstream drainage area at each gauge location.

Gauge network (11 gauges — revised Feb 2026):

  NOTE: gauge_id format is now ausvic_XXXXXX (not aus_vic_XXXXXX).
  Reviewer requested two-part IDs so gauge_id.split('_') returns exactly 2 parts.

  DEEP CREEK / UPPER CATCHMENT (Melbourne Water / melbwater API):
    230100A  Darraweit Guim    Deep Creek (upper tributary), 1996+
    230102A  Bulla             Deep Creek d/s Emu Creek at Bulla, 2004+  ← added Feb 2026
    230211A  Clarkefield       Bolinda Creek (upper tributary), 2008+
    230107A  Konagaderra       Konagaderra Creek tributary, 1996+
    230237A  Keilor North      mainstem d/s Jacksons Creek confluence, 2008+  ← added Feb 2026
    230200   Keilor            mid mainstem, 1907+ (Victorian Water/Hydstra)
    230106A  Chifley Drive     lower mainstem / tidal zone, 1996+

  TRIBUTARIES (Victorian Water / Hydstra API):
    Jacksons Creek system (joins Maribyrnong at Sunbury):
      230206  Gisborne          Jacksons Creek, 1960+
      230202  Sunbury           Jacksons Creek at Sunbury confluence, 1960+
    Mt Macedon / Campaspe headwaters:
      230213  Mt Macedon        Turritable Creek headwater, 1980+
      230227  Kerrie            Main Creek, 1990+

  EXCLUDED — already in Caravan via CAMELS AUS v2 (Kratzert review, Feb 2026):
    230210  Bullengarook      CAMELS AUS period 1968-05-10 to 2022-02-28 (our start 1970 — no new data)
    230205  Bulla             CAMELS AUS period 1955-06-22 to 2022-02-28 (our start 1960 — no new data)
    230209  Barringo          CAMELS AUS period 1966-06-17 to 2020-02-29 (our start 1970 — no new data)

  EXCLUDED — duplicate of 230202 (Feb 2026):
    230104A  Sunbury  Co-located with 230202 (Jackson Creek at Sunbury, Hydstra, 1960+).
             230104A is the Melbourne Water station ID for the same physical gauge.
             230202 kept as it has a 36-year longer record (1960 vs 1996).
             Oct 2022 post-event analysis names 230104A "Jacksons Creek at Sunbury
             Road, Sunbury" — confirming it is NOT on the Maribyrnong mainstem.
"""

from datetime import date

GAUGES = [
    {
        # ── Deep Creek @ Darraweit Guim (upper mainstem tributary) ─────────
        # Name source: Jacobs/Melbourne Water Oct 2022 post-event analysis.
        # Previously misnamed "Maribyrnong River at Darraweit" — Deep Creek
        # is a major tributary, not the mainstem.
        "station_id":   "230100A",
        "gauge_id":     "ausvic_230100",
        "name":         "Deep Creek at Darraweit Guim",
        "lat":          -37.4103,
        "lon":          144.9023,
        "area_km2":     682.7,  # from HydroATLAS UP_AREA
        "api":          "melbwater",
        "fetch_start":  date(1996, 1, 1),
        "notes":        "Deep Creek (upper Maribyrnong tributary); flow recorded from 1996.",
    },
    {
        # ── Deep Creek @ Bulla, downstream of Emu Creek ────────────────────
        # Identified from Jacobs/Melbourne Water Oct 2022 post-event analysis
        # as the key junction gauge capturing combined Deep Creek + Emu Creek
        # before they enter the Maribyrnong mainstem (865 km² total catchment).
        # CAMELS AUS v2 check Feb 2026: not present — safe to include.
        # MW API: flow data from 2004 (river level from 1996; pre-2004 flow
        # data may exist in DEWLP/Hydstra but is not accessible via MW API).
        "station_id":   "230102A",
        "gauge_id":     "ausvic_230102",
        "name":         "Deep Creek at Bulla",
        "lat":          -37.6314,
        "lon":          144.801,
        "area_km2":     876.4,  # from HydroATLAS UP_AREA (polygon intersection)
        "api":          "melbwater",
        "fetch_start":  date(2004, 1, 1),
        "notes":        "Deep Creek downstream of Emu Creek confluence at Bulla; flow from 2004.",
    },
    {
        # ── Bolinda Creek @ Clarkefield (upper tributary) ──────────────────
        # Name source: Jacobs/Melbourne Water Oct 2022 post-event analysis.
        # Previously misnamed "Maribyrnong River at Clarkefield" — the gauge
        # is on Bolinda Creek, not the mainstem.
        "station_id":   "230211A",
        "gauge_id":     "ausvic_230211",
        "name":         "Bolinda Creek at Clarkefield",
        "lat":          -37.4662,
        "lon":          144.7440,
        "area_km2":     177.9,  # from HydroATLAS UP_AREA
        "api":          "melbwater",
        "fetch_start":  date(2008, 1, 1),
        "notes":        "Bolinda Creek tributary of Maribyrnong at Clarkefield; flow from 2008.",
    },
    {
        # ── Konagaderra Creek @ Konagaderra (tributary) ────────────────────
        "station_id":   "230107A",
        "gauge_id":     "ausvic_230107",
        "name":         "Konagaderra Creek at Konagaderra",
        "lat":          -37.5285,
        "lon":          144.8560,
        "area_km2":     682.7,  # from HydroATLAS UP_AREA
        "api":          "melbwater",
        "fetch_start":  date(1996, 1, 1),
        "notes":        "Konagaderra Creek tributary of Maribyrnong; flow from 1996.",
    },
    {
        # ── Maribyrnong River @ Keilor North (d/s Jacksons Creek) ──────────
        # Station number confirmed from Maribyrnong Municipal Storm and Flood
        # Emergency Plan (Oct 2018): "Maribyrnong River d/s Jacksons Creek,
        # Keilor North — 230237A — Sydenham Park, Keilor North".
        # Captures combined mainstem + Jacksons Creek flows after confluence,
        # closing the monitoring gap between 230202 (Jackson Creek at Sunbury) and 230200 (Keilor).
        # CAMELS AUS v2 check Feb 2026: not present — safe to include.
        "station_id":   "230237A",
        "gauge_id":     "ausvic_230237",
        "name":         "Maribyrnong River at Keilor North",
        "lat":          -37.6778,
        "lon":          144.805,
        "area_km2":     1413.8, # HydroATLAS UP_AREA — Level-12 resolution snaps all three
        # lower mainstem gauges (Keilor North, Keilor, Chifley Drive) to the same
        # outlet basin (HYBAS_ID 5120612070). Use with caution: true catchment
        # is smaller than 1305.4 km² (Keilor official), but no finer estimate available.
        "api":          "melbwater",
        "fetch_start":  date(2008, 1, 1),
        "notes":        "Junction gauge downstream of Jacksons Creek confluence at Keilor North; flow from 2008. Area from HydroATLAS Level-12 (snaps to same outlet basin as Keilor/Chifley Drive; true catchment likely 900-1200 km²).",
    },
    {
        # ── Maribyrnong River @ Keilor (mid mainstem) ──────────────────────
        "station_id":   "230200",
        "gauge_id":     "ausvic_230200",           # Caravan identifier
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
        "gauge_id":     "ausvic_230106",           # Caravan identifier
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
        # ── Jackson Creek @ Gisborne (Jacksons Creek mid-upper) ────────────
        "station_id":   "230206",
        "gauge_id":     "ausvic_230206",
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
        "gauge_id":     "ausvic_230202",
        "name":         "Jackson Creek at Sunbury",
        "lat":          -37.583217370,
        "lon":          144.742035600,
        "area_km2":     406.7,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1960, 1, 1),
        "notes":        "Jacksons Creek near Maribyrnong confluence at Sunbury; discharge from 1960.",
    },
    {
        # ── Turritable Creek @ Mount Macedon (headwater) ────────────────────
        "station_id":   "230213",
        "gauge_id":     "ausvic_230213",
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
        "gauge_id":     "ausvic_230227",
        "name":         "Main Creek at Kerrie",
        "lat":          -37.396121060,
        "lon":          144.660394900,
        "area_km2":     177.9,  # from HydroATLAS UP_AREA
        "api":          "hydstra",
        "fetch_start":  date(1990, 1, 1),
        "notes":        "Main Creek tributary of Maribyrnong at Kerrie; discharge from 1990.",
    },
]
