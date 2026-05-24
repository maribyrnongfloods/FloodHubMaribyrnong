# FloodHubMaribyrnong

Contributing 12 Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan), the open community dataset used by Google Flood Hub to train its AI flood forecasting model.

- **Zenodo DOI:** https://doi.org/10.5281/zenodo.18821361
- **Caravan submission:** https://github.com/kratzert/Caravan/issues/51
- **Extending Caravan guide:** https://github.com/kratzert/Caravan/wiki/Extending-Caravan-with-new-basins

## Gauge network

12 stations across the Maribyrnong catchment, Victoria, Australia (`ausvic_XXXXXX` format).

| Gauge ID | Name | Source | First flow | Last flow | Valid flow days |
|----------|------|--------|:---:|:---:|---:|
| ausvic_230119 | Maribyrnong River at Lancefield | Melbourne Water | 1996-09-25 | 2026-02-20 | 8,086 |
| ausvic_230100 | Deep Creek at Darraweit Guim | Melbourne Water | 1996-09-25 | 2026-02-20 | 8,086 |
| ausvic_230102 | Deep Creek at Bulla | Melbourne Water | 1996-09-25 | 2026-02-20 | 8,086 |
| ausvic_230211 | Bolinda Creek at Clarkefield | Melbourne Water | 2008-05-07 | 2026-02-20 | 6,493 |
| ausvic_230107 | Konagaderra Creek at Konagaderra | Melbourne Water | 1996-09-25 | 2026-02-20 | 8,070 |
| ausvic_230237 | Maribyrnong River at Keilor North | Melbourne Water | 2007-10-25 | 2026-02-20 | 6,603 |
| ausvic_230200 | Maribyrnong River at Keilor | Victorian Water | 1908-02-02 | 2026-02-20 | 36,483 |
| ausvic_230106 | Maribyrnong River at Chifley Drive | Melbourne Water | 1996-09-25 | 2026-02-20 | 8,070 * |
| ausvic_230206 | Jackson Creek at Gisborne | Victorian Water | 1960-05-10 | 2026-02-20 | 24,028 |
| ausvic_230202 | Jackson Creek at Sunbury | Victorian Water | 1960-01-01 | 2026-02-20 | 24,158 |
| ausvic_230213 | Turritable Creek at Mount Macedon | Victorian Water | 1975-03-01 | 2026-02-20 | 18,620 |
| ausvic_230227 | Main Creek at Kerrie | Victorian Water | 1989-12-05 | 2026-02-20 | 10,622 |

\* Tidal gauge. Of the 8,070 non-missing days, only 263 exceed the tidal threshold and represent physically valid streamflow (see Dataset notes).

## Notebooks

| Notebook | Purpose |
|----------|---------|
| `notebooks/1-derive_gauge_config_ausvic.ipynb` | Gauge network config and MERIT Hydro area lookup |
| `notebooks/2-fetch_catchments_ausvic.ipynb` | Catchment polygon derivation via HydroBASINS BFS |
| `notebooks/3-fetch_streamflow_ausvic.ipynb` | Daily streamflow from Melbourne Water and Victorian Water APIs |
| `notebooks/4-Caravan_part1_Earth_Engine.ipynb` | ERA5-Land forcing and HydroATLAS attributes via GEE (run in Colab) |
| `notebooks/5-Caravan_part2_local_postprocessing.ipynb` | ERA5 post-processing, PET, climate indices, Caravan output files |

## Notable flood events

### Official historical record — Lower Maribyrnong (mAHD at Maribyrnong/Chifley Drive)

Source: Table 1, SES Maribyrnong Flood Study post-event analysis (2018), p. 11.

| Rank | Year | Month | Peak height (mAHD) |
|------|------|-------|-------------------:|
| 1 | 1906 | Sept | 4.50 |
| 2 | 1916 | Sept | 4.26 |
| 3 | 2022 | Oct  | 4.22 |
| 4 | 1974 | May  | 4.20 |
| 5 | 1871 | Sept | 3.86 |
| 6 | 1891 | July | 3.32 |
| 7 | 1993 | Sept | 3.31 |
| 8 | 1954 | Dec  | 2.98 |
| 9 | 1924 | Aug  | 2.98 |
| 10 | 1983 | Oct | 2.85 |
| 11 | 1954 | Nov | 2.83 |

Events before 1908 (1906, 1871, 1891, 1924) predate the Keilor gauge record and cannot be
validated against the streamflow data in this dataset.

### Streamflow-derived flood dates

