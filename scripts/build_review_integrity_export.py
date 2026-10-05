from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "linkage" / "gbg-reviews-2026-10-05.parquet"
PREDICTIONS = ROOT / "data" / "linkage" / "baseline" / "splink-procedure-predictions.parquet"
BASELINE_REPORT = ROOT / "data" / "linkage" / "baseline" / "report.json"
OUTPUT = ROOT / "data" / "product" / "review-integrity.json"
MODEL_NAME = "splink-procedure"
EXPORT_SCHEMA_VERSION = 1


class UnionFind:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            if left_root < right_root:
                self.parent[right_root] = left_root
            else:
                self.parent[left_root] = right_root


def cosine(left: list[float], right: list[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(left, right, strict=True))


def serialise_review(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": row["unique_id"],
        "clinic_id": row["clinic_id"],
        "clinic_name": row["clinic_name"],
        "review_date": row["review_date"].isoformat() if row["review_date"] else None,
        "rating": row["rating"],
        "procedures": row["procedures"],
        "primary_procedure": row["primary_procedure"],
        "revision": row["revision"],
        "procedure_signature": row["procedure_signature"],
        "source": row["upstream_source"],
        "source_url": row["source_url"],
        "summary": row["summary_text"],
    }


def main() -> None:
    report = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
    model = next(model for model in report["models"] if model["name"] == MODEL_NAME)
    threshold = float(model["metrics"]["threshold"])

    source_rows = pq.read_table(DATASET).to_pylist()
    records_by_id = {str(row["unique_id"]): row for row in source_rows}
    record_ids = sorted(records_by_id)

    prediction_rows = pq.read_table(PREDICTIONS).to_pylist()
    accepted_pairs = [
        row for row in prediction_rows if float(row["match_probability"]) >= threshold
    ]

    union_find = UnionFind(record_ids)
    for pair in accepted_pairs:
        union_find.union(str(pair["unique_id_l"]), str(pair["unique_id_r"]))

    members_by_root: dict[str, list[str]] = defaultdict(list)
    for record_id in record_ids:
        members_by_root[union_find.find(record_id)].append(record_id)

    pair_lookup: dict[tuple[str, str], dict[str, object]] = {}
    for pair in accepted_pairs:
        left = str(pair["unique_id_l"])
        right = str(pair["unique_id_r"])
        key = tuple(sorted((left, right)))
        pair_lookup[key] = pair

    components = sorted(
        (sorted(members) for members in members_by_root.values()),
        key=lambda members: (-len(members), members[0]),
    )

    clusters: list[dict[str, object]] = []
    cluster_id_by_record: dict[str, str] = {}

    for index, members in enumerate(components, start=1):
        cluster_id = f"cluster-{index:03d}"
        for member in members:
            cluster_id_by_record[member] = cluster_id

        rows = [records_by_id[member] for member in members]
        clinic_ids = {str(row["clinic_id"]) for row in rows}
        if len(clinic_ids) != 1:
            raise RuntimeError(f"Cluster {cluster_id} crossed clinic boundary: {clinic_ids}")

        accepted_edges = []
        for left_index, left_id in enumerate(members):
            for right_id in members[left_index + 1 :]:
                key = tuple(sorted((left_id, right_id)))
                pair = pair_lookup.get(key)
                if pair is None:
                    continue

                left = records_by_id[left_id]
                right = records_by_id[right_id]
                accepted_edges.append(
                    {
                        "left_id": left_id,
                        "right_id": right_id,
                        "match_probability": float(pair["match_probability"]),
                        "embedding_cosine": cosine(
                            left["summary_embedding"],
                            right["summary_embedding"],
                        ),
                        "same_procedure_signature": (
                            left["procedure_signature"] == right["procedure_signature"]
                        ),
                        "same_review_date": left["review_date"] == right["review_date"],
                        "same_rating": left["rating"] == right["rating"],
                    }
                )

        edge_scores = [float(edge["match_probability"]) for edge in accepted_edges]
        possible_internal_pairs = len(members) * (len(members) - 1) // 2
        accepted_edge_count = len(accepted_edges)
        edge_density = (
            accepted_edge_count / possible_internal_pairs
            if possible_internal_pairs
            else 0.0
        )
        needs_review = len(members) > 2 and accepted_edge_count < possible_internal_pairs
        duplicate_count = max(0, len(members) - 1)
        representative_id = max(
            members,
            key=lambda member: (
                len(str(records_by_id[member]["summary_text"])),
                -int(records_by_id[member]["source_ordinal"]),
            ),
        )

        cluster = {
            "cluster_id": cluster_id,
            "kind": "duplicate_cluster" if len(members) > 1 else "singleton",
            "clinic_id": rows[0]["clinic_id"],
            "clinic_name": rows[0]["clinic_name"],
            "member_count": len(members),
            "duplicate_record_count": duplicate_count,
            "review_status": "needs_review" if needs_review else "auto_linked",
            "possible_internal_pairs": possible_internal_pairs,
            "accepted_edge_count": accepted_edge_count,
            "edge_density": edge_density,
            "transitive_only_pair_count": possible_internal_pairs - accepted_edge_count,
            "representative_id": representative_id,
            "procedure_signatures": sorted(
                {
                    str(row["procedure_signature"])
                    for row in rows
                    if row["procedure_signature"] is not None
                }
            ),
            "review_dates": sorted(
                {row["review_date"].isoformat() for row in rows if row["review_date"]}
            ),
            "ratings": sorted(
                {float(row["rating"]) for row in rows if row["rating"] is not None}
            ),
            "score_summary": (
                {
                    "accepted_edge_count": accepted_edge_count,
                    "min_match_probability": min(edge_scores),
                    "mean_match_probability": mean(edge_scores),
                    "max_match_probability": max(edge_scores),
                }
                if edge_scores
                else None
            ),
            "accepted_pair_matches": accepted_edges,
            "records": [serialise_review(records_by_id[member]) for member in members],
        }
        clusters.append(cluster)

    duplicate_clusters = [cluster for cluster in clusters if cluster["member_count"] > 1]
    singleton_clusters = [cluster for cluster in clusters if cluster["member_count"] == 1]
    review_clusters = [
        cluster for cluster in duplicate_clusters if cluster["review_status"] == "needs_review"
    ]

    clinic_accumulator: dict[str, dict[str, object]] = {}
    for row in source_rows:
        clinic_id = str(row["clinic_id"])
        clinic_accumulator.setdefault(
            clinic_id,
            {
                "clinic_id": clinic_id,
                "clinic_name": row["clinic_name"],
                "observed_reviews": 0,
                "estimated_unique_experiences": 0,
            },
        )
        clinic_accumulator[clinic_id]["observed_reviews"] += 1

    for cluster in clusters:
        clinic_accumulator[str(cluster["clinic_id"])]["estimated_unique_experiences"] += 1

    clinic_stats = []
    for clinic in sorted(
        clinic_accumulator.values(),
        key=lambda clinic: (-int(clinic["observed_reviews"]), str(clinic["clinic_name"])),
    ):
        observed = int(clinic["observed_reviews"])
        unique = int(clinic["estimated_unique_experiences"])
        clinic_stats.append(
            {
                **clinic,
                "estimated_redundant_records": observed - unique,
            }
        )

    payload = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "dataset": report["dataset"],
        "source_record_count": len(source_rows),
        "model": {
            "name": MODEL_NAME,
            "decision_threshold": threshold,
            "blocking_rule": report["blocking_rule"],
            "calibration_metrics": model["metrics"],
            "calibration_note": report["ground_truth"]["threshold_calibration_note"],
        },
        "summary": {
            "observed_reviews": len(source_rows),
            "estimated_unique_experiences": len(clusters),
            "estimated_redundant_records": len(source_rows) - len(clusters),
            "duplicate_clusters": len(duplicate_clusters),
            "singleton_reviews": len(singleton_clusters),
            "accepted_duplicate_edges": len(accepted_pairs),
            "clusters_requiring_review": len(review_clusters),
            "records_in_review_clusters": sum(
                int(cluster["member_count"]) for cluster in review_clusters
            ),
        },
        "clinic_stats": clinic_stats,
        "duplicate_clusters": duplicate_clusters,
        "singletons": singleton_clusters,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT}")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()