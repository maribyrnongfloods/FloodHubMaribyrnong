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

Source: SILO DataDrill gridded climate dataset
<https://www.longpaddock.qld.gov.au/silo/>

Provider: Queensland Department of Environment and Science, via the
Long Paddock service.

Variables included: daily rainfall, maximum temperature, minimum temperature,
Morton potential evapotranspiration, solar radiation, vapour pressure.

Licence: [Creative Commons Attribution 4.0 International (CC BY 4.0)](
https://creativecommons.org/licenses/by/4.0/)

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
    print(f"License file written → {LICENSE_PATH}")


if __name__ == "__main__":
    main()
