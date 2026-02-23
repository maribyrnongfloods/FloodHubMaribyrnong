# Pipeline, workflow and testing rules

## Data pipeline (run in order)

```
1. python fetch_maribyrnong.py
2. python fetch_silo_met.py --username your@email.com
3. python fetch_era5land.py          # requires GEE auth
4. python fetch_hydroatlas.py        # requires GEE auth
5. python fetch_catchments.py        # requires GEE auth
6. python write_netcdf.py
7. python generate_license.py
8. python make_map.py                # generates gauge_map.png
```

GEE project: `floodhubmaribyrnong`

GEE one-off setup:
```python
import ee
ee.Authenticate()
ee.Initialize(project='floodhubmaribyrnong')
```

## Git branches

- `main` — stable, mirrors latest release
- `dev`  — active development (default working branch)

Always work on `dev`. To publish: push `dev`, merge to `main`, push `main`.

```bash
git push upstream dev
git checkout main && git merge dev --no-edit
git push upstream main
git checkout dev
```

## Tests

```bash
python -m pytest tests/ -q                          # 39 unit tests, no network
python test_run.py --username your@email.com        # live API smoke test
```

Tests run automatically on every `git commit` via pre-commit hook.
Never use `--no-verify` to skip the hook.

## Caravan compliance checklist (all complete)

- `streamflow` column in mm/day
- SILO met columns (7 variables)
- ERA5-Land columns (33 variables)
- `attributes_caravan_aus_vic.csv` (10 climate stats)
- `attributes_hydroatlas_aus_vic.csv` (294 basin attributes)
- `attributes_other_aus_vic.csv` (gauge metadata)
- ESRI shapefiles (per-gauge + combined)
- CF-1.8 compliant netCDF4
- CC-BY-4.0 license file
- Zenodo upload (DOI: 10.5281/zenodo.18736844)
- GitHub issue (kratzert/Caravan#51)
