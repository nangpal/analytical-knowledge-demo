# Dimension definitions — batch 1

Six dimensions run through the dimension definition process. Two (sex, ESRD status) are close to direct field mappings. The other four each embed a real domain decision that needs a call, not just a derivation.

---

## Sex

1. **Membership hypothesis:** `BENE_SEX_IDENT_CD` maps directly to a sex category.
2. **Grain:** Beneficiary.
3. **Cardinality:** Single-valued.
4. **Source/provenance:** Direct CMS Beneficiary Summary field — internal source, no external schema.
5. **Residual/null:** Verified against loaded data — 0 nulls across all 2,000 beneficiaries; only `1`/`2` present (897 / 1,103), no residual category needed.
6. **Resolved:** Coding convention is `1` = Male, `2` = Female. Verified via the loaded data's value distribution (no nulls, no codes outside `1`/`2`) and corroborated by a secondary source that parsed the DE-SynPUF DDI/XML metadata for this file. Not a verbatim quote from the CMS PDF codebook table — PDF table-cell text extraction wasn't reliable in this environment (poppler failed to build here; a manual PDF-stream parser couldn't isolate the value-label table). Worth re-confirming against the literal PDF text if that tooling gap gets resolved later, but the convention matches the standard SSA/CMS sex-code scheme used throughout DE-SynPUF/CCW documentation.

---

## Age band

1. **Membership hypothesis:** Derived from `BENE_BIRTH_DT`, banded into ranges.
2. **Grain:** Beneficiary.
3. **Cardinality:** Single-valued.
4. **Source/provenance:** Derived, not from an external schema.
5. **Residual/null:** Missing birth date → explicit "unknown" band, not silent exclusion.
6. **Resolved:** Reference date is **January 1, 2008** — age is calculated as of the start of the observation year, not per-claim or year-end. Proposed bands (`<65`, `65–74`, `75–84`, `85+`) stand as confirmed; the `<65` band captures disability/ESRD-pathway beneficiaries who qualify for Medicare before standard eligibility age.

---

## State

1. **Membership hypothesis:** `SP_STATE_CODE` maps to a US state or territory.
2. **Grain:** Beneficiary.
3. **Cardinality:** Single-valued.
4. **Source/provenance:** SSA's standard state coding — confirmed via SSA POMS documentation (HI 01005.808), which lists three-digit codes (`010` = Alabama through `530` = Wyoming, plus territories like `400` = Puerto Rico, `650` = Guam). The beneficiary-level field in CMS data uses the two-digit form of this same scheme (three-digit code ÷ 10) — consistent with the loaded sample data, where `SP_STATE_CODE` values of `26` and `39` correctly correspond to Missouri (260) and Pennsylvania (390).
5. **Residual/null:** Invalid or unmapped code → explicit "unknown" state.
6. **Resolved:** Build the lookup table now. Source: SSA POMS HI 01005.808 (2-digit = 3-digit ÷ 10). Note two caveats worth carrying into the build: a few codes have historical/obsolete duplicate entries (e.g. Delaware `080` appears twice for different legacy programs), and several states are annotated "no current buy-in agreement" in the source table — that annotation is a Medicaid buy-in administrative note, not a data-quality flag, and shouldn't be treated as suspect data.

---

## Coverage type

1. **Membership hypothesis:** Beneficiary is categorized as "HMO/Part C" or "FFS" based on `BENE_HMO_CVRAGE_TOT_MONS`.
2. **Grain:** Beneficiary.
3. **Cardinality:** Single-valued (binary threshold, resolved below).
4. **Source/provenance:** Derived from coverage-month fields, no external schema.
5. **Residual/null:** None — the binary threshold rule forces every beneficiary into exactly one category, no residual needed.
6. **Resolved:** Binary threshold using majority-of-months. Beneficiary is "HMO/Part C" if `BENE_HMO_CVRAGE_TOT_MONS >= 7` (majority of the 12-month year), otherwise "FFS." Tie-break note: 6 months is not a majority under this rule and falls to "FFS" — worth confirming that default direction is acceptable, since a beneficiary with exactly 6/6 months split is a genuine edge case the threshold has to decide one way or the other.

---

## ESRD status

1. **Membership hypothesis:** `BENE_ESRD_IND` directly indicates end-stage renal disease status.
2. **Grain:** Beneficiary.
3. **Cardinality:** Single-valued (yes/no).
4. **Source/provenance:** Direct CMS field.
5. **Residual/null:** Verified against loaded data — 0 nulls across all 2,000 beneficiaries; only `0`/`Y` present (1,853 / 147), no residual category needed.
6. **Resolved:** Coding convention is `0` = does not have ESRD, `Y` = has ESRD (not `1`/`0` or `Y`/`N` as originally hypothesized). Verified via the loaded data's value distribution and corroborated by a secondary source that parsed the DE-SynPUF DDI/XML metadata for this file — same sourcing caveat as Sex above (not a verbatim CMS PDF quote). Resulting prevalence, 147/2,000 = 7.35%, is consistent with published DE-SynPUF-wide ESRD rates (~7%), a useful plausibility check independent of the codebook sourcing question.

---

## Mortality status

1. **Membership hypothesis:** Beneficiary is "deceased" if `BENE_DEATH_DT` is populated, "alive" otherwise (as of end of the 2008 observation window).
2. **Grain:** Beneficiary.
3. **Cardinality:** Single-valued (binary).
4. **Source/provenance:** Direct derivation from a CMS field.
5. **Residual/null:** None — binary and always determinate.
6. **Confirm or correct:**
   - **Interpretation caveat, not a data-quality issue:** slicing metrics like "average reimbursement" by mortality status will likely show elevated costs in the "deceased" group, reflecting the well-documented pattern of concentrated end-of-life healthcare spending in Medicare populations — not necessarily a data or modeling problem. Worth stating this explicitly wherever the dimension is used, so the number isn't misread as an anomaly.

---

## Summary of status

| Dimension | Status |
|---|---|
| Sex | Resolved — `1`=Male, `2`=Female, verified against loaded data (0 nulls) |
| ESRD status | Resolved — `0`=no ESRD, `Y`=has ESRD, verified against loaded data (0 nulls) |
| Mortality status | Ready — only needs the interpretation caveat documented |
| Age band | Resolved — Jan 1, 2008 reference date, bands `<65`/`65–74`/`75–84`/`85+` |
| State | Resolved — 2-digit SSA code (POMS HI 01005.808 ÷ 10), lookup table to be built |
| Coverage type | Resolved — binary threshold at `>=7` months HMO coverage |
