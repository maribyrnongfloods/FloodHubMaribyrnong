# FloodHubMaribyrnong

Contributing 12 Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan), the open community dataset used by Google Flood Hub to train its AI flood forecasting model.

- **Zenodo DOI:** https://doi.org/10.5281/zenodo.18736844
- **Caravan submission:** https://github.com/kratzert/Caravan/issues/51
- **Extending Caravan guide:** https://github.com/kratzert/Caravan/wiki/Extending-Caravan-with-new-basins

## Gauge network

12 stations across the Maribyrnong catchment, Victoria, Australia (`ausvic_XXXXXX` format).

| Station | Name | Source |
|---------|------|--------|
| 230119A | Maribyrnong River at Lancefield | Melbourne Water |
| 230100A | Deep Creek at Darraweit Guim | Melbourne Water |
| 230102A | Deep Creek at Bulla | Melbourne Water |
| 230211A | Bolinda Creek at Clarkefield | Melbourne Water |
| 230107A | Konagaderra Creek at Konagaderra | Melbourne Water |
| 230237A | Maribyrnong River at Keilor North | Melbourne Water |
| 230200  | Maribyrnong River at Keilor | Victorian Water |
| 230106A | Maribyrnong River at Chifley Drive | Melbourne Water |
| 230206  | Jackson Creek at Gisborne | Victorian Water |
| 230202  | Jackson Creek at Sunbury | Victorian Water |
| 230213  | Turritable Creek at Mount Macedon | Victorian Water |
| 230227  | Main Creek at Kerrie | Victorian Water |

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

Top 10 flood dates identified from the streamflow record, ranked by the fraction of the
gauge network simultaneously reporting high flows (≥ 3 gauges required).
Cross-checked against the SES Maribyrnong Flood Study historic stage table.

| Rank | Date | Gauges active | Peak gauge | Peak flow (mm/d) | SES reference |
|------|------|:---:|---|---:|---|
| 1 | 1993-09-15 | 5 | Jackson Ck at Gisborne (230206) | 65.50 | SES table: 3.83 m at Maribyrnong/Chifley |
| 2 | 1983-10-16 | 4 | Jackson Ck at Gisborne (230206) | 51.67 | — |
| 3 | 1971-11-08 | 3 | Jackson Ck at Gisborne (230206) | 30.84 | — |
| 4 | 2022-10-14 | **12** | Maribyrnong at Keilor (230200) | 33.27 | SES/report: 4.22 m at Chifley (14 Oct 2022) |
| 5 | 1990-07-18 | 5 | Jackson Ck at Gisborne (230206) | 24.71 | — |
| 6 | 1963-07-14 | 3 | Jackson Ck at Sunbury (230202) | 13.85 | — |
| 7 | 1978-08-08 | 4 | Maribyrnong at Keilor (230200) | 18.59 | — |
| 8 | 1985-12-10 | 4 | Jackson Ck at Sunbury (230202) | 17.91 | — |
| 9 | 1990-10-12 | 5 | Jackson Ck at Gisborne (230206) | 23.61 | — |
| 10 | 1960-09-18 | 3 | Jackson Ck at Sunbury (230202) | 14.23 | — |

**2022-10-14** is the only event in the full record where all 12 gauges simultaneously reported
elevated flows, making it the most comprehensively documented flood in the dataset.
Pre-Melbourne Water era events (before ~2003) are only captured by the Victorian Water gauges
(Keilor 230200, Jackson Creek 230202/230206, tributaries 230213/230227).

## License

CC-BY-4.0. Streamflow data: Melbourne Water (CC-BY-4.0), Victorian Water Monitoring Information System (CC-BY-4.0). Meteorological forcing: ERA5-Land (Copernicus C3S). Catchment attributes: HydroATLAS (CC-BY-4.0).
