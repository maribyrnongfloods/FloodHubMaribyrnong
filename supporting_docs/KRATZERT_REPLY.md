Hi @kratzert,

Thanks again for the thorough review. I've published a new version that resolves the two outstanding points from your last comment (the `attributes_other` columns and the basin polygons), and I've re-checked everything from your earlier review as well. There's also one data-quality upgrade.

**New DOI:** https://doi.org/10.5281/zenodo.20622400 (all versions: https://doi.org/10.5281/zenodo.18736843)
**Code + README:** https://github.com/maribyrnongfloods/FloodHubMaribyrnong

---

### Basin polygons (gauges mid-polygon / shared polygons)

This was the main fix. I replaced the HydroBASINS Level-12 polygons with catchments derived from the **Melbourne Water Stream Network (MWSTR)**, tracing each gauge's true upstream sub-catchment. As a result:

- **Each gauge now sits at its catchment outlet** (the downstream tip), not the middle — 6–300 m from the polygon edge versus 6–38 km from the centroid. I've added an `outlet_proof.png` to the bundle showing all 10. Figure attached below.
- **No two gauges share a polygon.** All 10 are distinct and correctly nested (e.g. Konagaderra ⊂ Bulla ⊂ Keilor North ⊂ Keilor ⊂ Chifley Drive), so each gauge gets its own forcings and attributes.
- The derived areas are cross-validated against two independent agency studies (MMBW 1986 and Jacobs 2023) to within **~1.7%** on the primary gauges, so they're representative of the true basin areas.

### `attributes_other` → 6 columns + `attributes_additional`

`attributes_other_ausvic.csv` now contains exactly the 6 standard columns in the standard order (`gauge_id, gauge_name, country, gauge_lat, gauge_lon, area`, with `country` as ISO alpha-2 `AU`). Everything else (`basin_name, unit_area, streamflow_period, streamflow_missing, streamflow_units, source, license, note`) has moved to `attributes/ausvic/attributes_additional_ausvic.csv`.

### Only-new gauges (CAMELS-AUS v2 overlap)

The 3 gauges that overlapped CAMELS-AUS v2 (230205, 230209, 230210) were removed. All **10 remaining gauges are new to Caravan** — re-checked against the CAMELS-AUS v2 station list with zero overlap.

### Everything else from your first review

- **Built with the official Caravan code** — Part-1 (Earth Engine) for the HydroATLAS attributes and ERA5-Land forcings, Part-2 for the timeseries and climate indices.
- **HydroATLAS** re-derived with the Part-1 notebook against the new polygons: `gauge_id` + 196 BasinATLAS attributes. (The GEE BasinATLAS asset has gained a couple of properties since the 2023 Caravan release — happy to drop the extras if you'd rather keep the column set identical.)
- **SILO removed** — forcings are ERA5-Land only, so there are no pre-1950 forcings anywhere. To your question about gauge 230200 (Keilor): its 1908–1949 streamflow (~10,200 valid days) is retained as streamflow-only rows with **empty** forcing columns; ERA5-Land begins 1950-01-02 as everywhere else.
- **Full-period forcings** — each gauge has ERA5-Land over the entire 1950-01-02 → 2026-03-06 window, not just the period overlapping streamflow.
- **Naming** is `ausvic_*`; a **single** `ausvic_basin_shapes.shp` with only a `gauge_id` column; the duplicate root-level hydroatlas file is removed (the `attributes/` directory now contains only `ausvic/`).

### Data-quality upgrade in this version

The 7 Melbourne Water gauges are now sourced from **BoM Water Data Online** (the quality-controlled `DMQaQc.Merged` discharge series) instead of the Melbourne Water API. The API carried spurious flood spikes; the BoM record is cleaner and longer. As a sanity check, the dataset now resolves the catchment's largest floods correctly — at Keilor (record from 1908) the three biggest daily-mean peaks are **October 2022** (the flood of record, ≈503 m³/s), **September 1916** (≈459) and **May 1974** (≈382), matching the SES historic flood table, and the October 2022 peak increases downstream as expected (Konagaderra ≈214 → Bulla ≈317 → Keilor ≈503 m³/s). Known per-gauge caveats (tidal baseline at Chifley Drive; reservoir regulation at Gisborne; a likely high-stage rating underestimate at Keilor North in Oct-2022) are documented in `attributes_additional`.

Happy to make any further changes. Thanks for maintaining Caravan!

Lee