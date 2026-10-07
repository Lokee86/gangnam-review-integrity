# Gangnam Beauty Guide — Review Integrity Explorer

A small product prototype for surfacing likely syndicated or duplicated cosmetic-procedure reviews.

The explorer compares **90 observed review summaries** from a Gangnam Beauty Guide snapshot against an estimated **44 underlying review experiences**, with ambiguous multi-record components explicitly flagged for manual review.

## What it does

- normalizes procedure language with a deterministic procedure taxonomy
- embeds review summaries with Qwen3 Embedding 8B at 1024 dimensions
- links same-clinic candidate pairs with Splink using:
  - embedding cosine similarity
  - Jaro-Winkler text similarity
  - review date
  - rating
  - normalized procedure signature
- clusters accepted duplicate edges into estimated underlying experiences
- exposes raw-vs-estimated-unique counts, clinic filtering, search, review clusters, and pairwise linkage evidence

## Calibration snapshot

The current evaluation set contains 493 same-clinic candidate pairs:

- 45 manually adjudicated likely duplicate pairs
- 448 manually adjudicated non-duplicate pairs

Procedure-aware Splink calibration-set performance:

- precision: **91.7%**
- recall: **97.8%**
- F1: **0.946**
- ROC-AUC: **0.999**
- average precision: **0.991**

These are calibration-set metrics, not held-out generalization results. The labels are used to select the operating threshold.

## Important caveat

The source records are AI-translated/AI-generated summaries exposed by Gangnam Beauty Guide and attributed there to GangnamUnni. Duplicate clusters are model estimates of likely repeated or syndicated review experiences, **not verified patient identities**.

Two larger connected components are intentionally marked `needs_review` because transitive linkage can overmerge otherwise distinct reviews.

## Run locally

Frontend:

```powershell
npm install
npm run dev
```

Production build:

```powershell
npm run build
```

Rebuild the static product export:

```powershell
uv run --no-project --python .venv\Scripts\python.exe python scripts\build_review_integrity_export.py
```

The frontend consumes `data/product/review-integrity.json` directly, so the deployed demo has no live Python service or API dependency.
