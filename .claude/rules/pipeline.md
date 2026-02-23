# Pipeline, workflow and testing rules

## Data pipeline (run in order)

```
1. python fetch_maribyrnong.py
2. python fetch_era5land.py          # requires GEE auth — builds full 1950+ CSV spine
3. [Colab notebook]                  # HydroATLAS attrs via official Caravan Part-1 notebook
4. python fetch_catchments.py        # requires GEE auth — single ausvic_basin_shapes.shp
5. python write_netcdf.py
6. python generate_license.py
7. python make_map.py                # generates gauge_map.png
```

NOTE: `fetch_silo_met.py` has been removed. SILO is not globally available
and must not be included in Caravan (reviewer feedback Feb 2026).

NOTE: `fetch_hydroatlas.py` (our custom script) produces non-standard columns.
Use the official Caravan Part-1 Colab notebook instead:
  https://github.com/kratzert/Caravan/blob/main/code/Caravan_part1_Earth_Engine.ipynb

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
python -m pytest tests/ -q     # unit tests, no network
python test_run.py             # live API smoke test (Hydstra + Melbourne Water)
```

Tests run automatically on every `git commit` via pre-commit hook.
Never use `--no-verify` to skip the hook.

## Caravan compliance checklist (revised after Feb 2026 reviewer feedback)

- [x] `streamflow` column in mm/day
- [ ] ERA5-Land columns (33 variables) — SILO removed, re-run fetch_era5land.py
- [ ] `attributes_caravan_ausvic.csv` — must recompute from ERA5-Land via Caravan Part-2 notebook
- [ ] `attributes_hydroatlas_ausvic.csv` — must re-derive via Caravan Part-1 Colab notebook
- [ ] `attributes_other_ausvic.csv` — standard columns only; extra columns → `attributes_additional_ausvic.csv`
- [ ] `ausvic_basin_shapes.shp` (single combined, gauge_id column only)
- [ ] CF-1.8 compliant netCDF4 (35 cols, no SILO)
- [x] CC-BY-4.0 license file (`license_ausvic.md`)
- [ ] 10 gauges (3 CAMELS AUS v2 duplicates removed: 230205, 230209, 230210)
- [ ] All gauge IDs renamed `aus_vic_` → `ausvic_`
- [ ] Zenodo re-upload with new version
- [ ] Update GitHub issue kratzert/Caravan#51 with new DOI
