# Review linkage schema

## Goal

Represent each observed review as one flat record that can be registered directly with
DuckDB/Splink, while keeping provenance and derived linkage features explicit.

The schema deliberately does **not** try to model the entire Gangnam Beauty Guide domain. It
contains only fields useful for provenance, blocking, linkage, or presentation.

## Linkage record

| Field | Type | Required | Role |
| --- | --- | --- | --- |
| `unique_id` | string | yes | Globally unique observed-record ID. Uses Splink's default ID name. |
| `source_dataset` | string | yes | Snapshot/dataset identity. Kept explicit for future multi-source linkage. |
| `ingest_source` | string | yes | Site/system actually ingested from, currently `gangnambeautyguide`. |
| `upstream_source` | string | no | Source attributed by the ingest source, currently `GangnamUnni`. |
| `source_url` | string | yes | URL from which this observed record was captured. |
| `source_ordinal` | int32 | yes | Position in the captured source; provenance/debugging only. |
| `captured_on` | date | yes | Snapshot capture date. |
| `content_kind` | string | yes | Current value: `ai_translated_summary`. |
| `language` | string | yes | Language of `summary_text`; currently `en`. |
| `clinic_id` | string | yes | Normalized clinic key. Primary blocking field. |
| `clinic_name` | string | yes | Display name as exposed by the ingest source. |
| `review_date` | date | no | Date exposed for the review by the ingest source. |
| `rating` | float32 | no | Exposed review rating. |
| `procedures` | string[] | yes | Deterministically extracted detailed canonical procedure tags. |
| `primary_procedure` | string | no | Most informative extracted procedure for presentation/debugging. |
| `revision` | bool | yes | Whether the summary explicitly identifies a revision/third operation. |
| `procedure_signature` | string | no | Normalized procedure identity used as linkage evidence. |
| `summary_text` | string | yes | Captured English review summary. |
| `summary_embedding` | float32[1024] | no | Fixed-size Qwen3 embedding. Fixed width is required by DuckDB `array_cosine_similarity`. |

## Current Splink use

The current procedure-aware model uses:

- **blocking:** exact `clinic_id`
- Qwen embedding cosine similarity
- Jaro-Winkler similarity on `summary_text`
- exact `rating` agreement
- exact `review_date` agreement
- term-frequency-adjusted exact `procedure_signature` agreement

The procedure signature is derived deterministically from the summary. Detailed procedure tags
are retained separately so normalization remains inspectable rather than destructive.

`source_dataset`, provenance fields, clinic display name, capture date, and `revision` are
not currently model evidence.

## Important provenance distinction

The current GBG snapshot contains translated AI-generated summaries of reviews, not original
source review text. The schema therefore uses `summary_text` and explicitly marks
`content_kind=ai_translated_summary`; it does not treat the captured text as a verbatim
patient review.

`ingest_source` and `upstream_source` are separate because the records were captured from
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

## Still deliberately omitted

Do not add these until there is evidence they improve linkage:

- surgeon identity
- price extraction
- recovery-duration extraction
- complications/outcome fields
- general LLM-extracted entities
- hand-written similarity weights
