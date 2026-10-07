# Assessment Submission — Gangnam Beauty Guide Review Integrity Explorer

## Public URL

https://lokee86.github.io/gangnam-review-integrity/

Repository:

https://github.com/Lokee86/gangnam-review-integrity

## Approach

I chose one of the product card's stated hard problems — review de-duplication across syndicated sources — and built a small Review Integrity Explorer around real Gangnam Beauty Guide review data.

The prototype starts from a snapshot of 90 English review summaries exposed by Gangnam Beauty Guide. Each review is normalized into a linkage record, including clinic, review date, rating, procedure signals, and semantic embedding.

For matching, I used Splink rather than writing a custom duplicate detector. Reviews are blocked by normalized clinic, then scored using:

- semantic similarity from Qwen3 Embedding 8B
- Jaro-Winkler text similarity
- review-date agreement
- rating agreement
- a deterministic normalized procedure signature

The procedure layer is intentionally rule-based and auditable rather than another LLM call. It maps the procedure language actually present in the snapshot into a small canonical vocabulary, while keeping more specific detail tags separate from the normalized linkage signature.

I manually adjudicated the same-clinic candidate set to create a small calibration set:

- 493 candidate pairs
- 45 likely duplicate pairs
- 448 non-duplicate pairs

The final procedure-aware linkage model reaches, on that calibration set:

- 91.7% precision
- 97.8% recall
- F1 0.946
- ROC-AUC 0.999
- average precision 0.991

The product layer turns the accepted duplicate edges into review clusters and exposes both observed review volume and estimated underlying review experiences.

Current snapshot:

- 90 observed review records
- 44 model-estimated underlying experiences
- 46 estimated redundant/syndicated records
- 42 multi-record clusters
- 2 singleton reviews

The UI lets a reviewer filter by clinic, search by procedure or review text, inspect duplicate clusters, and see the evidence behind each accepted pair.

Two larger connected components are explicitly marked `needs_review` instead of being presented as confirmed single experiences. This is deliberate: connected-components clustering can overmerge records when a false-positive edge bridges otherwise separate duplicate pairs.

## Deliberate technical choices

### Splink over custom matching logic

The hard part here is probabilistic record linkage, not inventing another similarity formula. Splink already provides a mature linkage model, comparison levels, EM-based parameter estimation, and interpretable match probabilities.

### Static frontend instead of a live Python service

The linkage pipeline is reproducible offline, but the deployed assessment artifact consumes a precomputed JSON export. That removes API hosting, secrets, latency, and runtime failure modes from the demo while preserving the real linkage output.

### Procedure extraction without an LLM

The 90 summaries use explicit procedure language, so a small deterministic extractor was sufficient. It is faster, cheaper, inspectable, and avoids adding a second model to a problem that did not require one.

### Clinic blocking

I only compare reviews within the same normalized clinic. This both reflects the expected duplicate mechanism and reduces the candidate space dramatically.

### Manual-review state for ambiguous clusters

I did not force every connected component to be treated as a verified duplicate cluster. Larger components with transitive-only relationships are surfaced as ambiguous and require review.

## Reflection

The most useful part of the exercise was that the initial semantic baseline was already reasonably strong, but the remaining failures were informative.

Embedding similarity alone reached an F1 of about 0.85, but several clearly related reviews were phrased too differently to rank highly. Looking at those misses showed that procedure identity was the missing structured signal. Adding a small normalized procedure representation improved recall from 75.6% to 97.8% while keeping precision above 91%.

The main limitation is that these are calibration-set metrics rather than held-out generalization results. The manual labels were used to choose the operating threshold, so I would not treat 0.946 F1 as a production estimate.

The source text is also not the original Korean review text; it is the translated/AI-generated summary text exposed by Gangnam Beauty Guide. That means the prototype proves the linkage workflow against the product's current review surface, not against every upstream source format.

If I continued, the next work would not be more UI polish or more text-similarity functions. It would be:

1. ingest multiple real upstream Korean review sources,
2. normalize clinic and surgeon identities across sources,
3. evaluate on a genuinely held-out labeled set,
4. add a lightweight moderator workflow for uncertain pairs,
5. incrementally link new reviews as they arrive,
6. use verified procedure/surgeon evidence as stronger trust signals when available.

The final system should probably treat deduplication as part of a broader review-provenance layer: users should be able to see not only that several records look like the same underlying experience, but also where each copy came from, which details agree, and which trust signals are independently verified.

## Short version

I built a Review Integrity Explorer for Gangnam Beauty Guide using a real 90-review snapshot. It groups likely syndicated review copies with Splink using semantic similarity, text similarity, date/rating agreement, and deterministic procedure normalization. On a manually adjudicated same-clinic calibration set, the final model achieved 91.7% precision, 97.8% recall, and F1 0.946. The deployed UI shows observed review volume versus estimated unique experiences and exposes ambiguous clusters for manual review rather than hiding model uncertainty.

Public demo: https://lokee86.github.io/gangnam-review-integrity/
