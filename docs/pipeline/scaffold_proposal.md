# Scaffold proposal — CMS DE-SynPUF demo island

This is a proposal, not a declaration. Each metric below is a hypothesis derived from the domaining pass (entity model + data dictionary). It's presented for confirmation or correction, not asserted as settled — consistent with "consult, don't dictate." Anything not explicitly confirmed stays in draft status regardless of how complete it looks below.

---

### Proposed metric 1: Total reimbursement per beneficiary

**Hypothesis:** `MEDREIMB_IP + MEDREIMB_OP + MEDREIMB_CAR` from the beneficiary table, per `DESYNPUF_ID`, represents that beneficiary's total 2008 Medicare reimbursement.

**Confidence:** High. These are CMS-supplied pre-aggregated fields, not something we're deriving ourselves.

**Confirm or correct:**
- Does "total reimbursement" need to include Part D (prescription drug events)? Currently out of scope — confirm that's acceptable for this demo, not an oversight.
- Is single-year (2008) scope sufficient, or does the intended use case need multi-year totals?

---

### Proposed metric 2: Inpatient admission rate

**Hypothesis:** `COUNT(DISTINCT DESYNPUF_ID with ≥1 inpatient claim) / COUNT(DISTINCT DESYNPUF_ID in beneficiary) × 100`

**Confidence:** Medium. The calculation is simple, but the definition embeds a scoping choice.

**Confirm or correct:**
- This treats a beneficiary with 5 admissions the same as one with 1 admission (both count once). Is that the intended meaning of "admission rate," or is a volume metric (admissions per beneficiary) also needed alongside it?

---

### Proposed metric 3: Average length of stay

**Hypothesis (revised):** `AVG(CLM_UTLZTN_DAY_CNT)` across inpatient claims — using the CMS-supplied field as authoritative, not raw discharge-minus-admission date arithmetic.

**Confidence:** Medium-high, upgraded from low-medium based on verification evidence below.

**Verification evidence** (n=1,162 inpatient claims, no rows excluded — all had complete admission date, discharge date, and day count):

| | Count |
|---|---|
| Exact match to computed calendar days | 1,107 (95.3%) |
| Mismatch | 55 (4.7%) |

The mismatch pattern is not random noise — it's mostly explained by a real definitional difference. The largest mismatch bucket (delta = −1, 18 claims) is same-day admission/discharge, where calendar diff = 0 but `CLM_UTLZTN_DAY_CNT` = 1, consistent with CMS counting a same-day stay as 1 utilization day rather than 0. Most remaining mismatches are small (±1–4 days), consistent with `CLM_UTLZTN_DAY_CNT` reflecting covered benefit-period days rather than raw calendar span for longer or more complex stays.

Two outliers (deltas of −39 and −78 days) don't fit this pattern and remain unexplained — confirmed not an artifact of the load script's segment-aggregation logic (checked against raw CSV; both are single-segment claims), so the discrepancy exists in the source data itself. At 2 of 1,162 claims (0.17%), this is small enough to flag rather than block on.

**Decision:** `CLM_UTLZTN_DAY_CNT` is the correct field to use — it's a genuine CMS utilization concept, not a data-loading error, and now has evidence behind that claim rather than an assumption. **Recommend certifying with a caveat**: note in the certified definition that ~0.2% of claims show large unexplained deltas, and consider whether outlier exclusion or a documented tolerance band belongs in the calculation logic. This is a scoping decision for grounding, not a blocker.

**Confirm or correct:**
- Is a documented ~0.2% outlier rate acceptable to certify against, or should outlier claims be excluded/flagged in the metric's calculation logic itself?
- Grain question (multiple claims per stay) remains a separate, still-open item — see below.

---

### Proposed metric 4: Chronic condition prevalence

**Hypothesis:** `COUNT(WHERE SP_<condition> = 1) / COUNT(*) × 100`, computed per condition, across all 11 `SP_*` chronic condition flags (SP_ALZHDMTA, SP_CHF, SP_CHRNKIDN, SP_CNCR, SP_COPD, SP_DEPRESSN, SP_DIABETES, SP_ISCHMCHT, SP_OSTEOPRS, SP_RA_OA, SP_STRKETIA).

**Confidence:** High — **verified** against the official CMS DE-SynPUF codebook. `1` = "Yes" (has condition), `2` = "No" (does not have condition), confirmed for all 11 flags. This was previously a stated assumption; it's now a checked fact, not a working guess.

**Status: certifiable**, pending only the same interpretation caveat every chronic condition metric should carry: the codebook itself notes chronic condition flags were calculated using synthetic claims and, due to processing order, may not perfectly replicate what a from-scratch recalculation would produce — a data-generation caveat, not a coding-convention risk.

