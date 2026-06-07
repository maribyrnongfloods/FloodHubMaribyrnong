# Caravan-AUS-VIC: Maribyrnong River basin (10 gauges)

Caravan dataset extension for the Maribyrnong River catchment, north-west Melbourne, Victoria, Australia.

## What's in this bundle

- **10 gauges** spanning the Maribyrnong catchment: upper Deep Creek (Lancefield) down through Bulla and Keilor to Chifley Drive at the city fringe, plus Jacksons Creek (Gisborne → Sunbury) and Bolinda Creek at Clarkefield.
- **Daily streamflow** (mm/day) per gauge, area-normalised with the GEE Part-1 polygon areas.
- **Daily ERA5-Land forcings** (1950-01-02 → 2024-01-01), 14 variables aggregated from hourly UTC to local time.
- **Attributes**: 6-column `attributes_other`, 197 HydroATLAS attributes, 14 derived climate indices, and an extension-specific `attributes_additional` (basin name, streamflow period/missing/units, source, license, notes).
- **Single combined shapefile** `ausvic_basin_shapes.shp` (gauge_id only, EPSG:4326), 10 distinct simplified polygons.

Built with the official Caravan Part-1 (Earth Engine) and Part-2 (local postprocessing) notebooks.

## Gauge list

| gauge_id | name | km² | streamflow source | area cross-validated |
|----------|------|-----|-------------------|----------------------|
| ausvic_230119 | Deep Creek at Doggetts Bridge, Lancefield | 219.2 | BoM Water Data Online | MMBW 1986 |
| ausvic_230100 | Deep Creek at Darraweit Guim | 483.8 | BoM Water Data Online | Jacobs 2023 (500) |
| ausvic_230107 | Deep Creek at Konagaderra | 620.7 | BoM Water Data Online | MMBW 1986 |
| ausvic_230102 | Deep Creek at Bulla | 860.3 | BoM Water Data Online | MMBW 1986 (874), Jacobs 2023 (865) |
| ausvic_230237 | Maribyrnong River at Keilor North | 1,279.4 | BoM Water Data Online | MMBW 1986 |
| ausvic_230200 | Maribyrnong River at Keilor | 1,306.0 | Victorian Water (Hydstra) | MMBW 1986 (1,312), Jacobs 2023 (1,303) |
| ausvic_230106 | Maribyrnong River at Chifley Drive | 1,385.7 | BoM Water Data Online | MWSTR-at-Chifley (1,386) |
| ausvic_230206 | Jacksons Creek at Gisborne | 91.0 | Victorian Water (Hydstra) | MMBW 1986 |
| ausvic_230202 | Jacksons Creek at Sunbury | 342.8 | Victorian Water (Hydstra) | MMBW 1986 (338), Jacobs 2023 (337) |
| ausvic_230211 | Bolinda Creek at Clarkefield | 96.0 | BoM Water Data Online | MMBW 1986 (sub-catchment K) |

Two independent agency sources (MMBW 1986 + Jacobs 2023) agree with the MWSTR-derived areas to within ~1.5 % on every primary gauge.

## Streamflow source

The seven Melbourne Water gauges are taken from **BoM Water Data Online** (the quality-controlled `DMQaQc.Merged` discharge series), aggregated from sub-daily to a time-weighted daily mean. This replaces the earlier Melbourne Water API source and is cleaner and longer: records reach back to **1955** (Bulla), **1975** (several gauges) and **1979** (Konagaderra), and earlier API artefacts (spurious flood spikes) are absent. The three Victorian Water gauges (Keilor, Gisborne, Sunbury) come from the Hydstra daily-discharge API (variable 141.00). The October 2022 flood is captured correctly, with peaks increasing downstream (Konagaderra ≈214 → Bulla ≈317 → Keilor Nth ≈313 → Chifley Drive ≈494 m³/s daily mean).

## Caveats

- **230106 (Chifley Drive) is tidal.** BoM certifies a discharge rating only in the flood range — every reading above ~190 m³/s is quality-A (including the Oct-2022 peak) — and records the tidal baseflow as an uncertified ~0. It is therefore a reliable flood-event record with a low-confidence near-zero baseline. See `attributes_additional`.
- **230107 (Konagaderra)** is mixed BoM quality (~51 % quality-A, ~34 % quality-E); usable but lower-confidence than the mainstem Deep Creek gauges.
- **230202 (Sunbury)** has Hydstra data from 1908, but pre-1960 values are level-derived artefacts without a rating curve and are excluded (kept from 1960).
- **Negatives**: small near-zero negative sensor readings (sub-cumec) are clipped to 0 (Caravan requires non-negative streamflow). Missing values are `NaN`.
- **Period**: the merged timeseries runs to 2024-01-01, bounded by the ERA5-Land forcing export; streamflow observations beyond that are not included.

## Files

```
attributes/ausvic/   attributes_other_ausvic.csv (6 cols)
                     attributes_hydroatlas_ausvic.csv (197)
                     attributes_caravan_ausvic.csv (14 climate indices)
                     attributes_additional_ausvic.csv (extension-specific)
timeseries/csv/ausvic/      <gauge_id>.csv   (forcings + streamflow)
timeseries/netcdf/ausvic/   <gauge_id>.nc
shapefiles/ausvic/   ausvic_basin_shapes.{shp,shx,dbf,prj,cpg}
LICENSE.txt          CC-BY-4.0 + source attributions
```
