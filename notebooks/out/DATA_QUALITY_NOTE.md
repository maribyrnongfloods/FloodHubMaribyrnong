# Streamflow data-quality note — ausvic (Maribyrnong) BoM gauges

**Purpose.** Documents the BoM Water Data Online quality codes carried by the 7 Melbourne Water
streamflow gauges in this submission, so the flags travel with the data. Per project decision the
pipeline **keeps all gauges and does not filter on quality code** — therefore these flags are
documented here.

All 7 are served by BoM as the quality-controlled `DMQaQc.Merged.AsStored` discharge series
(parameter "Water Course Discharge", m³/s), aggregated here to a time-weighted daily mean.

## BoM quality-code legend (from each export's `disclaimer.txt`)

| Code | Grade | Meaning |
|---|---|---|
| 10 | quality-A | The record set is the best available given technologies/techniques at classification. |
| 90 | quality-B | The record set is compromised in its ability to truly represent the parameter. |
| 110 | quality-C | The record set is an estimate. |
| 140 | quality-E | The record set's ability to truly represent the parameter is not known. |
| 210 | quality-F | The record set is not of release quality or contains missing data. |

## Per-gauge quality-code mix (share of sub-daily readings)

Three gauges report the BoM A–F numeric scheme above:

| gauge | name | A (10) | B (90) | C (110) | E (140) | F (210) |
|---|---|---|---|---|---|---|
| 230102 | Deep Ck d/s Bulla Rd, Bulla | **94.3%** | 0.9% | 0.1% | 2.6% | 2.1% |
| 230107 | Deep Ck at Konagaderra | **51.3%** | 0.2% | 3.6% | **34.0%** | 10.9% |
| 230106 | Maribyrnong R at Chifley Dr | 0.1% | 0.0% | – | – | **99.9%** |

The other four report a **4-digit provider code** (not in the supplied A–F legend; each dominated
by a single in-service code, daily records validate cleanly — legend worth confirming with
Melbourne Water/BoM):

| gauge | name | dominant code | mix |
|---|---|---|---|
| 230100 | Deep Ck at Darraweit Guim | 1034 (76.5%) | 1164 15.6%, 1134 5.7%, 1234 1.8%, 1114 0.5% |
| 230119 | Deep Ck at Doggetts Bridge, Lancefield | 1034 (68.0%) | 1134 31.4%, 1164 0.2%, 1234 0.2%, 1114 0.1% |
| 230211 | Bolinda Ck at Clarkefield | 1034 (94.5%) | 1164 4.2%, 1114 0.7%, 1234 0.5%, 1134 0.1% |
| 230237 | Maribyrnong R d/s Jacksons Ck, Keilor Nth | 1034 (86.8%) | 1234 6.6%, 1134 6.0%, 1164 0.5%, 1114 0.1% |

## Caveats to carry into the submission

**230106 — Maribyrnong River at Chifley Drive (tidal; a flood-event gauge).** The headline
"99.9% quality-F" is misleading on its own. BoM assigns quality codes here **by flow regime**:

- **Every reading above ~190 m³/s is quality-A** (best available). The quality-A readings are
  exclusively high flows — min 191, median 217, max 770 m³/s — i.e. BoM has a **certified rating
  for the flood range** at this gauge. The Oct-2022 flood is captured at quality-A (~494 m³/s
  daily mean), consistent with the event and with the downstream-increasing peak sequence.
- Below the flood range the site is tidal and BoM does not certify a discharge, recording ~0
  (quality-F). So ~99% of readings are a zero/uncertified baseline.

Net: **230106 is a reliable flood-event record with a low/zero baseline** — well-suited to flood
forecasting, which is the dataset's purpose. The zeros should be read as "no certified freshwater
discharge", not as precise low-flow measurements.

**230107 — Deep Creek at Konagaderra (mixed).** ~51% quality-A but ~34% quality-E
("representativeness unknown") and ~11% quality-F. Usable, lower-confidence than the mainstem
Deep Creek gauges.

**230202 — Jacksons Creek at Sunbury (Hydstra, not BoM).** Record runs from 1908 but 1908–1959 are
~0.25 ML/day level-derived artefacts (no rating curve); kept from **1960** only.

## Suggested wording for `attributes` / README

> Streamflow for the seven Melbourne Water gauges is the BoM Water Data Online
> `DMQaQc.Merged` quality-controlled discharge series, aggregated to daily mean; published
> per-reading quality codes are retained unfiltered. Gauge 230106 (Maribyrnong River at Chifley
> Drive) is tidal: BoM certifies discharge only in the flood range (every reading > ~190 m³/s is
> quality-A, including the Oct-2022 peak), recording the tidal baseflow as an uncertified zero —
> it is a reliable flood-event record with a near-zero baseline. Gauge 230107 (Deep Creek at
> Konagaderra) is mixed quality (~51% quality-A, ~34% quality-E). The remaining three gauges
> (230200, 230206, 230202) are Victorian Water (Hydstra) daily discharge.
