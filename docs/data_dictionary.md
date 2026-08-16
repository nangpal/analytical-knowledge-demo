# Data dictionary — CMS DE-SynPUF demo island

Scope: only the fields used in the current entity model and the four confirmed metric definitions. Source: CMS DE-SynPUF Sample 1, 2008.

Status legend: **Confirmed** = verified against CMS documentation. **Assumed** = working assumption, not yet validated. **Open** = explicit verification item.

\* = verified against loaded data plus secondary CMS-adjacent sources (DDI/XML-derived metadata for this file, or ResDAC's official variable documentation); not a verbatim quote from the CMS PDF codebook table (PDF table-cell text extraction was not reliable in this environment).

---

## beneficiary
*Grain: one row per beneficiary per calendar year (2008 file loaded).*

| Field | Meaning | Status |
|---|---|---|
| `DESYNPUF_ID` | Synthetic unique identifier for a beneficiary. Primary key of this table; foreign key on claims tables. | Confirmed |
| `BENE_BIRTH_DT` | Date of birth (YYYYMMDD). | Confirmed |
| `BENE_DEATH_DT` | Date of death, if applicable. Null = alive at end of observation period. | Confirmed |
| `BENE_SEX_IDENT_CD` | Beneficiary sex. `1` = Male, `2` = Female. Loaded data contains only these two values (897 `1` / 1,103 `2` of 2,000), no nulls or other codes. | Confirmed\* |
| `BENE_ESRD_IND` | End-stage renal disease indicator. `0` = does not have ESRD, `Y` = has ESRD. Loaded data contains only these two values (1,853 `0` / 147 `Y` of 2,000), no nulls or other codes. 147/2,000 = 7.35% ESRD prevalence, consistent with published DE-SynPUF-wide rates (~7%). | Confirmed\* |
| `SP_DIABETES`, `SP_CHF`, `SP_CNCR`, `SP_COPD`, etc. (11 flags total: also `SP_ALZHDMTA`, `SP_CHRNKIDN`, `SP_DEPRESSN`, `SP_ISCHMCHT`, `SP_OSTEOPRS`, `SP_RA_OA`, `SP_STRKETIA`) | Chronic condition indicator flags. `1` = has condition, `2` = does not. Verified against loaded data: all 11 flags contain only `1`/`2` across all 2,000 beneficiaries, 0 nulls, no other codes. Cross-referenced against ResDAC's official documentation for this CCW-derived flag family, which states directly (for the heart-failure flag): "Equals 1 if beneficiary has Heart Failure" — confirming `1` = has condition. | Confirmed\* |
| `MEDREIMB_IP` | Total Medicare inpatient reimbursement for the beneficiary, summed across all inpatient claims in the year. Pre-aggregated by CMS — not derived from raw claim amounts in this table. | Confirmed |
| `MEDREIMB_OP` | Total Medicare outpatient reimbursement, same aggregation logic as above. | Confirmed |
| `MEDREIMB_CAR` | Total Medicare carrier (Part B physician/supplier) reimbursement. | Confirmed |

**Feeds metrics:** Total reimbursement per beneficiary (1), Chronic condition prevalence (4)

---

## inpatient_claims
*Grain: one row per inpatient claim.* In the real Medicare data this file's structure mirrors, over 99% of hospital stays produce exactly one claim, but a small minority produce multiple claims for a single stay — identifiable by matching beneficiary ID, admission date, and provider number (source: ResDAC guidance on Medicare inpatient files). Whether this same near-1:1 pattern holds in the *synthetic* DE-SynPUF data specifically has not been separately confirmed — see open item 3 below.

| Field | Meaning | Status |
|---|---|---|
| `DESYNPUF_ID` | Foreign key to `beneficiary`. Not unique in this table — a beneficiary can have many claims. | Confirmed |
| `CLM_ID` | Unique claim identifier. Primary key of this table. | Confirmed |
| `CLM_ADMSN_DT` | Hospital admission date. | Confirmed |
| `NCH_BENE_DSCHRG_DT` | Hospital discharge date. | Confirmed |
| `CLM_UTLZTN_DAY_CNT` | CMS-supplied length-of-stay in days. Cross-checked against `NCH_BENE_DSCHRG_DT − CLM_ADMSN_DT` calendar-day arithmetic across all 1,162 loaded inpatient claims: 95.3% exact match (1,107/1,162). The remaining 4.7% (55 claims) mismatch mostly by ±1–4 days — the single most common pattern (18 claims) is same-day admission/discharge, where calendar diff is 0 but the field reads 1, consistent with CMS counting a same-day stay as 1 utilization day. Two outliers (deltas of −39 and −78 days) look like genuine noise in the synthetic data rather than a loading defect — both traced to single-segment source rows, ruling out an artifact of this project's claim-segment aggregation. | Confirmed |
| `CLM_PMT_AMT` | Amount Medicare paid on this specific claim. | Confirmed |
| `ICD9_DGNS_CD_1` | Primary diagnosis code (ICD-9) for the claim. CMS provides up to 10 diagnosis code slots per claim; only the primary is modeled in this demo scope. | Assumed (scope decision, not a data-meaning question) |

**Feeds metrics:** Inpatient admission rate (2), Average length of stay (3)

---

## outpatient_claims
*Grain: one row per outpatient visit/claim.*

| Field | Meaning | Status |
|---|---|---|
| `DESYNPUF_ID` | Foreign key to `beneficiary`. | Confirmed |
| `CLM_ID` | Unique claim identifier. Primary key of this table. | Confirmed |
| `CLM_FROM_DT` / `CLM_THRU_DT` | Service date range for the outpatient claim (no separate admission/discharge concept, unlike inpatient). | Confirmed |
| `CLM_PMT_AMT` | Amount Medicare paid on this claim. | Confirmed |
| `ICD9_DGNS_CD_1` | Primary diagnosis code. Same scope decision as inpatient — only primary modeled. | Assumed (scope decision) |

---

## Conditional and sparse fields

Some fields in this dataset are not simply "populated or missing" — their presence or absence carries meaning tied to claim type or coverage type. Treating them as ordinary nullable fields (e.g. averaging over them, or counting non-null as "has value") can produce misleading results if that structure isn't accounted for.

| Pattern | Example fields | What sparsity means here |
|---|---|---|
| Multi-slot repeating fields | `HCPCS_CD_1`...`_45` (procedure codes), `ICD9_DGNS_CD_2`...`_10` (secondary diagnoses) | Slot count reflects how many distinct codes were billed on that specific claim — not a fixed schema. Most slots are empty by design, not by data-quality failure. `_1` fields are far more reliably present than higher-numbered slots. |
| Claim-type-specific fields | `CLM_DRG_CD`, `ADMTNG_ICD9_DGNS_CD`, `NCH_BENE_IP_DDCTBL_AMT` (inpatient-only concepts) | Structurally not applicable to outpatient claims — absence here isn't "missing data," it's "this concept doesn't exist for this claim type." Modeling these fields in a shared/unified claims table (if that's ever done) would need explicit type-conditional logic, not a blanket null check. |
| Coverage-type-conditional fields | `BENE_HMO_CVRAGE_TOT_MONS` | Only meaningful for beneficiaries enrolled in a Part C/HMO plan. A value of zero may mean "not enrolled in this plan type" rather than "enrolled with zero months of coverage" — these two states are easy to conflate in an aggregate. |

**Implication for metric definitions:** metrics that touch inpatient-specific or coverage-type-specific fields should state explicitly whether they're scoped to "beneficiaries/claims where this field applies" or "all beneficiaries/claims" — silently averaging across a mixed population where the field means different things in different rows is a common source of subtly wrong numbers.

## Open items to resolve before certifying metrics 3 and 4

1. ~~Chronic condition flag coding~~ — **Resolved.** See `SP_*` row above: `1`/`2` convention confirmed against ResDAC documentation and the loaded data (0 nulls, no codes outside `1`/`2` across all 11 flags).
2. ~~Length-of-stay validation~~ — **Resolved.** See `CLM_UTLZTN_DAY_CNT` row above: 95.3% exact match against calendar-day arithmetic, mismatches characterized and explained.
3. **Claim-to-stay grain** — check whether any `DESYNPUF_ID` + `CLM_ADMSN_DT` + `PRVDR_NUM` combination appears on more than one `CLM_ID` in the loaded data. If so, "average length of stay" as currently calculated (one row = one claim) may double-count or fragment a small number of actual hospital stays.

Metric 4 (chronic condition prevalence) can now move toward certification — its load-bearing coding-convention assumption (item 1) is resolved. Metric 3 (average length of stay) remains **draft, not certified**, pending item 3 — the claim-to-stay grain question is still untouched even though the day-count field itself (item 2) is resolved. This is consistent with the platform's labeled-not-gated certification principle: visible and usable, but explicitly flagged as unverified rather than silently trusted until fully resolved.
