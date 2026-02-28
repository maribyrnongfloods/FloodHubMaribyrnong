# FloodHubMaribyrnong — Project Context

Contributing 12 Maribyrnong River gauging stations to [Caravan](https://github.com/kratzert/Caravan),
the open community dataset used by Google Flood Hub to train its AI flood forecasting model.

- **Zenodo DOI:** https://doi.org/10.5281/zenodo.18736844
- **Caravan submission:** https://github.com/kratzert/Caravan/issues/51
- **GitHub:** https://github.com/maribyrnongfloods/FloodHubMaribyrnong

## Repository layout

```
notebooks/
  1-derive_gauge_config_ausvic.ipynb    — gauge network config + MERIT Hydro area lookup
  2-fetch_catchments_ausvic.ipynb       — catchment polygon derivation via HydroBASINS BFS
  3-fetch_streamflow_ausvic.ipynb       — fetch daily streamflow from MW + VW APIs
  4-Caravan_part1_Earth_Engine.ipynb    — GEE: ERA5-Land export + HydroATLAS attributes
  5-Caravan_part2_local_postprocessing.ipynb — ERA5 post-processing + save Caravan outputs
  caravan_utils.py                      — aggregation and unit conversion utilities
  pet.py                                — FAO-56 Penman-Monteith PET

caravan_maribyrnong_gee/
  gauges_ausvic.json                    — gauge config (id, name, lat, lon, area_km2)
  attributes/attributes.csv             — HydroATLAS attributes from GEE
  shapefiles/ausvic_basin_shapes.*      — catchment polygons (WGS84)
  batch*.csv                            — ERA5-Land hourly GEE exports (gitignored, ~2.9 GB)

tasks/                                  — todo.md, lessons.md (gitignored)
```

Output lives in `caravan_maribyrnong/` (gitignored).
Zenodo zip is `caravan_maribyrnong_zenodo.zip` (also gitignored).

## Gauge network

12 stations across the Maribyrnong catchment, Victoria, Australia.
Gauge IDs follow Caravan convention: `ausvic_XXXXXX` (two-part format).

- **Mainstem** (Melbourne Water API): 230119A, 230100A, 230102A, 230211A, 230107A, 230237A, 230106A
- **Keilor** (Victorian Water / Hydstra API): 230200
- **Tributaries** (Victorian Water / Hydstra API): 230206, 230202, 230213, 230227

3 gauges excluded (in CAMELS AUS v2): 230210, 230205, 230209.
1 gauge excluded (agency duplicate of 230202): 230104A.

Keilor (230200) has records from 1908 — the longest in the network.
Chifley Drive (230106A) is tidal — only 263 valid flow days above the tidal threshold.

## Key technical facts

- Streamflow unit: **mm/day** (converted from ML/day ÷ catchment area km²)
- ERA5-Land fetched from **1950** (dataset start); pre-1950 rows have ERA5 cols = ""
- SILO removed: not globally available (Caravan reviewer Feb 2026)
- Missing data: empty string in CSV, `_FillValue = -9999` in netCDF
- CSV has **41 columns**: date + streamflow + 39 ERA5-Land
  (10 instant vars × 3 + 2 accum flux vars × 3 + total_precip_sum + pet_era5_sum + pet_fao_pm_sum)
- FAO-56 Penman-Monteith PET computed per Caravan `pet.py`
- Climate indices in `attributes_caravan_ausvic.csv` computed over 1981–2020 per Caravan standard
- Catchment areas from HydroATLAS `UP_AREA`; Keilor = official VW figure 1305.4 km²; Keilor North + Chifley Drive = MERIT Hydro 90m (HydroBASINS Level-12 too coarse for these co-located gauges)
- All data licensed CC-BY-4.0

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
