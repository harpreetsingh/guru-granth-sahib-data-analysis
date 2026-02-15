# Guru Granth Sahib: Computational Lexical Analysis

Results of running a multi-phase NLP pipeline against the complete text of the
Guru Granth Sahib (1,430 angs, 60,629 lines, 396,036 tokens).

## Table of Contents

1. [Corpus Overview](./01-corpus.md) -- The dataset: source, scope, structure, and authorship
2. [Lexical Matching](./02-matching.md) -- Entity recognition: what was found and how often
3. [Feature Dimensions](./03-features.md) -- Eleven register dimensions measured across every line
4. [Register Density by Ang](./04-density.md) -- Where register vocabulary concentrates geographically
5. [Co-occurrence Analysis](./05-cooccurrence.md) -- Which entities appear together and what that reveals
6. [Interpretive Tagging](./06-tagging.md) -- Classifying every line by its dominant register
7. [Cross-Register Mixing](./07-mixing.md) -- Perso-Arabic / Sanskritic overlap and nirgun / sagun interplay
8. [Per-Author Analysis](./08-authors.md) -- Lexical profiles of all 18 authors
9. [Semantic Analysis](./09-semantic.md) -- RAM behavior, ALLAH context, cross-tradition fusion, civilizational density
10. [Key Findings](./10-findings.md) -- Summary of what the data tells us
- [Glossary](./glossary.md) -- Key terms for readers unfamiliar with Sikh scripture

## Method

The pipeline operates in six phases:

- **Phase 1 (Matching):** Aho-Corasick multi-pattern matching of 124 lexicon
  entities (346 aliases including spelling variants) against every tokenized line.
- **Phase 2a (Features):** Each line receives an 11-dimensional feature vector
  measuring density of perso-arabic, sanskritic, nirgun, sagun-narrative, ritual,
  cleric, ethical, devotional, oneness, scriptural, and identity vocabulary.
- **Phase 2b (Tagging):** Lines are classified into interpretive categories based
  on feature presence and dominance.
- **Phase 3 (Co-occurrence):** Ang-level Pointwise Mutual Information (PMI)
  for all entity pairs.
- **Phase 4 (Authors):** Per-author entity frequency and register density profiles
  based on Mahalla header extraction (18 authors identified).
- **Phase 5 (Semantic):** RAM semantic behavior, ALLAH context analysis,
  cross-tradition line detection.
- **Phase 6 (Composite):** Stoic-Bhakti-Advaita triangle, Civilizational Density
  Index.

All data files are in `data/derived/`. The analysis script is
`scripts/run_full_analysis.py`.
