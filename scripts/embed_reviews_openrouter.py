from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from linkage.schema import LINKAGE_RECORD_SCHEMA, validate_linkage_table

DEFAULT_INPUT = ROOT / "data" / "linkage" / "gbg-reviews-2026-10-05.parquet"
DEFAULT_OUTPUT = DEFAULT_INPUT
DEFAULT_MANIFEST = ROOT / "data" / "linkage" / "gbg-reviews-2026-10-05.embeddings.json"
DEFAULT_MODEL = "qwen/qwen3-embedding-8b"
DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
DEFAULT_DIMENSIONS = 1024
DEFAULT_BATCH_SIZE = 32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate review embeddings through OpenRouter.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--dimensions",
        type=int,
        default=int(os.environ.get("CONTINUITY_EMBEDDING_DIMENSIONS", DEFAULT_DIMENSIONS)),
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    return parser.parse_args()


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError("Embedding vector has invalid L2 norm")
    return [float(value / norm) for value in vector]


def request_embeddings(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    dimensions: int,
    texts: list[str],
) -> tuple[list[list[float]], dict[str, object]]:
    payload = json.dumps(
        {
            "model": model,
            "input": texts,
            "dimensions": dimensions,
            "encoding_format": "float",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Gangnam Prep Linkage Calibration",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter embeddings request failed: HTTP {error.code}: {detail}") from error

    data = sorted(body["data"], key=lambda item: item["index"])
    vectors = [normalize([float(value) for value in item["embedding"]]) for item in data]

    if len(vectors) != len(texts):
        raise ValueError(f"Expected {len(texts)} embeddings, received {len(vectors)}")
    if any(len(vector) != dimensions for vector in vectors):
        dimensions_seen = sorted({len(vector) for vector in vectors})
        raise ValueError(
            f"Expected {dimensions}-dimensional embeddings, received dimensions {dimensions_seen}"
        )

    return vectors, dict(body.get("usage") or {})


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
        "CONTINUITY_EMBEDDING_API_KEY"
    )
    if not api_key:
        raise SystemExit(
            "OPENROUTER_API_KEY or CONTINUITY_EMBEDDING_API_KEY must be set in the process environment"
        )

    table = pq.read_table(args.input)
    validate_linkage_table(table)

    rows = table.to_pylist()
    all_vectors: list[list[float]] = []
    usage_totals: dict[str, int] = {}

    for start in range(0, len(rows), args.batch_size):
        batch = rows[start : start + args.batch_size]
        vectors, usage = request_embeddings(
            endpoint=args.endpoint,
            api_key=api_key,
            model=args.model,
            dimensions=args.dimensions,
            texts=[str(row["summary_text"]) for row in batch],
        )
        all_vectors.extend(vectors)
        for key, value in usage.items():
            if isinstance(value, int):
                usage_totals[key] = usage_totals.get(key, 0) + value
        print(f"Embedded {min(start + len(batch), len(rows))}/{len(rows)} records")

    for row, vector in zip(rows, all_vectors, strict=True):
        row["summary_embedding"] = vector

    output = pa.Table.from_pylist(rows, schema=LINKAGE_RECORD_SCHEMA)
    validate_linkage_table(output)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(output, args.output, compression="zstd")

    norms = [
        math.sqrt(sum(value * value for value in vector))
        for vector in all_vectors
    ]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input.relative_to(ROOT)),
        "output": str(args.output.relative_to(ROOT)),
        "endpoint": args.endpoint,
        "model": args.model,
        "dimensions": args.dimensions,
        "encoding_format": "float",
        "local_postprocessing": "L2 normalization",
        "record_count": len(all_vectors),
        "batch_size": args.batch_size,
        "norm_min": min(norms),
        "norm_max": max(norms),
        "usage": usage_totals,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(all_vectors)} embeddings to {args.output}")
    print(f"Embedding dimensions: {args.dimensions}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()
