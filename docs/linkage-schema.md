# Review linkage schema

## Goal

Represent each observed review as one flat record that can be registered directly with
DuckDB/Splink, while keeping provenance and model-derived features explicit.

The schema deliberately does **not** try to model the entire Gangnam Beauty Guide domain.
It contains only fields that are useful for provenance, blocking, linkage, or presentation.

## Linkage record

| Field | Type | Required | Role |
| --- | --- | --- | --- |
| `unique_id` | string | yes | Globally unique observed-record ID. Uses Splink's default ID name. |
| `source_dataset` | string | yes | Snapshot/dataset identity. Kept explicit for future multi-source linkage. |
| `ingest_source` | string | yes | Site/system we actually ingested from, e.g. `gangnambeautyguide`. |
| `upstream_source` | string | no | Source attributed by the ingest source, e.g. `GangnamUnni`. |
| `source_url` | string | yes | URL from which this observed record was captured. |
| `source_ordinal` | int32 | yes | Position in the captured source; provenance/debugging only. |
| `captured_on` | date | yes | Snapshot capture date. |
| `content_kind` | string | yes | What the text actually is. Current value: `ai_translated_summary`. |
| `language` | string | yes | Language of `summary_text`; currently `en`. |
| `clinic_id` | string | yes | Normalized clinic key. Primary blocking field. |
| `clinic_name` | string | yes | Display name as exposed by the ingest source. |
| `review_date` | date | no | Date exposed for the review by the ingest source. |
| `rating` | float32 | no | Exposed rating, preserving half-star values. |
| `reviewer_initial` | string | no | Display/provenance field. Not expected to carry useful linkage evidence. |
| `summary_text` | string | yes | The captured English review summary. |
| `summary_embedding` | float32[1024] | no | Fixed-size Qwen3 embedding used for semantic comparison. Fixed width is required by DuckDB `array_cosine_similarity`; null until embeddings are generated. |

## Current Splink use

The current baseline uses:

- **blocking:** exact `clinic_id`
- **primary comparison:** cosine similarity on `summary_embedding`
- **secondary comparisons:** Jaro-Winkler similarity on `summary_text`, exact rating agreement, and exact review-date agreement; calibration showed these substantially reduce false positives

`source_dataset`, provenance fields, clinic display name, reviewer initial, and capture date are
not model evidence.

## Important provenance distinction

The current GBG snapshot contains translated AI-generated summaries of reviews, not the
original source review text. The schema therefore uses `summary_text` and explicitly marks
`content_kind=ai_translated_summary`; it does not pretend the captured text is a verbatim
patient review.

`ingest_source` and `upstream_source` are separate because we captured the records from
Gangnam Beauty Guide while GBG attributes them to GangnamUnni.

## Ground truth is separate

Human duplicate labels must never be columns in the production linkage table. Evaluation uses
a separate pair-label contract:

- `source_dataset_l`
- `unique_id_l`
- `source_dataset_r`
- `unique_id_r`
- `label` = `duplicate` or `non_duplicate`
- `confidence` = `high` or `medium`
- `duplicate_cluster_id` when applicable
- `rationale`

This prevents accidental target leakage and maps cleanly to Splink's pair-label conventions.

## Deliberately omitted for now

Do not add these until we have evidence they improve linkage:

- procedure taxonomy
- surgeon identity
- price extraction
- recovery-duration extraction
- complications/outcome fields
- LLM-extracted entities
- normalized summary copies
- hand-written similarity scores

Those can be derived later without changing the identity/provenance contract.