# Assessment Submission Checklist

## Ready now

- [x] Public product URL:
  https://lokee86.github.io/gangnam-review-integrity/
- [x] Public repository:
  https://github.com/Lokee86/gangnam-review-integrity
- [x] Production build passes
- [x] GitHub Pages deployment passes
- [x] Public URL verified HTTP 200
- [x] README explains architecture, calibration, and caveats
- [x] Paste-ready approach drafted
- [x] Paste-ready reflection drafted
- [x] Likely-question answer bank drafted
- [x] Final repo clean and pushed

## Core numbers

- 90 observed review records
- 44 model-estimated underlying experiences
- 46 estimated redundant/syndicated records
- 42 multi-record clusters
- 2 singleton reviews
- 2 larger components flagged for manual review

Calibration set:

- 493 same-clinic candidate pairs
- 45 manually adjudicated likely duplicate pairs
- 448 non-duplicate pairs

Procedure-aware Splink model:

- precision 91.7%
- recall 97.8%
- F1 0.946
- ROC-AUC 0.999
- average precision 0.991

## Technical stack

- React + TypeScript + Vite frontend
- static JSON product export
- Python data/linkage pipeline
- Splink 5
- DuckDB
- Qwen3 Embedding 8B via OpenRouter
- deterministic procedure normalization
- GitHub Pages deployment

## Important wording

Use:

- "model-estimated underlying experiences"
- "likely duplicate/syndicated review records"
- "manually adjudicated likely duplicate pairs"
- "calibration-set metrics"
- "translated/AI-generated summaries exposed by Gangnam Beauty Guide"

Avoid:

- claiming verified patient identity
- calling the metrics held-out/generalization performance
- implying the source text is original Korean review text
- claiming multi-source production ingestion is already implemented

## Still requires the live assessment

- actual 8 questions
- any word/character limits
- final submission action
- any assessment-specific request for process/timing details

Once the question text is visible, map each question to the answer bank rather than rewriting from scratch.
