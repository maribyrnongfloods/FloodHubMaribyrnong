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
| `notebooks/0a-derive_gauge_config_ausvic.ipynb` | Gauge network config and MERIT Hydro area lookup (run in Colab) |
| `notebooks/0b-fetch_catchments_ausvic.ipynb` | Catchment polygon derivation via HydroBASINS BFS (run in Colab) |
| `notebooks/1-Caravan_part1_Earth_Engine_Lee.ipynb` | ERA5-Land forcing and HydroATLAS attributes via GEE (run in Colab) |

## License

CC-BY-4.0. Streamflow data: Melbourne Water (CC-BY-4.0), Victorian Water Monitoring Information System (CC-BY-4.0). Meteorological forcing: ERA5-Land (Copernicus C3S). Catchment attributes: HydroATLAS (CC-BY-4.0).