**Confirm or correct:**
- Condition scope resolved: all 11 flags in scope, not a curated subset.

---

### Proposed metric 5: Readmission rate

**Hypothesis (revised):** A readmission is any inpatient claim for a beneficiary whose `CLM_ADMSN_DT` falls within 30 days of a prior claim's `NCH_BENE_DSCHRG_DT` for that same `DESYNPUF_ID` — matching CMS's standard 30-day readmission window. Readmission rate = `COUNT(DISTINCT DESYNPUF_ID with ≥1 qualifying readmission) / COUNT(DISTINCT DESYNPUF_ID with ≥1 inpatient claim) × 100`.

**Confidence:** Medium-high on the windowing logic; **explicitly simplified** relative to the full CMS measure — see below.

**Scope decision, not a technicality:** The actual CMS 30-day readmission measure excludes "planned" readmissions — <cite index="29-1">scheduled procedures like obstetrical delivery, transplant surgery, maintenance chemotherapy, and rehabilitation don't count as readmissions even within the 30-day window</cite>, identified via a diagnosis/procedure code classification table (AHRQ CCS categories) this demo's data model does not currently include. Adding that exclusion is a real scope increase, not a minor detail.

**This proposal adopts the 30-day window but not the planned-readmission exclusion.** That means this metric should be labeled something like "30-day all-cause readmission rate (simplified, unplanned-only exclusion not applied)" rather than presented as CMS's official measure — an agent or user querying this metric needs to know it's CMS-inspired, not CMS-equivalent, or it risks being compared against published hospital readmission benchmarks it wasn't built to match.

**Confirm or correct:**
- Confirm the simplified (window-only) version is acceptable for demo scope, with the planned-exclusion gap named explicitly rather than silently absent.
- Denominator and multiple-readmission scoping questions from the original draft still apply (see below).
- Multiple readmissions: a beneficiary with 3 inpatient claims (2 readmissions) still counts once in the numerator, same as a beneficiary with exactly 2 claims (1 readmission). Confirm whether a rate metric or a volume metric (readmissions per admitted beneficiary) is more useful for the intended story.

---

## Cohort as a reporting dimension

Cohort membership is being added as a dimension that all five metrics above can be sliced by (e.g. "average reimbursement per beneficiary, by chronic condition cohort"), not just a standalone metric 4 concern.

**Modeling implication:** cohort membership is many-to-many, not many-to-one. A beneficiary can belong to multiple condition cohorts simultaneously (e.g. diabetes + CHF). This requires a bridge table (`BENEFICIARY_COHORT`) joining `beneficiary` to a `COHORT` dimension table — a beneficiary with 2 conditions produces 2 bridge rows, not a single row with 2 columns. Naively adding cohort as a column on `beneficiary` would force a one-cohort-per-beneficiary assumption that's false for this data.

**Cohort source:** the initial cohort set is grounded in CMS's Chronic Conditions Data Warehouse (CCW) methodology — the 11 `SP_*` flags in DE-SynPUF are a coarsened subset of CCW's original chronic condition indicator schema (21 conditions at CCW's 2006 launch, later expanded to 27, then 30 with ICD-10). Using CCW-derived cohorts gives external validation for the schema rather than an ad hoc grouping. The `COHORT` table's `SOURCE_SCHEMA` field exists specifically to preserve that provenance, in case custom (non-CCW) cohorts get added later — a query slicing "by cohort" should be able to distinguish federally-validated groupings from anything defined in-house.

**Confirm or correct:**
- Each metric definition above should be revisited to state whether it's reported at the population level, per-cohort, or both — this affects the query compiler stage's design, not just the metric's math.
- Does a beneficiary with zero flagged conditions get its own "no chronic condition" cohort for completeness, or does it simply not appear in `BENEFICIARY_COHORT` (implicit absence)? Worth deciding explicitly rather than leaving ambiguous.

---

## What this proposal does NOT include

Per demo scope discipline: no cross-year trending, no Part D/Carrier claims metrics, no drill-down by demographic slice beyond what's needed to support the metrics above. These are explicitly out of scope for this pass, not forgotten.

## Next step

This proposal is ready for a grounding session to resolve the remaining open items — claim-to-stay grain (metric 3) — and to confirm the scoping questions above. Metrics 1, 2, 3, and 4 could all reasonably move toward certification now (3 with the outlier caveat noted, 4 now fully verified against the official codebook); metric 5 is defined but should be labeled as CMS-inspired rather than CMS-equivalent. The cohort bridge table is a structural addition that all five metrics need to account for before the query compiler stage.
