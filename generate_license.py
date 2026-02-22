#!/usr/bin/env python3
"""
generate_license.py

Writes caravan_maribyrnong/licenses/aus_vic/license_aus_vic.md

This file is required by the Caravan contribution process.  It declares the
data sources and the licence under which this dataset extension is released.

Usage
-----
    python generate_license.py
"""

from pathlib import Path

LICENSE_DIR = Path("caravan_maribyrnong") / "licenses" / "aus_vic"
LICENSE_PATH = LICENSE_DIR / "license_aus_vic.md"

LICENSE_TEXT = """\
# License — Caravan-AUS-VIC (Maribyrnong River)

## Dataset extension

This dataset extension contributes streamflow and meteorological timeseries
for 13 gauging stations across the Maribyrnong River catchment, Victoria,
Australia, to the [Caravan](https://github.com/kratzert/Caravan) community
dataset.

### Mainstem gauges (Melbourne Water API)

| gauge_id | Station name | Station ID |
|---|---|---|
| aus_vic_230100 | Maribyrnong River at Darraweit | 230100A |
| aus_vic_230211 | Maribyrnong River at Clarkefield | 230211A |
| aus_vic_230104 | Maribyrnong River at Sunbury | 230104A |
| aus_vic_230107 | Konagaderra Creek at Konagaderra | 230107A |
| aus_vic_230200 | Maribyrnong River at Keilor | 230200 |
| aus_vic_230106 | Maribyrnong River at Chifley Drive | 230106A |

### Tributary gauges (Victorian Water / Hydstra API)

| gauge_id | Station name | Station ID |
|---|---|---|
| aus_vic_230210 | Jacksons Creek at Bullengarook | 230210 |
| aus_vic_230206 | Jackson Creek at Gisborne | 230206 |
| aus_vic_230202 | Jackson Creek at Sunbury | 230202 |
| aus_vic_230205 | Deep Creek at Bulla | 230205 |
| aus_vic_230209 | Barringo Creek at Barringo | 230209 |
| aus_vic_230213 | Turritable Creek at Mount Macedon | 230213 |
| aus_vic_230227 | Main Creek at Kerrie | 230227 |

---

## Streamflow data

**Mainstem stations (230100A, 230211A, 230104A, 230107A, 230106A) —
Melbourne Water public API**

Source: Melbourne Water public API
<https://api.melbournewater.com.au/rainfall-river-level>

Provider: Melbourne Water Corporation.

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

Note: Flow at station 230106A (Chifley Drive) is only reliable above
approximately 1 m water level (> 16,520 ML/day) due to tidal influence.
Days below this threshold are absent from the timeseries.

---

**Keilor and tributary stations (230200, 230210, 230206, 230202, 230205,
230209, 230213, 230227) — Victorian Water Monitoring Information System**

Source: Victorian Water Monitoring Information System (WMIS)
<https://data.water.vic.gov.au/>

Provider: Victorian Department of Energy, Environment and Climate Action
(DEECA), through the Victorian Water Register.

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

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
"""


def main():
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_PATH.write_text(LICENSE_TEXT, encoding="utf-8")
    print(f"License file written -> {LICENSE_PATH}")


if __name__ == "__main__":
    main()
