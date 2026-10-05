from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from linkage.schema import LINKAGE_RECORD_SCHEMA, validate_linkage_table

SNAPSHOT = ROOT / "data" / "gbg-reviews-2026-10-05.json"
OUT = ROOT / "data" / "linkage" / "gbg-reviews-2026-10-05.parquet"
SOURCE_DATASET = "gbg-reviews-2026-10-05"

payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
captured_on = date.fromisoformat(payload["snapshot"]["captured_on"])

rows: list[dict[str, object]] = []
for review in payload["reviews"]:
    rows.append(
        {
            "unique_id": review["snapshot_id"],
            "source_dataset": SOURCE_DATASET,
            "ingest_source": "gangnambeautyguide",
            "upstream_source": review.get("source"),
            "source_url": review["snapshot_source_url"],
            "source_ordinal": int(review["ordinal"]),
            "captured_on": captured_on,
            "content_kind": "ai_translated_summary",
            "language": "en",
            "clinic_id": review["clinic_slug"],
            "clinic_name": review["clinic_name"],
            "review_date": (
                date.fromisoformat(review["review_date"])
                if review.get("review_date")
                else None
            ),
            "rating": (
                float(review["rating"])
                if review.get("rating") is not None
                else None
            ),
            "summary_text": review["summary"],
            "summary_embedding": None,
        }
    )

table = pa.Table.from_pylist(rows, schema=LINKAGE_RECORD_SCHEMA)
validate_linkage_table(table)

OUT.parent.mkdir(parents=True, exist_ok=True)
pq.write_table(table, OUT, compression="zstd")

print(f"Wrote {table.num_rows} linkage records to {OUT}")
print(table.schema)
