from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "gbg-reviews-2026-10-05.json"
CLUSTERS = ROOT / "data" / "ground-truth" / "gbg-review-duplicate-clusters-2026-10-05.json"
OUT = ROOT / "data" / "ground-truth" / "gbg-review-pair-labels-2026-10-05.csv"

snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
truth = json.loads(CLUSTERS.read_text(encoding="utf-8"))
records = {record["snapshot_id"]: record for record in snapshot["reviews"]}

cluster_for: dict[str, dict] = {}
for cluster in truth["clusters"]:
    for record_id in cluster["record_ids"]:
        if record_id in cluster_for:
            raise SystemExit(f"Record appears in multiple clusters: {record_id}")
        cluster_for[record_id] = cluster

missing = sorted(set(records) - set(cluster_for))
extra = sorted(set(cluster_for) - set(records))
if missing or extra:
    raise SystemExit(f"Cluster coverage mismatch. missing={missing} extra={extra}")

rows: list[dict[str, object]] = []
ids = sorted(records)

for left_index, left_id in enumerate(ids):
    left = records[left_id]
    for right_id in ids[left_index + 1 :]:
        right = records[right_id]

        # Keep the calibration set intentionally hard: compare only records from
        # the same clinic. Cross-clinic pairs are trivial negatives and would
        # make aggregate metrics look artificially good.
        if left["clinic_slug"] != right["clinic_slug"]:
            continue

        same_cluster = cluster_for[left_id]["cluster_id"] == cluster_for[right_id]["cluster_id"]
        if same_cluster:
            cluster = cluster_for[left_id]
            label = "duplicate"
            confidence = cluster["confidence"]
            rationale = cluster["rationale"]
            cluster_id = cluster["cluster_id"]
        else:
            label = "non_duplicate"
            confidence = "high"
            rationale = "Different manually adjudicated patient-experience clusters within the same clinic."
            cluster_id = ""

        rows.append(
            {
                "left_id": left_id,
                "right_id": right_id,
                "clinic": left["clinic_name"],
                "left_date": left["review_date"],
                "right_date": right["review_date"],
                "left_rating": left["rating"],
                "right_rating": right["rating"],
                "label": label,
                "confidence": confidence,
                "duplicate_cluster_id": cluster_id,
                "rationale": rationale,
            }
        )

fieldnames = [
    "left_id",
    "right_id",
    "clinic",
    "left_date",
    "right_date",
    "left_rating",
    "right_rating",
    "label",
    "confidence",
    "duplicate_cluster_id",
    "rationale",
]

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

positive = sum(row["label"] == "duplicate" for row in rows)
negative = sum(row["label"] == "non_duplicate" for row in rows)
medium = sum(row["label"] == "duplicate" and row["confidence"] == "medium" for row in rows)

print(f"Wrote {len(rows)} same-clinic labeled pairs: {positive} duplicates, {negative} non-duplicates")
print(f"Duplicate confidence: {positive - medium} high, {medium} medium")
