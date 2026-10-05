# Splink baseline — GBG review duplicate linkage

## Dataset

- 90 observed review summaries
- exact `clinic_id` blocking
- 493 same-clinic candidate pairs
- 45 manually labelled duplicate pairs
- 448 manually labelled non-duplicate pairs
- Qwen3 Embedding 8B, 1024 dimensions, L2-normalized

Ground-truth labels are **not** used to estimate Splink model parameters. They are used to
select/report the decision threshold, so the metrics below are calibration-set metrics rather
than a held-out estimate of generalization.

## Models

### Raw embedding cosine

A single continuous cosine threshold on the Qwen vectors.

- best threshold: 0.8794485
- precision: 0.900
- recall: 0.800
- F1: 0.847
- ROC-AUC: 0.979
- average precision: 0.899
- 36 TP / 4 FP / 9 FN
- 52 predicted unique clusters (38 redundant records)

### Splink cosine-only

Splink 5 with:

- exact `clinic_id` blocking
- cosine comparison levels at 0.97 / 0.94 / 0.91 / 0.88 / 0.85 / 0.80 / 0.70
- `u` estimated from random record pairs
- `m` estimated by expectation-maximization
- fixed prior match probability of 0.01

Results:

- precision: 0.895
- recall: 0.756
- F1: 0.819
- ROC-AUC: 0.974
- average precision: 0.874
- 34 TP / 4 FP / 11 FN

This is intentionally expected not to beat raw cosine: one discretized signal cannot add
ranking information that was not already present in the continuous cosine score.

### Splink augmented

The same model plus:

- Jaro-Winkler levels over `summary_text`
- exact `rating` agreement
- exact `review_date` agreement

Results:

- best calibrated match-probability threshold: 0.7483212
- precision: **0.971**
- recall: **0.756**
- F1: **0.850**
- ROC-AUC: **0.989**
- average precision: **0.933**
- 34 TP / 1 FP / 11 FN
- 55 predicted unique clusters (35 redundant records)

The added evidence removes three of the four cosine-only false positives while preserving the
same true-positive count. It materially improves ranking quality (ROC-AUC/AP) and precision,
but does not recover the hardest low-cosine paraphrases.

## Error interpretation

The remaining false negatives are not primarily a threshold problem. Several manually
adjudicated duplicate pairs have unusually low embedding similarity despite matching procedure,
recovery timeline, and distinctive details. The two medium-confidence human labels are among
the difficult cases.

This is the point at which procedure/entity features become justified. The next experiment
should add a small deterministic/structured procedure representation (and, if available,
surgeon identity) rather than adding more generic text-distance functions.

## Reproduction

Run:

```powershell
uv run --no-project --python .venv\Scripts\python.exe python scripts\run_splink_baseline.py
```

Outputs are under `data/linkage/baseline/`:

- `report.json`
- raw-cosine pair scores
- both trained Splink model JSON files
- both prediction Parquet files
- `errors.csv`
