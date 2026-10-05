from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "data" / "gbg-reviews-2026-10-05.html"
OUT = ROOT / "data" / "gbg-reviews-2026-10-05.json"

html = HTML.read_text(encoding="utf-8")
chunks: list[str] = []

for match in re.finditer(r"self\.__next_f\.push\(\[1,(.*?)\]\)</script>", html, re.S):
    raw = match.group(1)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        continue
    if isinstance(value, str):
        chunks.append(value)

needle = '"reviews":['
reviews_text = None

for chunk in chunks:
    start = chunk.find(needle)
    if start < 0:
        continue

    array_start = start + len('"reviews":')
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(chunk[array_start:])
    if isinstance(value, list):
        reviews_text = value
        break

if reviews_text is None:
    raise SystemExit("Could not locate reviews array in Next.js payload")

records = []
for index, review in enumerate(reviews_text, start=1):
    records.append(
        {
            "snapshot_id": f"gbg-2026-10-05-{index:03d}",
            "ordinal": index,
            "clinic_name": review.get("clinicName"),
            "clinic_slug": review.get("clinicSlug"),
            "rating": review.get("rating"),
            "source": review.get("source"),
            "review_date": review.get("date"),
            "summary": review.get("summary"),
            "initial": review.get("initial"),
            "snapshot_source_url": "https://gangnambeautyguide.com/en/reviews/",
        }
    )

payload = {
    "snapshot": {
        "captured_on": "2026-10-05",
        "source_url": "https://gangnambeautyguide.com/en/reviews/",
        "page_claimed_count": 90,
        "record_count": len(records),
        "notes": "Public translated review summaries exposed by Gangnam Beauty Guide. Raw HTML is stored alongside this normalized snapshot.",
    },
    "reviews": records,
}

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {len(records)} reviews to {OUT}")
if len(records) != 90:
    raise SystemExit(f"Expected 90 reviews, got {len(records)}")
