# Domaining stage — conditional/sparse field detection

**Origin:** Observed while domaining the DE-SynPUF island (inpatient-only fields, multi-slot procedure/diagnosis codes, coverage-type-conditional fields — see `data_dictionary.md`).

## Checklist item

During domaining, for each new island's sample data, check whether any fields are **conditionally populated** based on a type or category value elsewhere in the record — rather than simply present-or-missing at random.

Look for:
- Fields that only make sense for one subtype of record within a shared table (e.g. inpatient-only fields sitting in a claims table that also holds outpatient rows)
- Repeating/multi-slot fields where slot count varies by record rather than following a fixed schema
- Fields whose zero/null value is ambiguous between "not applicable" and "applicable but zero"

If found: flag explicitly in that island's data dictionary, and require any metric touching those fields to state its population scope (e.g. "claims where X applies" vs. "all claims") rather than aggregating silently across a mixed population.

## Representativeness caveat

This checklist item was derived from patterns observed in **one sample of one island** (DE-SynPUF Sample 1). Absence of this pattern in a future island's sample data is not evidence the island lacks conditional fields — it may only mean the sample didn't surface them. This checklist item should be treated as "one known failure mode to actively check for," not an exhaustive detection method, and should be revisited/expanded as more islands are domained and new sparsity patterns are observed.
