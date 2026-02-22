# License — Caravan-AUS-VIC (Maribyrnong River)

## Dataset extension

This dataset extension contributes streamflow and meteorological timeseries
for two gauging stations on the Maribyrnong River, Victoria, Australia, to
the [Caravan](https://github.com/kratzert/Caravan) community dataset.

| gauge_id | Station name | Station ID |
|---|---|---|
| aus_vic_230200 | Maribyrnong River at Keilor | 230200 |
| aus_vic_230106 | Maribyrnong River at Chifley Drive | 230106A |

---

## Streamflow data

**Station 230200 — Maribyrnong River at Keilor**

Source: Victorian Water Monitoring Information System (WMIS)
<https://data.water.vic.gov.au/>

Provider: Victorian Department of Energy, Environment and Climate Action
(DEECA), through the Victorian Water Register.

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

---

**Station 230106A — Maribyrnong River at Chifley Drive**

Source: Melbourne Water public API
<https://api.melbournewater.com.au/rainfall-river-level>

Provider: Melbourne Water Corporation.

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

Note: Flow at this station is only reliable above approximately 1 m water
level (> 16,520 ML/day) due to tidal influence at the gauge location.
Days below this threshold are absent from the timeseries.

---

## Meteorological forcing data

**SILO DataDrill**

Source: SILO DataDrill gridded climate dataset
<https://www.longpaddock.qld.gov.au/silo/>

Provider: Queensland Department of Environment and Science, via the
Long Paddock service.

Variables included: daily rainfall, maximum temperature, minimum temperature,
Morton potential evapotranspiration, solar radiation, vapour pressure.

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

---

**ERA5-Land (ECMWF)**

Source: ERA5-Land hourly data via Google Earth Engine
<https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY>

Provider: European Centre for Medium-Range Weather Forecasts (ECMWF).

Variables included: dewpoint temperature, surface net solar radiation,
surface net thermal radiation, surface pressure, 10-m wind components (U and V),
snow depth water equivalent, volumetric soil water layers 1–4.

Licence: [Copernicus Climate Change Service (C3S) Licence](
https://cds.climate.copernicus.eu/api/v2/terms/static/licence-to-use-copernicus-products.pdf)
— permits use for research and education. Attribution required.

---

## Catchment boundary shapefiles

Derived from HydroBASINS Level 12 (© HydroSHEDS / WWF), upstream-traced
from the gauge outlet cell.

Source: <https://www.hydrosheds.org/products/hydrobasins>

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

---

## This dataset extension

Released under [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/).

When using this dataset, please cite the original data providers above and the
Caravan dataset paper:

> Kratzert, F., Gauch, M., Nearing, G., and Klotz, D. (2023). Caravan — A
> global community dataset for large-sample hydrology. *Scientific Data*, 10,
> 61. <https://doi.org/10.1038/s41597-023-01975-w>
