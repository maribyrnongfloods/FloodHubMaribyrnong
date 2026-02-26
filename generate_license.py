#!/usr/bin/env python3
"""
generate_license.py

Writes caravan_maribyrnong/licenses/ausvic/license_ausvic.md

This file is required by the Caravan contribution process.  It declares the
data sources and the licence under which this dataset extension is released.

Usage
-----
    python generate_license.py
"""

from pathlib import Path

LICENSE_DIR  = Path("caravan_maribyrnong") / "licenses" / "ausvic"
LICENSE_PATH = LICENSE_DIR / "license_ausvic.md"

LICENSE_TEXT = """\
# License — Caravan-AUSVIC (Maribyrnong River)

## Dataset extension

This dataset extension contributes streamflow and ERA5-Land meteorological
timeseries for 10 gauging stations across the Maribyrnong River catchment,
Victoria, Australia, to the [Caravan](https://github.com/kratzert/Caravan)
community dataset.

Three gauges (230205, 230209, 230210) present in CAMELS AUS v2 are excluded
to avoid duplicating records already in Caravan.

### Melbourne Water API gauges

| gauge_id | Station name | Station ID |
|---|---|---|
| ausvic_230100 | Deep Creek at Darraweit Guim | 230100A |
| ausvic_230211 | Bolinda Creek at Clarkefield | 230211A |
| ausvic_230104 | Maribyrnong River at Sunbury | 230104A |
| ausvic_230107 | Konagaderra Creek at Konagaderra | 230107A |
| ausvic_230200 | Maribyrnong River at Keilor | 230200 |
| ausvic_230106 | Maribyrnong River at Chifley Drive | 230106A |

### Tributary gauges (Victorian Water / Hydstra API)

| gauge_id | Station name | Station ID |
|---|---|---|
| ausvic_230206 | Jackson Creek at Gisborne | 230206 |
| ausvic_230202 | Jackson Creek at Sunbury | 230202 |
| ausvic_230213 | Turritable Creek at Mount Macedon | 230213 |
| ausvic_230227 | Main Creek at Kerrie | 230227 |

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

**Keilor and tributary stations (230200, 230206, 230202, 230213, 230227) —
Victorian Water Monitoring Information System**

Source: Victorian Water Monitoring Information System (WMIS)
<https://data.water.vic.gov.au/>

Provider: Victorian Department of Energy, Environment and Climate Action
(DEECA), through the Victorian Water Register.

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

---

## Meteorological forcing data

**ERA5-Land (ECMWF)**

Source: ERA5-Land daily aggregated data via Google Earth Engine
<https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR>

Provider: European Centre for Medium-Range Weather Forecasts (ECMWF).

Variables included: dewpoint temperature, surface net solar radiation,
surface net thermal radiation, surface pressure, 10-m wind components (U and V),
snow depth water equivalent, volumetric soil water layers 1–4.

Coverage: 1950-01-01 to present (ERA5-Land dataset start).

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
