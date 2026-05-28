---
name: Near-dup Jaccard threshold
description: The Jaccard similarity threshold used in the OSINT deduplicator and what "slightly different" text really means for tests
---

## Threshold
`0.72` — two events are near-duplicates if their word-token Jaccard similarity ≥ 0.72.

## Token splitting
Text is word-tokenised after lowercasing and stripping punctuation/emoji. "airstrikes" and "air strikes" are **two different tokens**, so paraphrases that split compound words will have lower similarity than expected.

## Test string guideline
For a "slightly different but same event" test case, use strings that share ≥ 73% of their tokens. A safe pattern: same subject/object/location, only verb tense or word order changes.

Good example (Jaccard ≈ 0.83):
- "IDF targeted Hezbollah weapons depot in northern Gaza killing five militants"
- "IDF targeted Hezbollah weapons depot in northern Gaza five militants killed"

Bad example (Jaccard ≈ 0.39 — will NOT trigger near-dup):
- "Israeli airstrikes targeted a weapons depot in southern Lebanon"
- "Israeli air strikes target weapons depot in south Lebanon"

**Why:** The first pair shares 10/12 tokens. The second pair only shares 5/13 because "airstrikes"→"air"+"strikes" splits, "southern"→"south", "targeted"→"target" are all different tokens.
