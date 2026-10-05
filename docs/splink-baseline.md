# Splink baseline — GBG review duplicate linkage

## Dataset

- 90 observed review summaries
- exact `clinic_id` blocking
- 493 same-clinic candidate pairs
- 45 manually labelled duplicate pairs
- 448 manually labelled non-duplicate pairs
- Qwen3 Embedding 8B, 1024 dimensions, L2-normalized
- deterministic procedure extraction from `summary_text`

Ground-truth labels are **not** used to estimate Splink model parameters. They are used to
select/report the decision threshold, so the metrics below are calibration-set metrics rather
than a held-out estimate of generalization.

## Models

| Model | Precision | Recall | F1 | ROC-AUC | Average precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw Qwen cosine | 0.900 | 0.800 | 0.847 | 0.979 | 0.899 |
| Splink cosine-only | 0.895 | 0.756 | 0.819 | 0.974 | 0.874 |
| Splink + lexical/date/rating | **0.971** | 0.756 | 0.850 | 0.989 | 0.933 |
| **Splink + procedure signature** | 0.917 | **0.978** | **0.946** | **0.999** | **0.991** |

## Procedure-aware model

The current best model uses:

- exact `clinic_id` blocking
- Qwen cosine comparison levels
- Jaro-Winkler levels over `summary_text`
- exact `rating` agreement
- exact `review_date` agreement
- term-frequency-adjusted exact agreement on normalized `procedure_signature`
- `u` estimated from random record pairs
- `m` estimated by expectation-maximization
- fixed prior match probability of 0.01

Calibration-set result:

- precision: **0.917**
- recall: **0.978**
- F1: **0.946**
- ROC-AUC: **0.999**
- average precision: **0.991**
- 44 TP / 4 FP / 1 FN
- 44 predicted connected-component clusters

The procedure signature itself agrees for all 45 manually adjudicated duplicate pairs, but it
also agrees for 40 of the 448 non-duplicate same-clinic pairs. It is therefore treated as
probabilistic evidence rather than a duplicate rule.

## Remaining errors

The single false negative is the medium-confidence Chai pair describing a posterior/lower
eye-corner operation with materially different paraphrasing. It has the same normalized
procedure signature, date, and rating, but unusually weak text/embedding similarity.

The four false positives are same-clinic reviews where procedure, date, and rating also agree.
They are concentrated in repeated eyelid/ptosis procedures at View and Pop, so further gains
would require evidence that distinguishes individual patient experiences rather than broader
procedure taxonomy.

This is a good stopping point for procedure extraction. Adding more procedure categories would
mostly make the taxonomy more detailed without addressing the remaining ambiguity.

## Reproduction

Run:

```powershell
uv run --no-project --python .venv\Scripts\python.exe python scripts\run_splink_baseline.py
```

Outputs under `data/linkage/baseline/`:

- `report.json`
- `errors.csv`
- `raw-cosine-pairs.parquet`
- `splink-cosine-model.json`
- `splink-cosine-predictions.parquet`
- `splink-augmented-model.json`
- `splink-augmented-predictions.parquet`
- `splink-procedure-model.json`
- `splink-procedure-predictions.parquet`

Procedure extraction audit:

- `data/linkage/procedure-extraction-report.json`
- `docs/procedure-extraction.md`
