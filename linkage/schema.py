from __future__ import annotations

import pyarrow as pa

EMBEDDING_DIMENSIONS = 1024

# One flat row per observed review record. Keep this aligned with Splink's
# default unique_id/source_dataset conventions so the adapter needs minimal
# custom configuration. The embedding is a fixed-size array because DuckDB's
# array_cosine_similarity() requires ARRAY rather than a variable-length LIST.
LINKAGE_RECORD_SCHEMA = pa.schema(
    [
        pa.field("unique_id", pa.string(), nullable=False),
        pa.field("source_dataset", pa.string(), nullable=False),
        pa.field("ingest_source", pa.string(), nullable=False),
        pa.field("upstream_source", pa.string(), nullable=True),
        pa.field("source_url", pa.string(), nullable=False),
        pa.field("source_ordinal", pa.int32(), nullable=False),
        pa.field("captured_on", pa.date32(), nullable=False),
        pa.field("content_kind", pa.string(), nullable=False),
        pa.field("language", pa.string(), nullable=False),
        pa.field("clinic_id", pa.string(), nullable=False),
        pa.field("clinic_name", pa.string(), nullable=False),
        pa.field("review_date", pa.date32(), nullable=True),
        pa.field("rating", pa.float32(), nullable=True),
        pa.field("procedures", pa.list_(pa.string()), nullable=False),
        pa.field("primary_procedure", pa.string(), nullable=True),
        pa.field("revision", pa.bool_(), nullable=False),
        pa.field("procedure_signature", pa.string(), nullable=True),
        pa.field("summary_text", pa.string(), nullable=False),
        pa.field(
            "summary_embedding",
            pa.list_(pa.float32(), list_size=EMBEDDING_DIMENSIONS),
            nullable=True,
        ),
    ]
)

# Evaluation labels are kept separate from linkage input to prevent accidental
# ground-truth leakage into the model.
PAIR_LABEL_SCHEMA = pa.schema(
    [
        pa.field("source_dataset_l", pa.string(), nullable=False),
        pa.field("unique_id_l", pa.string(), nullable=False),
        pa.field("source_dataset_r", pa.string(), nullable=False),
        pa.field("unique_id_r", pa.string(), nullable=False),
        pa.field("label", pa.string(), nullable=False),
        pa.field("confidence", pa.string(), nullable=False),
        pa.field("duplicate_cluster_id", pa.string(), nullable=True),
        pa.field("rationale", pa.string(), nullable=False),
    ]
)


REQUIRED_CONTENT_KINDS = {"ai_translated_summary"}
SUPPORTED_LANGUAGES = {"en"}


def validate_linkage_table(table: pa.Table) -> None:
    if table.schema != LINKAGE_RECORD_SCHEMA:
        raise ValueError(
            "Linkage table schema mismatch.\n"
            f"Expected: {LINKAGE_RECORD_SCHEMA}\n"
            f"Actual:   {table.schema}"
        )

    ids = table.column("unique_id").to_pylist()
    if len(ids) != len(set(ids)):
        raise ValueError("unique_id values must be globally unique")

    if any(not value.strip() for value in table.column("clinic_id").to_pylist()):
        raise ValueError("clinic_id must be non-empty")

    if any(not value.strip() for value in table.column("summary_text").to_pylist()):
        raise ValueError("summary_text must be non-empty")

    content_kinds = set(table.column("content_kind").to_pylist())
    if not content_kinds <= REQUIRED_CONTENT_KINDS:
        raise ValueError(f"Unsupported content_kind values: {sorted(content_kinds)}")

    languages = set(table.column("language").to_pylist())
    if not languages <= SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language values: {sorted(languages)}")

    embeddings = table.column("summary_embedding").to_pylist()
    invalid_lengths = sorted(
        {len(vector) for vector in embeddings if vector is not None and len(vector) != EMBEDDING_DIMENSIONS}
    )
    if invalid_lengths:
        raise ValueError(
            f"summary_embedding must contain {EMBEDDING_DIMENSIONS} values; "
            f"invalid lengths: {invalid_lengths}"
        )
