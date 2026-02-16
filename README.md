# Guru Granth Sahib — Computational Lexical Analysis

A reproducible, line-level analysis of the complete Guru Granth Sahib
(1,430 angs, 60,629 lines, 396,036 tokens) using a 124-entity theological
lexicon across 11 feature dimensions. All analysis is grounded in preserved
Unicode Gurmukhi. No English translation drives analytical logic.

## Corpus at a Glance

| Metric | Value |
|--------|-------|
| Total angs (pages) | 1,430 |
| Total lines | 60,629 |
| Total tokens | 396,036 |
| Lexicon entities | 124 (346 aliases) |
| Feature dimensions | 11 |
| Authors identified | 18 |
| Entity matches | 60,012 |
| Lines with matches | 34,712 (57.3%) |

```
Guru Arjan:         26,036  ██████████████████████████████████████████████████
Guru Nanak:         11,230  █████████████████████▌
Guru Amar Das:       9,041  █████████████████▎
Guru Ram Das:        7,005  █████████████▍
Kabir:               4,187  ████████
All others (13):     3,130  ██████
```

## Key Findings

- **The GGS is quantitatively a nirgun text.** 42.25% of all lines contain
  nirgun-register vocabulary. Sagun narrative appears in only 0.51% -- a 83:1
  ratio.
- **HARI (ਹਰਿ) is the dominant divine name, not WAHEGURU.** HARI appears 9,341
  times (55x more than WAHEGURU's 171). WAHEGURU became primary in the later
  Sikh tradition, not in the scriptural text itself.
- **Three Pillars account for 85.2% of theological vocabulary:** nirgun theology
  (42.25%), Sanskritic philosophy (30.21%), devotional-ethical practice (12.7%).

Full findings: [docs/10-findings.md](docs/10-findings.md)

## Analysis Results

Start here: **[Corpus Overview](docs/01-corpus.md)** -- then follow the
numbered documents in sequence.

| # | Document | What it covers |
|---|----------|---------------|
| 1 | [Corpus Overview](docs/01-corpus.md) | Source, scope, structure, authorship |
| 2 | [Lexical Matching](docs/02-matching.md) | Entity recognition: what was found and how often |
| 3 | [Feature Dimensions](docs/03-features.md) | Eleven register dimensions measured across every line |
| 4 | [Register Density](docs/04-density.md) | Where register vocabulary concentrates by ang |
| 5 | [Co-occurrence](docs/05-cooccurrence.md) | Which entities appear together (PMI analysis) |
| 6 | [Interpretive Tagging](docs/06-tagging.md) | Classifying every line by dominant register |
| 7 | [Cross-Register Mixing](docs/07-mixing.md) | Perso-Arabic / Sanskritic overlap, nirgun / sagun interplay |
| 8 | [Per-Author Analysis](docs/08-authors.md) | Lexical profiles of all 18 authors |
| 9 | [Semantic Analysis](docs/09-semantic.md) | RAM behavior, ALLAH context, civilizational density |
| 10 | [Key Findings](docs/10-findings.md) | Summary of all findings |
| - | [Glossary](docs/glossary.md) | Key terms for readers unfamiliar with Sikh scripture |

## Repository Structure

```
lexicon/       Entity & marker definitions (YAML)
src/           Core pipeline code
scripts/       Phase runner scripts
data/corpus/   Canonical Gurmukhi corpus (JSONL)
data/derived/  Analysis outputs (matches, features, tags, densities)
docs/          Analysis results (the documents listed above)
tests/         Regression + matching tests
```

## Quick Start

```bash
git clone <repo-url> && cd guru-granth-sahib-data-analysis
uv sync
uv run scripts/run_full_analysis.py
```

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

## Design Principles

- Evidence-first: all claims link to Gurmukhi lines
- Reproducible: each phase produces a run manifest with git commit, lexicon
  hashes, and artifact checksums
- Descriptive, not doctrinal: no theological claims are made
- Interpretive tagging is rule-based and auditable

## License

Code: MIT. Data artifacts: published with source acknowledgement.
