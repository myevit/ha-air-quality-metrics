# Canadian AQHI smoke / PM2.5 (local estimate)

Choose **Outdoor — Canadian AQHI smoke / PM2.5 (local estimate)** when adding an
Air Quality Metrics entry. Select **one outdoor PM2.5 concentration sensor**,
device class `pm25`, unit `μg/m³` (the typographic `µg/m³` is also accepted).
A reported zero is valid. The source must be recorded by Home Assistant.
Existing Indoor and Outdoor (US EPA AQI) entries keep their algorithms and IDs.
Create a separate Canadian entry; this is not a relabelled US AQI.

## Method and limits

This implements the **Canadian one-hour PM2.5-only smoke component**, not the
complete national three-pollutant AQHI or a complete provincial AQHI-Plus.
It needs no additional hardware. It neither identifies smoke chemically nor
proves wildfire origin. The selected sensor's measurement/calibration applies;
no undocumented AirGradient/PurpleAir correction is introduced.

For a valid one-hour mean `P` in micrograms per cubic metre:

```
smoke_index = min(11, max(1, ceil(P / 10)))
```

No preliminary rounding of `P`. Numeric **11 means the capped display `10+`**,
not a separately quantified risk grade. Categories:

| Numeric state | Display | Category state |
|---|---|---|
| 1–3 | 1–3 | `low` |
| 4–6 | 4–6 | `moderate` |
| 7–10 | 7–10 | `high` |
| 11 | 10+ | `very_high` |

Examples from the primary study's Table 2: **51 μg/m³ → 6** and
**100 μg/m³ → 10**. Decimal boundaries follow its explicit ceiling rule:
30 → 3, 30.01 → 4, 60 → 6, 60.01 → 7, 100.01 → 10+.
BCCDC Table 1 explicitly places zero in band 1.

The ordinary national AQHI uses NO2, ozone, and PM2.5 trailing three-hour
averages and is reported hourly. BC calculates both the three-pollutant value
and the PM-only component and reports the higher. Alberta has other pollutant
overrides as well. This integration **does not** pretend absent ozone/NO2 are
zero, use AirGradient relative NOx as NO2, include VOC or PM10 in this formula,
or combine local and regional values with an unapproved maximum policy.
A low local PM-only result does **not** establish low overall pollution risk.
Consult official AQHI/alerts separately. No safety/activity advice or alerts
are generated here.

## Time and missing-data contract

The period is the **previous fully completed UTC clock hour**, not the current
instantaneous reading, not an EPA NowCast, and not a sample-count average.
At 12:20 UTC it describes [11:00, 12:00). Polling follows the configured
interval; results can lag a changing smoke event by about an hour plus polling.

The following are **conservative local implementation policies**, not claimed
ECCC regulatory QA/completeness requirements:

- Use HA recorder's state at the hour start plus **all** transitions during the
  hour, including unknown/unavailable and unit/device-class changes.
- Integrate the piecewise-constant HA state by duration. For example, 50 minutes
  at 10 and 10 minutes at 70 gives **20**, not the change-sample mean 40.
- A held valid state carries forward from before the start. An unchanged,
  actively reporting zero is not missing just because it produced no changes.
- Require **100% valid time coverage**. No start seed, recorder exclusion,
  a numeric negative/nonfinite value, wrong units/device class, or any positive
  duration of unknown/unavailable prevents a numeric result. An invalid segment
  ends the previous held numeric state; it is never silently skipped.
- Current source must be valid and have HA `last_reported` no more than
  **15 minutes** old (future timestamps are rejected too). Slow reporters may
  therefore be unknown. Polling determines how soon this is reflected.
- Recorder read errors clear the current result to unknown rather than retaining
  a previous apparently good value. Category clears together with the index.

HA held-state history is not an independent guarantee of continuous instrument
sampling: a silent past outage not represented by an invalid state cannot be
reconstructed. Consumer-sensor accuracy, calibration, recorder inclusion,
retention, and source reporting frequency remain deployment responsibilities.
The public method sources do not specify HA interpolation, within-hour recorder
coverage, or consumer-sensor freshness rules. A study's requirement that no more
than 25% of **48-hour analysis values** be missing is **not** a within-hour
instrument completeness rule and is not used here.

## Native entity / card contract

