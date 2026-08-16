# Dimension definition process

Facts (metrics) already have a repeatable definition process: hypothesis → grain → calculation logic → confidence → confirm/correct → certify. Dimensions need the same structure — they've been handled ad hoc so far because cohort is the first one that came up. This is the template going forward.

## Template

For any proposed dimension:

1. **Membership hypothesis** — what rule determines whether a record belongs to a given value of this dimension? State it as explicitly as a metric's calculation logic.
2. **Grain** — what is the unit of membership? (Per-beneficiary, per-claim, per-encounter — dimensions can attach at different grains than the facts they'll slice.)
3. **Cardinality** — is membership single-valued (mutually exclusive, like sex or state) or multi-valued (a record can belong to several values at once, like cohort)? This determines whether the dimension is a plain column or needs a bridge table.
4. **Source and provenance** — is this dimension derived from an external, validated schema (like CCW), or defined in-house for this project? Both are legitimate, but they should never be indistinguishable downstream.
5. **Residual/null category** — what happens to a record that matches none of the dimension's defined values? Three options, and the choice must be explicit:
   - **Implicit absence** — the record simply doesn't appear in any membership row (works if "not present" is a meaningful, intended default for every fact that will ever slice by this dimension).
   - **Explicit residual category** (e.g. "no chronic condition") — the record gets its own membership row rather than silently vanishing. Needed whenever a slice-by-dimension query should be able to report a complete denominator (e.g. "average reimbursement, healthy vs. any chronic condition").
   - **Not applicable / excluded** — the dimension genuinely doesn't apply to some records (e.g. an outpatient-only dimension applied to a table with no outpatient claims), which is different from a beneficiary who simply has zero flagged conditions.
6. **Confirm or correct** — same spirit as the fact process: state what's still assumption vs. verified, and what a domain reviewer should sanity-check.

## Worked example: cohort dimension

1. **Membership hypothesis:** a beneficiary belongs to a condition cohort if their corresponding `SP_*` flag equals `1` (has condition). This coding convention is now **verified** — confirmed against ResDAC's official documentation for this CCW-derived flag family and against the loaded data (0 nulls, only `1`/`2` present across all 11 flags, all 2,000 beneficiaries) — so cohort membership can be computed as defined without an inherited open item.
2. **Grain:** per-beneficiary (not per-claim).
3. **Cardinality:** multi-valued — a beneficiary can belong to multiple condition cohorts simultaneously. Requires the `BENEFICIARY_COHORT` bridge table, not a column on `beneficiary`.
4. **Source and provenance:** CCW-derived (external, federally validated schema), tracked via `COHORT.SOURCE_SCHEMA` so future custom cohorts remain distinguishable from this one.
5. **Residual/null category:** **decision needed** — recommend an explicit residual category ("no flagged chronic condition") rather than implicit absence, specifically because metrics like "average reimbursement by cohort" lose their most useful comparison (healthy vs. any condition) if the zero-condition population silently disappears from the slice instead of appearing as its own row.
6. **Confirm or correct:**
   - Confirm the residual-category recommendation above, or override it with implicit absence if there's a reason the "no condition" population shouldn't be directly comparable.
   - Coding-convention question is resolved (see step 1) — this dimension no longer carries an inherited open item from metric 4.

## Why this matters beyond cohort

Future dimensions (geography via `SP_STATE_CODE`, coverage type via HMO enrollment, age bands) should go through this same six-step process rather than being added as convenient columns. The cardinality and residual-category steps in particular are where silent modeling mistakes tend to hide — they're easy to skip because the dimension "looks" simple until a fact actually gets sliced by it.
