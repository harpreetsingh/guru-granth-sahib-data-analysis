# Guru Granth Sahib: Computational Lexical Analysis

Results of running a multi-phase NLP pipeline against the complete text of the
Guru Granth Sahib (1,430 angs, 60,629 lines, 396,036 tokens).

## Table of Contents

1. [Corpus Overview](./01-corpus.md) -- The dataset: source, scope, and structure
2. [Lexical Matching](./02-matching.md) -- Entity recognition: what was found and how often
3. [Feature Dimensions](./03-features.md) -- Six register dimensions measured across every line
4. [Register Density by Ang](./04-density.md) -- Where register vocabulary concentrates geographically
5. [Co-occurrence Analysis](./05-cooccurrence.md) -- Which entities appear together and what that reveals
6. [Interpretive Tagging](./06-tagging.md) -- Classifying every line by its dominant register
7. [Cross-Register Mixing](./07-mixing.md) -- Perso-Arabic / Sanskritic overlap and nirgun / sagun interplay
8. [Key Findings](./08-findings.md) -- Summary of what the data tells us

## Method

The pipeline operates in three phases:

- **Phase 1 (Matching):** Aho-Corasick multi-pattern matching of 70 lexicon
  entities (206 aliases including spelling variants) against every tokenized line.
- **Phase 2 (Features):** Each line receives a 6-dimensional feature vector
  measuring density of perso-arabic, sanskritic, nirgun, sagun-narrative, ritual,
  and cleric vocabulary.
- **Phase 3 (Tagging):** Lines are classified into interpretive categories based
  on feature presence and dominance.

All data files are in `data/derived/`. The analysis script is
`scripts/run_full_analysis.py`.
