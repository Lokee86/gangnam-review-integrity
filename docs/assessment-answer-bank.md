# Assessment Answer Bank

These are paste-ready building blocks for likely assessment prompts. Use the shortest version that fits the actual field.

## What did you build?

I built a Review Integrity Explorer for Gangnam Beauty Guide. It takes observed review summaries, links likely syndicated/duplicate copies, clusters them into estimated underlying review experiences, and shows the evidence behind each match.

The current demo runs against a real snapshot of 90 GBG review summaries and estimates 44 underlying experiences. It also flags two larger ambiguous components for manual review instead of silently overmerging them.

Public demo: https://lokee86.github.io/gangnam-review-integrity/

## Why this feature?

The product card calls out review syndication, translation, de-duplication, and clinic normalization as the hard problem and says trust signals are the moat.

Rather than build a generic directory page, I chose one narrow part of that moat: helping a buyer or moderator distinguish raw review volume from likely unique underlying experiences.

That makes the output directly relevant to trust. Ten observed records are not necessarily ten independent patient experiences.

## Who is it for?

Primary user: an English-speaking medical-tourism buyer trying to compare Korean clinics without being misled by repeated or syndicated review copies.

Secondary user: an internal moderator/operator who needs to inspect why two reviews were linked and resolve ambiguous cases.

## How does it work?

Reviews are first blocked by normalized clinic, then compared with a probabilistic Splink model using:

- Qwen3 Embedding 8B cosine similarity
- Jaro-Winkler text similarity
- review date agreement
- rating agreement
- deterministic normalized procedure-signature agreement

Accepted duplicate edges are clustered into connected components. The UI exposes the resulting estimated unique experiences and the pairwise evidence behind each cluster.

## Why Splink?

This is a record-linkage problem, and I did not want to spend the build on recreating a mature probabilistic matching library.

Splink provides the linkage model, comparison levels, EM-based parameter estimation, and match probabilities. My custom work is primarily data normalization, procedure extraction, calibration/evaluation, cluster handling, and product presentation.

## Why Qwen3 Embedding 8B?

I wanted a strong semantic signal that could handle paraphrased translated summaries. I used Qwen3 Embedding 8B through OpenRouter at 1024 dimensions.

The embedding is only one signal. The final model performs substantially better after adding structured procedure identity, date, rating, and lexical similarity.

## Did you use a regular LLM?

Not as a runtime extraction or matching component.

The product pipeline uses Qwen3 Embedding 8B for semantic vectors, Splink for linkage, and deterministic procedure extraction. I intentionally avoided adding a general-purpose LLM extraction call because the procedure language in this snapshot was explicit enough to normalize deterministically.

AI assistance was used during development for implementation, analysis, and manual adjudication support.

## How did you evaluate it?

I manually adjudicated the complete same-clinic candidate set:

- 493 candidate pairs
- 45 likely duplicate pairs
- 448 non-duplicate pairs

The final procedure-aware model achieved on that calibration set:

- precision: 91.7%
- recall: 97.8%
- F1: 0.946
- ROC-AUC: 0.999
- average precision: 0.991

These are calibration-set metrics, not held-out production estimates, because the labels were also used to select the operating threshold.

## What changed as you built it?

The first semantic-only version was useful but missed several pairs that were clearly describing the same procedure and recovery story in different language.

Looking at those false negatives showed that generic text similarity was not the right next move. The missing evidence was structured procedure identity.

I added a small deterministic procedure normalizer. That increased recall from 75.6% to 97.8% while preserving useful precision.

## What was the most deliberate technical choice?

Probably choosing not to add more models.

Once I saw the semantic baseline's failure modes, it would have been easy to add an LLM extractor or more fuzzy text metrics. Instead I added the smallest structured feature justified by the errors: normalized procedure identity.

The deployed demo is also intentionally static. The Python/Splink pipeline generates a product JSON artifact, and the React app consumes it directly. That makes the public demo reliable and removes runtime API/secrets failure modes.

## What tradeoff did you make?

I optimized the demo for inspectability and reliability rather than pretending it was production-ready automation.

The biggest tradeoff is connected-components clustering. One false-positive edge can bridge otherwise separate duplicate pairs. Rather than hide that, the app flags larger components with transitive-only relationships as `needs_review`.

I would rather expose uncertainty than inflate confidence in the deduplication result.

## What are the limitations?

The main limitations are:

- evaluation is calibration-set, not held-out
- the source is GBG's translated/AI-generated summary text, not original Korean review text
- the current dataset is effectively one exposed upstream source
- clinic normalization is trivial in this snapshot because GBG already provides clinic labels
- surgeon identity and verified-procedure evidence are not available
- ambiguous multi-record clusters still need human review

So the prototype validates the workflow and product surface, not the full multi-source production ingestion problem.

## What would you build next?

The next useful work is upstream and operational:

1. ingest multiple real Korean sources,
2. normalize clinic and surgeon identities across sources,
3. keep source/provenance history for every syndicated copy,
4. evaluate on a held-out labeled set,
5. add a moderator queue for uncertain matches,
6. link new reviews incrementally,
7. incorporate verified procedure/surgeon evidence as stronger trust signals.

I would not spend the next iteration adding more generic text similarity metrics.

## What is the product value?

A review directory can accidentally overstate trust if syndicated copies are presented like independent patient experiences.

This feature makes that visible.

The buyer can see both observed review volume and estimated unique experience count, and an operator can inspect exactly why records were linked. That turns de-duplication from invisible backend cleanup into a user-facing trust signal.

## Short reflection

I started with the assumption that semantic similarity would carry most of the deduplication problem. It did reasonably well, but the errors were more useful than the score: the hard false negatives were often the same procedure described in very different translated language.

Adding a small, deterministic procedure representation improved the model much more than adding another generic text metric would have. The main thing I would change with more time is evaluation: I would separate calibration from a held-out set and test across genuinely independent upstream sources.

## Ultra-short approach

I focused on the product card's de-duplication problem. I used real GBG review summaries, Qwen embeddings, deterministic procedure normalization, and Splink probabilistic linkage to group likely syndicated copies into estimated underlying experiences. The static React UI exposes raw-vs-unique review counts and lets users inspect the evidence and ambiguity behind each cluster.

## Ultra-short reflection

The semantic baseline was decent, but its false negatives showed that structured procedure identity mattered more than adding another generic similarity metric. The final procedure-aware model reached 0.946 F1 on the calibration set. With more time, I would prioritize held-out evaluation and multi-source ingestion rather than more UI or model complexity.
