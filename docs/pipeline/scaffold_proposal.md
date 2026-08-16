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

**Confidence:** High, upgraded from medium based on verification evidence below.

**Verification evidence** (all 11 `SP_*` flags, n=2,000 beneficiaries, no rows excluded — every flag fully populated):

- Every flag contains only `1`/`2` across all 2,000 beneficiaries; **0 nulls**, no codes outside `1`/`2` anywhere.
- Coding convention (`1` = has condition, `2` = does not) confirmed against ResDAC's official CMS documentation for this CCW-derived flag family, which states directly (for the heart-failure flag): *"Equals 1 if beneficiary has Heart Failure."* Not a verbatim CMS PDF codebook quote — PDF table-cell text extraction wasn't reliable in this environment — but corroborated by an authoritative CMS-adjacent source rather than left as a bare assumption.
- Per-flag prevalence counts (e.g. SP_DIABETES 763/2,000 = 38.2%, SP_CHF 606/2,000 = 30.3%, SP_CNCR 142/2,000 = 7.1%) are in a plausible range for a Medicare population and show no sign of an inverted coding convention (e.g. diabetes/ischemic heart disease prevalence well above cancer prevalence, as expected).

**Status: coding convention resolved — ready to move toward certification.** The load-bearing assumption this metric depended on is no longer an assumption.

**Confirm or correct:**
- Condition scope resolved: all 11 flags in scope, not a curated subset.
- No remaining open items specific to this metric; general certification review (e.g. confirming the query logic itself) is still worthwhile before formal sign-off.

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

This proposal is ready for a grounding session to resolve the remaining open items — claim-to-stay grain (metric 3), the readmission windowing decision (metric 5, resolved to 30-day window without planned-exclusion), and cohort dimension scoping (per-cohort vs. population-level reporting for each metric, plus the residual-category decision). Chronic condition coding convention (metric 4) is now resolved, not just assumed — see verification evidence above. Metrics 1, 2, and 4 could reasonably move toward certification now; metric 3 needs the outlier caveat noted and the claim-to-stay grain question resolved first; metric 5 is defined but should be labeled as CMS-inspired rather than CMS-equivalent. The cohort bridge table is a structural addition that all five metrics need to account for before the query compiler stage.