Top 10 flood events ranked by peak daily flow at **Maribyrnong River at Keilor (230200)**,
the mainstem gauge closest to the SES measurement point with the longest record (1908–present).
Events are de-duplicated with a 30-day separation window (peak day shown per event).
Cross-checked against the SES Maribyrnong Flood Study historic stage table.

| Rank | Date | Keilor flow (mm/d) | SES reference |
|------|----|---:|---|
| 1 | 2022-10-14 | 33.27 | SES rank 3 (4.22 mAHD at Chifley Drive) |
| 2 | 1916-09-24 | 30.40 | SES rank 2 (4.26 mAHD) |
| 3 | 1974-05-16 | 25.26 | SES rank 4 (4.20 mAHD) |
| 4 | 1983-10-16 | 24.96 | SES rank 10 (2.85 mAHD) |
| 5 | 1993-09-16 | 24.18 | SES rank 7 (3.31 mAHD) |
| 6 | 1971-11-08 | 23.49 | — |
| 7 | 1987-07-30 | 23.17 | — |
| 8 | 1909-08-20 | 20.66 | — |
| 9 | 1911-06-22 | 20.25 | — |
| 10 | 1924-08-26 | 19.36 | SES rank 9 (2.98 mAHD) |

6 of the 10 events correspond to SES-documented floods. SES ranks 1 (1906), 5 (1871), and
6 (1891) predate the Keilor gauge record and cannot be validated. SES rank 8 (1954) falls
just outside the top 10 by Keilor flow.

The Keilor-based ranking aligns closely with the SES stage table because both measure the
same point on the lower mainstem. The 2022 event ranks first by flow volume (33.27 mm/d)
even though it ranks third by stage height — likely due to floodplain storage changes and
rating curve updates over a century of record.

## Dataset notes for reviewers

### Catchment areas for co-located mainstem gauges

Three gauges sit within a few kilometres of each other on the lower mainstem:

| Gauge | Area (km²) | Method |
|-------|---:|--------|
| 230237A Keilor North | 1278.1 | MERIT Hydro 90m DEM |
| 230200 Keilor | 1305.4 | Official Victorian Water figure |
| 230106A Chifley Drive | 1385.0 | MERIT Hydro 90m DEM |

HydroBASINS Level-12 is too coarse to resolve these gauges — all three snap to the
same Level-12 cell (UP_AREA = 1413.6 km²). Keilor uses the agency-published figure.
Keilor North and Chifley Drive use MERIT Hydro 90m upstream delineations, which
produce physically plausible areas consistent with their positions on the reach.
The HydroATLAS `UP_AREA` value in `attributes_hydroatlas_ausvic.csv` is therefore
overridden by the MERIT Hydro figure in `attributes_other_ausvic.csv` for these two gauges.

### Data availability by agency

The 5 main Melbourne Water gauges (`230119A`, `230100A`, `230102A`, `230107A`, `230106A`)
have records from 1996-09-25 onwards. Two newer sites (`230211A` from 2008-05-07,
`230237A` from 2007-10-25) were installed later. Before 1996, only the 5 Victorian Water
gauges are present (Keilor 230200 from 1908, Jackson Creek gauges from 1960,
Turritable Creek from 1975, Main Creek from 1989).

The apparent 12-gauge network is therefore a **5-gauge network before 1996** and a
**12-gauge network from 2008**.

### Tidal gauge — Chifley Drive (230106A)

This gauge sits at the tidal limit of the Maribyrnong River. Flow readings are only
physically meaningful above approximately 1 m water level (roughly 16,520 ML/day at
that section); below that threshold, tidal effects dominate. Only 263 days in the full
record exceed this threshold. The timeseries is included for completeness — the gauge
captures the largest flood peaks — but should be treated as sparse mainstem data rather
than a conventional streamflow record.

### Sensor ceiling — Bolinda Creek at Clarkefield (230211A)

The Melbourne Water pressure transducer at this site has a hardware ceiling equivalent
to approximately 500 m³/s. During the December 2008 flood the sensor flatlined at this
ceiling for three consecutive days (14–16 December 2008). Those readings were masked as
missing rather than retained as underestimates.

### Pre-ERA5 rows — Keilor (230200)

Keilor's streamflow record begins in 1908, predating the ERA5-Land dataset (which starts
1950-01-02). Rows from 1908 to 1949-12-31 have empty ERA5-Land columns, per the Caravan
standard for pre-reanalysis data.

## License

CC-BY-4.0. Streamflow data: Melbourne Water (CC-BY-4.0), Victorian Water Monitoring Information System (CC-BY-4.0). Meteorological forcing: ERA5-Land (Copernicus C3S). Catchment attributes: HydroATLAS (CC-BY-4.0).
