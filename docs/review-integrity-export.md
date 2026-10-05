# Review Integrity product export

`data/product/review-integrity.json` is the static frontend contract for the Review Integrity
Explorer.

It is generated from the procedure-aware Splink predictions by:

```powershell
uv run --no-project --python .venv\Scripts\python.exe python scripts\build_review_integrity_export.py
```

## Headline summary

Current snapshot:

- 90 observed review records
- 44 model-estimated underlying experiences
- 46 model-estimated redundant/syndicated records
- 42 multi-record clusters
- 2 singleton records
- 48 accepted duplicate edges
- 2 connected components flagged for review

These are **model estimates**, not verified patient identities. The export embeds the model's
calibration note and metrics for that reason.

## Cluster contract

Each cluster contains:

- stable `cluster_id`
- clinic identity
- member count and estimated redundant-record count
- `review_status`
  - `auto_linked`: a simple/fully linked component
  - `needs_review`: a multi-record connected component containing transitive-only pairings
- procedure signatures
- review dates and ratings represented in the cluster
- accepted pairwise model matches
- per-edge evidence:
  - Splink match probability
  - Qwen embedding cosine
  - procedure-signature agreement
  - review-date agreement
  - rating agreement
- the review summaries and display metadata needed by the UI

## Ambiguous connected components

Connected-components clustering can merge multiple duplicate pairs when even one false-positive
edge bridges them. The export does not hide this.

Current calibration produces two four-record components requiring review:

- Pop PS: 5 accepted edges out of 6 possible internal pairs
- View PS: 3 accepted edges out of 6 possible internal pairs

The remaining multi-record clusters are two-record pairs. The frontend should surface
`needs_review` prominently rather than treating these larger components as confirmed single
patient experiences.

## Clinic summary

`clinic_stats` provides:

- observed review count
- estimated unique-experience count
- estimated redundant-record count

This lets the static UI filter or summarize review integrity by clinic without running Python
at request time.
