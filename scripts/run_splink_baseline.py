from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
from splink.comparison_library import (
    CosineSimilarityAtThresholds,
    ExactMatch,
    JaroWinklerAtThresholds,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "linkage" / "gbg-reviews-2026-10-05.parquet"
LABELS = ROOT / "data" / "ground-truth" / "gbg-review-pair-labels-2026-10-05.csv"
OUT = ROOT / "data" / "linkage" / "baseline"

COSINE_THRESHOLDS = [0.97, 0.94, 0.91, 0.88, 0.85, 0.80, 0.70]
JARO_WINKLER_THRESHOLDS = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60]
PRIOR_MATCH_PROBABILITY = 0.01
U_RANDOM_SEED = 42
U_MAX_PAIRS = 4005


@dataclass(frozen=True)
class Label:
    duplicate: bool
    confidence: str
    cluster_id: str
    rationale: str


def read_labels() -> dict[tuple[str, str], Label]:
    result: dict[tuple[str, str], Label] = {}
    with LABELS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            result[(row["unique_id_l"], row["unique_id_r"])] = Label(
                duplicate=row["label"] == "duplicate",
                confidence=row["confidence"],
                cluster_id=row["duplicate_cluster_id"],
                rationale=row["rationale"],
            )
    return result


def pair_key(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left < right else (right, left)


def cosine(left: list[float], right: list[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(left, right, strict=True))


def roc_auc(scored: list[tuple[float, bool]]) -> float:
    positives = [score for score, label in scored if label]
    negatives = [score for score, label in scored if not label]
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def average_precision(scored: list[tuple[float, bool]]) -> float:
    ordered = sorted(scored, key=lambda item: item[0], reverse=True)
    positives = sum(label for _, label in ordered)
    true_positives = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(ordered, start=1):
        if label:
            true_positives += 1
            precision_sum += true_positives / rank
    return precision_sum / positives


def metrics_at_threshold(
    scored: list[tuple[float, bool]],
    threshold: float,
) -> dict[str, float | int]:
    tp = sum(score >= threshold and label for score, label in scored)
    fp = sum(score >= threshold and not label for score, label in scored)
    fn = sum(score < threshold and label for score, label in scored)
    tn = sum(score < threshold and not label for score, label in scored)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
    }


def best_f1(scored: list[tuple[float, bool]]) -> dict[str, float | int]:
    candidates = sorted({score for score, _ in scored})
    return max(
        (metrics_at_threshold(scored, threshold) for threshold in candidates),
        key=lambda metrics: (float(metrics["f1"]), float(metrics["precision"])),
    )


def cluster_count(
    record_ids: list[str],
    predicted_pairs: list[tuple[str, str]],
) -> int:
    parent = {record_id: record_id for record_id in record_ids}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left, right in predicted_pairs:
        union(left, right)

    return len({find(record_id) for record_id in record_ids})


def add_common_metrics(
    metrics: dict[str, float | int],
    scored: list[tuple[float, bool]],
    record_ids: list[str],
    predicted_pairs: list[tuple[str, str]],
) -> dict[str, float | int]:
    result = dict(metrics)
    result["roc_auc"] = roc_auc(scored)
    result["average_precision"] = average_precision(scored)
    result["predicted_edges"] = len(predicted_pairs)
    result["predicted_unique_clusters"] = cluster_count(record_ids, predicted_pairs)
    result["predicted_redundant_records"] = len(record_ids) - int(
        result["predicted_unique_clusters"]
    )
    return result


def make_linker(
    table: pa.Table,
    *,
    model_name: str,
    comparisons: list,
) -> tuple[Linker, DuckDBAPI]:
    api = DuckDBAPI()
    table_name = "reviews_" + model_name.replace("-", "_")
    splink_df = api.register(table, table_name=table_name)
    settings = SettingsCreator(
        link_type="dedupe_only",
        blocking_rules_to_generate_predictions=[block_on("clinic_id")],
        comparisons=comparisons,
        probability_two_random_records_match=PRIOR_MATCH_PROBABILITY,
        retain_matching_columns=False,
        retain_intermediate_calculation_columns=True,
        linker_uid=f"gbg-{model_name}-v1",
    )
    linker = Linker(splink_df, settings, log_level="ERROR")
    linker.training.estimate_u_using_random_sampling(
        max_pairs=U_MAX_PAIRS,
        seed=U_RANDOM_SEED,
        min_count_per_level=1,
        num_chunks=1,
    )
    linker.training.estimate_parameters_using_expectation_maximisation(
        block_on("clinic_id"),
        fix_u_probabilities=True,
        fix_probability_two_random_records_match=True,
        max_pairs=10_000,
        record_sample_proportion=1.0,
    )
    return linker, api


def run_splink_model(
    *,
    name: str,
    table: pa.Table,
    labels: dict[tuple[str, str], Label],
    comparisons: list,
    record_ids: list[str],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    linker, _api = make_linker(table, model_name=name, comparisons=comparisons)
    predictions_df = linker.inference.predict()
    predictions = predictions_df.as_record_list()

    scored: list[tuple[float, bool]] = []
    enriched: list[dict[str, object]] = []

    for prediction in predictions:
        key = pair_key(prediction["unique_id_l"], prediction["unique_id_r"])
        label = labels[key]
        score = float(prediction["match_probability"])
        scored.append((score, label.duplicate))
        enriched.append(
            {
                "unique_id_l": key[0],
                "unique_id_r": key[1],
                "match_probability": score,
                "match_weight": float(prediction["match_weight"]),
                "label": "duplicate" if label.duplicate else "non_duplicate",
                "confidence": label.confidence,
                "duplicate_cluster_id": label.cluster_id,
                "rationale": label.rationale,
            }
        )

    selected = best_f1(scored)
    threshold = float(selected["threshold"])
    predicted_pairs = [
        (row["unique_id_l"], row["unique_id_r"])
        for row in enriched
        if float(row["match_probability"]) >= threshold
    ]
    final_metrics = add_common_metrics(
        selected,
        scored,
        record_ids,
        predicted_pairs,
    )

    model_path = OUT / f"{name}-model.json"
    model_path.write_text(
        json.dumps(linker.misc.save_model_to_json(), indent=2) + "\n",
        encoding="utf-8",
    )

    predictions_path = OUT / f"{name}-predictions.parquet"
    pq.write_table(pa.Table.from_pylist(enriched), predictions_path, compression="zstd")

    errors = []
    for row in enriched:
        predicted_duplicate = float(row["match_probability"]) >= threshold
        actual_duplicate = row["label"] == "duplicate"
        if predicted_duplicate != actual_duplicate:
            errors.append(
                {
                    "model": name,
                    "error": "false_positive" if predicted_duplicate else "false_negative",
                    **row,
                }
            )

    return {
        "name": name,
        "training": {
            "ground_truth_used_for_parameter_training": False,
            "u_estimation": {
                "max_pairs": U_MAX_PAIRS,
                "seed": U_RANDOM_SEED,
            },
            "m_estimation": "expectation_maximisation",
            "m_estimation_block": "exact clinic_id",
            "prior_match_probability": PRIOR_MATCH_PROBABILITY,
        },
        "comparisons": [type(comparison).__name__ for comparison in comparisons],
        "metrics": final_metrics,
        "model_path": str(model_path.relative_to(ROOT)),
        "predictions_path": str(predictions_path.relative_to(ROOT)),
    }, errors


def run_raw_cosine(
    *,
    rows: list[dict[str, object]],
    labels: dict[tuple[str, str], Label],
    record_ids: list[str],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    by_id = {str(row["unique_id"]): row for row in rows}
    enriched = []
    scored: list[tuple[float, bool]] = []

    for (left_id, right_id), label in labels.items():
        left = by_id[left_id]
        right = by_id[right_id]
        score = cosine(left["summary_embedding"], right["summary_embedding"])
        scored.append((score, label.duplicate))
        enriched.append(
            {
                "unique_id_l": left_id,
                "unique_id_r": right_id,
                "cosine_similarity": score,
                "label": "duplicate" if label.duplicate else "non_duplicate",
                "confidence": label.confidence,
                "duplicate_cluster_id": label.cluster_id,
                "rationale": label.rationale,
            }
        )

    selected = best_f1(scored)
    threshold = float(selected["threshold"])
    predicted_pairs = [
        (row["unique_id_l"], row["unique_id_r"])
        for row in enriched
        if float(row["cosine_similarity"]) >= threshold
    ]
    final_metrics = add_common_metrics(selected, scored, record_ids, predicted_pairs)

    pq.write_table(
        pa.Table.from_pylist(enriched),
        OUT / "raw-cosine-pairs.parquet",
        compression="zstd",
    )

    errors = []
    for row in enriched:
        predicted_duplicate = float(row["cosine_similarity"]) >= threshold
        actual_duplicate = row["label"] == "duplicate"
        if predicted_duplicate != actual_duplicate:
            errors.append(
                {
                    "model": "raw_cosine",
                    "error": "false_positive" if predicted_duplicate else "false_negative",
                    **row,
                }
            )

    return {
        "name": "raw_cosine",
        "comparisons": ["Qwen3 embedding cosine similarity"],
        "metrics": final_metrics,
        "predictions_path": "data/linkage/baseline/raw-cosine-pairs.parquet",
    }, errors


def write_errors(errors: list[dict[str, object]]) -> None:
    path = OUT / "errors.csv"
    all_keys: list[str] = []
    for row in errors:
        for key in row:
            if key not in all_keys:
                all_keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(errors)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    table = pq.read_table(DATASET)
    rows = table.to_pylist()
    record_ids = [str(row["unique_id"]) for row in rows]
    labels = read_labels()

    expected_pairs = sum(
        1
        for left_index, left in enumerate(rows)
        for right in rows[left_index + 1 :]
        if left["clinic_id"] == right["clinic_id"]
    )
    if expected_pairs != len(labels):
        raise SystemExit(
            f"Clinic blocking yields {expected_pairs} pairs but ground truth has {len(labels)}"
        )

    raw_report, raw_errors = run_raw_cosine(
        rows=rows,
        labels=labels,
        record_ids=record_ids,
    )

    cosine_comparison = CosineSimilarityAtThresholds(
        "summary_embedding",
        COSINE_THRESHOLDS,
    )
    cosine_report, cosine_errors = run_splink_model(
        name="splink-cosine",
        table=table,
        labels=labels,
        comparisons=[cosine_comparison],
        record_ids=record_ids,
    )

    augmented_report, augmented_errors = run_splink_model(
        name="splink-augmented",
        table=table,
        labels=labels,
        comparisons=[
            CosineSimilarityAtThresholds("summary_embedding", COSINE_THRESHOLDS),
            JaroWinklerAtThresholds("summary_text", JARO_WINKLER_THRESHOLDS),
            ExactMatch("rating"),
            ExactMatch("review_date"),
        ],
        record_ids=record_ids,
    )

    errors = raw_errors + cosine_errors + augmented_errors
    write_errors(errors)

    report = {
        "dataset": "gbg-reviews-2026-10-05",
        "records": len(rows),
        "candidate_pairs": len(labels),
        "ground_truth": {
            "duplicate_pairs": sum(label.duplicate for label in labels.values()),
            "non_duplicate_pairs": sum(not label.duplicate for label in labels.values()),
            "threshold_calibration_note": (
                "Model parameters are trained without ground-truth labels. "
                "The reported decision threshold is selected on the same 493 manually "
                "labelled candidate pairs, so these are calibration-set metrics, not a "
                "held-out generalisation estimate."
            ),
        },
        "blocking_rule": "exact clinic_id",
        "models": [raw_report, cosine_report, augmented_report],
        "error_file": "data/linkage/baseline/errors.csv",
    }

    report_path = OUT / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for model in report["models"]:
        metrics = model["metrics"]
        print(
            f"{model['name']}: "
            f"F1={metrics['f1']:.3f} "
            f"precision={metrics['precision']:.3f} "
            f"recall={metrics['recall']:.3f} "
            f"ROC-AUC={metrics['roc_auc']:.3f} "
            f"AP={metrics['average_precision']:.3f} "
            f"clusters={metrics['predicted_unique_clusters']}"
        )
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()