Entity IDs are assigned by HA and may be renamed; select them rather than
hardcoding example household IDs. Unique-ID suffixes:

- `{entry_id}_aqhi_smoke_pm25`: dimensionless numeric measurement, **no US AQI
  device class**, no physical unit; 1–11 or unknown/unavailable.
- `{entry_id}_aqhi_smoke_category`: enum `low`, `moderate`, `high`, `very_high`,
  or unknown/unavailable.

Both expose `index_type: canadian_aqhi_smoke_pm25`,
`scope: local_pm25_only_estimate`, `display_value` (`10+` at 11), `category`,
`source_entity`, `pm25_mean`, `mean_unit: μg/m³`, `coverage` (fraction 0–1),
`coverage_required: 1.0`, `period_start`, `period_end`, `averaging`, `method`,
`source_max_age_minutes: 15`, `source_last_reported`, `evaluated_at`,
`limitations`, and `status`.
`source_last_reported` is the authoritative HA source receipt timestamp (ISO
UTC, null if missing); `evaluated_at` is the coordinator evaluation start time
(ISO UTC), refreshed on every evaluation including invalid/history failures.
Changing this attribute publishes repeated valid calculations even when the
index and source concentration are unchanged. Consumers must bind certification
to `source_entity`, age both timestamps independently, and still reject a
currently invalid/unavailable source. Normal HA frontend states omit
`last_reported`; source `last_updated` cannot certify unchanged reports.
Coverage uses exact microsecond durations; weighted concentrations and ceiling
use exact rational arithmetic without rounding source decimals. Only the
diagnostic `pm25_mean` attribute is converted to a JSON-compatible float.
Statuses are `valid`, `source_invalid`, `source_stale`, `history_unavailable`,
`incomplete_history`. A frontend must respect unknown/unavailable, must not map
11 to a US AQI grade, and should label it **AQHI smoke / PM2.5 · local estimate**.
Keep official community AQHI separate, clearly labelled. The Canadian risk
categories do not authorize an overall “safe” label.

## Sources and attribution

1. **ECCC, About the AQHI**, page details **2026-10-14**:
   https://www.canada.ca/en/environment-climate-change/services/air-quality-health-index/about.html
   Three pollutants, hourly PM-only smoke adjustment, 1–10+ scale and community
   averaging (different from an individual monitoring site).
2. **ECCC news release, June 5 2024**, page details June 12 2024:
   https://www.canada.ca/en/environment-climate-change/news/2024/06/new-public-alert-makes-it-easier-to-understand-air-quality-conditions-during-wildfire-events-and-year-round.html
   Explains smoke reporting using PM2.5 hourly. The historical alert policy is
   context only, not a current alert implementation in this integration.
3. **BCCDC, Wildfire Smoke and the AQHI, last updated May 2024**, Table 1:
   https://www.bccdc.ca/resource-gallery/Documents/Guidelines%20and%20Forms/Guidelines%20and%20Manuals/Health-Environment/BCCDC_WildFire_FactSheet_SmokeAndTheAQHI.pdf
   Zero floor, mass units, bands/categories, maximum10+, higher-of-two BC method.
4. **Yao et al., Assessment of the AQHI and four alternate AQHI-Plus amendments
   for wildfire seasons in BC**, published online July 8 2019, *Canadian Journal
   of Public Health* 111, 96–106 (February 2020), DOI
   **10.17269/s41997-019-00237-w**, primary full text:
   https://pmc.ncbi.nlm.nih.gov/articles/PMC7046905/
   Table 2 and Methods / “1-h PM2.5Only” explicitly specify ceiling(P/10), cap10+;
   Table2 supplies the 51→6 and100→10 examples. “Assigning AQHI and AQHI-Plus
   values to LHAs” explains coding10+ as11 for analysis, not a new public grade.
5. **Government of Alberta, Air Quality Health Index – Calculation**, current
   page retrieved during development:
   https://www.alberta.ca/air-quality-health-index-calculation
   Describes national three-pollutant basis, harmonized hourly PM override and
   other Alberta pollutant overrides; links source4. No historical Alberta
   activation threshold is guessed or presented as current policy.

Full local three-pollutant AQHI is intentionally not implemented without actual
NO2 and O3 sources. The local smoke component can differ from official AQHI for
legitimate scientific, timing, spatial, instrument, and coverage reasons.
