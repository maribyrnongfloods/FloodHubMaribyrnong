# Caravan extension: `ausvic` — Maribyrnong River basin, Victoria, Australia

## License

This sub-dataset is released under the **Creative Commons Attribution 4.0 International (CC-BY-4.0)** license, consistent with the Caravan dataset: <https://creativecommons.org/licenses/by/4.0/>

**Cite this extension as:**

> Lanzafame, L. (2026). *Caravan-AUS-VIC: Maribyrnong River basin (10 gauges).* Zenodo. https://doi.org/10.5281/zenodo.18736843 (all versions; this DOI always resolves to the latest release — the version-specific DOI is shown on the Zenodo record page)

## Data sources and attributions

### Streamflow

- **Bureau of Meteorology, Water Data Online** — <http://www.bom.gov.au/waterdata/>
  Gauges 230100A, 230102A, 230106A, 230107A, 230119A, 230211A, 230237A (Melbourne Water Corporation data). Quality-controlled "Water Course Discharge" (series `DMQaQc.Merged.AsStored`), sub-daily aggregated to a time-weighted daily mean. CC-BY-4.0.
- **Victorian Government Water Measurement Information System** — <https://data.water.vic.gov.au/>
  Gauges 230200 (Maribyrnong @ Keilor), 230202 (Jacksons Ck @ Sunbury), 230206 (Jacksons Ck @ Gisborne). Daily mean discharge (variable 141.00). CC-BY-4.0 (State of Victoria).

### Catchment polygons

- **Melbourne Water Stream Network (MWSTR) v1.3.1** (Walsh & Kunapo 2023) — Waterway Ecosystem Research Group, School of Geography, Earth and Atmospheric Sciences, University of Melbourne. <https://tools.thewerg.unimelb.edu.au/mwstr/> — CC-BY-4.0.
  Polygons were derived by tracing the upstream sub-catchments of each gauge through the MWSTR `subcs.nextds` connectivity graph, unioning them per gauge, then simplifying to a ~110 m tolerance for Earth Engine compute tractability (maximum area drift 0.23%). Each gauge has a distinct polygon; nested gauges (e.g. Konagaderra ⊂ Bulla ⊂ Keilor North ⊂ Chifley Drive) are properly contained, not duplicated.

### Static catchment attributes

- **HydroATLAS / BasinATLAS** (Linke et al. 2019, *Scientific Data* 6:283) — <https://www.hydrosheds.org/page/hydroatlas> — CC-BY-4.0. Extracted via the official Caravan Part-1 (Google Earth Engine) pipeline.

### Meteorological forcings

- **ECMWF ERA5-Land** (Muñoz-Sabater 2019, doi:10.24381/cds.e2161bac) — Copernicus Climate Change Service (C3S) Climate Data Store. Licensed under the Copernicus Licence (CC-BY-4.0 compatible). Aggregated from hourly (UTC) to daily in local time at the gauge coordinates via the official Caravan Part-2 pipeline.

## Catchment-area cross-validation

The MWSTR-derived catchment areas were independently cross-checked against two agency studies and agree to within ~1.5% on every primary gauge:

- Melbourne and Metropolitan Board of Works (March 1986). *Maribyrnong River Flood Mitigation Study*, Report MMBW-D-0040. Catchment areas at Keilor (1,312 km²), Bulla (874 km²), Sunbury (338 km²).
- Jacobs Group Pty Ltd (March 2023). *Maribyrnong River Flood Event October 2022 — Post Event Analysis.* Commissioned by Melbourne Water.

## References

- Kratzert, F., Nearing, G., Addor, N., et al. (2023). Caravan – A global community dataset for large-sample hydrology. *Scientific Data*, 10, 61. doi:10.1038/s41597-023-01975-w
- Linke, S., Lehner, B., Ouellet Dallaire, C., et al. (2019). Global hydro-environmental sub-basin and river reach characteristics at high spatial resolution. *Scientific Data*, 6, 283. doi:10.1038/s41597-019-0300-6
- Muñoz-Sabater, J. (2019). ERA5-Land hourly data from 1950 to present. Copernicus C3S Climate Data Store. doi:10.24381/cds.e2161bac
- Walsh, C. J. & Kunapo, J. (2023). *Melbourne Water Stream Network (MWSTR) v1.3.1.* University of Melbourne.
