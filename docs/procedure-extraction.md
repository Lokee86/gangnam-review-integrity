# Procedure extraction

## Purpose

Convert the procedure language in each GBG review summary into a small deterministic
representation that can be used as linkage evidence without adding another model call.

The extractor is intentionally dataset-scoped and auditable. It normalizes the procedure
language present in the current 90-review snapshot; it is not intended to be a complete
cosmetic-procedure ontology.

## Output

For each review, `linkage/procedures.py` derives:

- `procedures`: detailed canonical tags detected in the summary
- `primary_procedure`: the most informative detected procedure for presentation/debugging
- `revision`: whether the summary explicitly identifies a revision/third operation
- `procedure_signature`: normalized linkage signature

Example:

```json
{
  "procedures": ["epicanthoplasty", "eyelid_surgery", "ptosis_correction"],
  "primary_procedure": "ptosis_correction",
  "revision": false,
  "procedure_signature": "eye_corner_surgery|ptosis_correction"
}
```

The linkage signature intentionally differs from the raw tag list. Translation/summarization
can describe equivalent periocular procedures at different levels of specificity, so the
signature:

- collapses epicanthoplasty, lateral/lower canthoplasty and lower-eyelid/corner wording into
  `eye_corner_surgery`
- suppresses generic `eyelid_surgery` when a more specific eye-corner or ptosis procedure is
  present
- keeps `revision` separate rather than baking it into procedure identity

This preserves the auditable extraction while making the linkage representation less brittle
to paraphrase.

## Current coverage

On `gbg-reviews-2026-10-05`:

- 90 / 90 records receive at least one procedure
- 22 detailed canonical procedure types are represented by the rule vocabulary
- 11 records are marked as explicit revision procedures
- 45 / 45 manually adjudicated duplicate pairs have the same normalized procedure signature
- 40 / 448 manually adjudicated non-duplicate same-clinic pairs also share a signature

That last number is why procedure agreement is evidence rather than a deduplication rule by
itself.

The full audit is materialized in:

`data/linkage/procedure-extraction-report.json`

## Linkage effect

Adding term-frequency-adjusted exact agreement on `procedure_signature` to the existing
Splink model changes calibration-set performance from:

- F1 0.850
- precision 0.971
- recall 0.756
- ROC-AUC 0.989
- average precision 0.933

to:

- **F1 0.946**
- **precision 0.917**
- **recall 0.978**
- **ROC-AUC 0.999**
- **average precision 0.991**
- 44 TP / 4 FP / 1 FN

The procedure signal mainly recovers low-cosine paraphrases. The remaining false positives are
same-clinic, same-procedure, same-date/rating cases that still require the text/semantic
evidence to distinguish them.

These are calibration-set metrics: the 493 manual labels are used to choose the reporting
threshold, so they are not a held-out generalization estimate.
