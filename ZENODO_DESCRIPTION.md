Caravan-AUS-VIC: Maribyrnong River basin (10 gauges)

This dataset is a community extension to Caravan (Kratzert et al., 2023), the global large-sample hydrology dataset used by Google Flood Hub. It adds 10 streamflow gauges in the Maribyrnong River catchment of north-west Melbourne, Victoria, Australia — a basin with a long and significant flood history, including the major floods of October 2022 (the largest on record) and May 1974. Every gauge is supplied in the standard Caravan format and merges directly into the dataset under the basin prefix "ausvic".

SPATIAL AND TEMPORAL COVERAGE

The dataset covers the Maribyrnong River and its main tributaries — Deep Creek, Jacksons Creek and Bolinda Creek — spanning the catchment from the upper headwaters near Lancefield, through Bulla and Keilor, down to Chifley Drive at the edge of central Melbourne. Catchment areas range from 91 to 1,386 km². Daily time series run from 1950-01-02 to 2026-03-07, bounded by ERA5-Land availability; individual gauge streamflow records begin between 1950 (Keilor, the longest record) and 2000 (Lancefield).

CONTENTS (PER GAUGE)

- Daily streamflow in mm/day, area-normalised using the catchment-polygon areas.
- Daily ERA5-Land meteorological forcings: 14 variables (2 m air and dewpoint temperature, total precipitation, surface net solar and thermal radiation, 10 m wind components, surface pressure, four soil-moisture layers, snow-water equivalent, and potential evaporation), aggregated from hourly to daily.
- Static catchment attributes: the 197-column HydroATLAS/BasinATLAS table and 14 derived Caravan climate indices (aridity, precipitation/PET means, seasonality, snow fraction, high/low-precipitation frequency and duration).
- An extension-specific attributes table recording each gauge's basin name, streamflow period and missing fraction, data source, licence and gauge-specific notes.
- A single combined catchment-boundary shapefile (gauge_id only, EPSG:4326), with one distinct polygon per gauge.

DATA SOURCES

- Streamflow: the seven Melbourne Water gauges are drawn from the Australian Bureau of Meteorology (BoM) Water Data Online, using the quality-controlled "Water Course Discharge" series aggregated to a time-weighted daily mean; the three remaining gauges (Keilor, Sunbury, Gisborne) come from the Victorian Government Water Measurement Information System (Hydstra), daily mean discharge.
- Catchment polygons: derived from the Melbourne Water Stream Network (MWSTR v1.3.1; Walsh & Kunapo, 2023) by tracing each gauge's upstream sub-catchments through the stream-connectivity graph and simplifying lightly for compute tractability.
- Static catchment attributes: HydroATLAS / BasinATLAS (Linke et al., 2019).
- Meteorological forcings: ECMWF ERA5-Land (Muñoz-Sabater, 2019).

The dataset was built with the official Caravan Part-1 (Google Earth Engine) and Part-2 (local post-processing) notebooks, so its attributes, climate indices and forcing aggregation are computed identically to the rest of Caravan.

QUALITY AND VALIDATION

- Catchment areas were cross-validated against two independent agency studies — the Melbourne and Metropolitan Board of Works flood mitigation study (MMBW, 1986) and the Jacobs post-event analysis of the October 2022 flood (2023) — and agree to within ~1.7% on the three primary gauges (Bulla, Keilor, Sunbury) and within ~3.2% across all cross-validated gauges.
- Each gauge sits at the hydrological outlet (the downstream tip) of its own catchment, and the nested catchments are correctly contained (Konagaderra within Bulla within Keilor North within Keilor within Chifley Drive), not duplicated.
- The two largest floods in the catchment's instrumental history are clearly resolved. At Keilor (record from 1950) the two biggest daily-mean peaks are 14 October 2022 (about 503 m3/s) and 16 May 1974 (about 382 m3/s); the same first/second ordering holds at Bulla (record from 1955). The October 2022 event is the flood of record at most gauges, is consistent with the heavy rainfall of 13 October, and increases in magnitude downstream as expected.

NOTES AND CAVEATS

- Gauge 230106 (Maribyrnong River at Chifley Drive) is tidal. The BoM certifies a discharge rating only in the flood range, so this gauge is a reliable flood-event record with a low-confidence near-zero baseline; see the additional-attributes table.
- Streamflow is non-negative: small sub-cumec negative sensor readings are clipped to zero, as required by Caravan. Missing values are encoded as NaN.

STRUCTURE

The archive unpacks to the standard Caravan sub-dataset layout and can be merged by copying the "ausvic" folders into the corresponding Caravan directories: attributes/ausvic/, timeseries/csv/ausvic/ and timeseries/netcdf/ausvic/, shapefiles/ausvic/, and licenses/ausvic/. A README and a catchment-outlet figure are included.

CHANGES IN THIS VERSION

This version sources the seven Melbourne Water gauges from BoM Water Data Online (replacing an earlier Melbourne Water API source that contained spurious flood spikes and shorter records), extends the time series to March 2026, and provides the catchment metadata in the current Caravan attribute format (attributes_other plus an attributes_additional table).

LICENCE AND CITATION

Released under the Creative Commons Attribution 4.0 International (CC-BY-4.0) licence.

Lanzafame, L. (2026). Caravan-AUS-VIC: Maribyrnong River basin (10 gauges). Zenodo. https://doi.org/10.5281/zenodo.20580213

REFERENCES

- Kratzert, F., Nearing, G., Addor, N., et al. (2023). Caravan – A global community dataset for large-sample hydrology. Scientific Data, 10, 61.
- Linke, S., Lehner, B., Ouellet Dallaire, C., et al. (2019). Global hydro-environmental sub-basin and river reach characteristics at high spatial resolution. Scientific Data, 6, 283.
- Muñoz-Sabater, J. (2019). ERA5-Land hourly data from 1950 to present. Copernicus Climate Change Service (C3S) Climate Data Store.
- Walsh, C. J. & Kunapo, J. (2023). Melbourne Water Stream Network (MWSTR) v1.3.1. University of Melbourne.
- Melbourne and Metropolitan Board of Works (1986). Maribyrnong River Flood Mitigation Study (Report MMBW-D-0040).
- Jacobs Group (2023). Maribyrnong River Flood Event October 2022 — Post Event Analysis. Prepared for Melbourne Water.
