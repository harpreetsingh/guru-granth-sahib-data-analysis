Below is a production-grade `README.md` to initialize the repository.
It assumes the structure defined in **PLAN.md v3** and is written for external contributors and reviewers.

---

# Guru Granth Sahib — Structured Textual Analysis

A reproducible, line-level, auditable analysis platform for the *Guru Granth Sahib*.

This repository builds:

* A canonical Gurmukhi corpus (Ang 1–1430)
* Lexical analysis (strict counting)
* Structural analysis (register density, co-occurrence)
* Interpretive tagging (rule-based, evidence-first)
* A web-ready data bundle

All analysis is grounded in preserved Unicode Gurmukhi.
No English translation drives analytical logic.

---

# Project Goals

1. Create a deterministic, versioned corpus of the Guru Granth Sahib.
2. Provide strict lexical counts (e.g., divine names, ritual terms).
3. Analyze structural features (register usage, co-occurrence patterns).
4. Provide bounded interpretive tagging (Nirgun/Sagun spectrum, etc.).
5. Publish auditable outputs consumable by a web application.

---

# Architecture Overview

Phases:

* **Phase 0** — Canonical Extraction
* **Phase 1** — Lexical Matching
* **Phase 2** — Structural Analytics
* **Phase 3** — Interpretive Tagging
* **Phase 4** — Web Application (see `PLAN_WEBAPP.md`)

Each phase is independent and reproducible.

---

# Repository Structure

```
config/        Configuration files
lexicon/       Entity & marker definitions
src/           Core pipeline code
scripts/       Phase runner scripts
data/          Raw + derived artifacts
tests/         Regression + matching tests
PLAN.md        Research architecture
PLAN_WEBAPP.md Web app plan
```

---

# Requirements

Recommended:

* Python 3.11+
* `uv` or `pip`
* Docker (optional but recommended)

---

# Quick Start

## 1. Clone

```
git clone <repo-url>
cd <repo>
```

---

## 2. Install Dependencies

Using uv:

```
uv sync
```

Or pip:

```
pip install -r requirements.txt
```

---

## 3. Run Phase 0 (Corpus Extraction)

⚠️ This performs live HTTP requests.

```
./scripts/run_phase0.sh --config config/config.yaml
```

Outputs:

```
data/raw_html/
data/corpus/ggs_lines.jsonl
data/corpus/manifest.json
data/corpus/validation_report.json
```

---

## 4. Run Phase 1 (Lexical Analysis)

```
./scripts/run_phase1.sh --config config/config.yaml
```

Outputs:

```
data/derived/matches.jsonl
data/reports/entity_counts.csv
data/web_bundle/aggregates.json
```

---

## 5. Run Phase 2 (Structural Analysis)

```
./scripts/run_phase2.sh --config config/config.yaml
```

Outputs:

```
data/derived/features.jsonl
data/web_bundle/cooccurrence.json
```

---

## 6. Run Phase 3 (Interpretive Tagging)

```
./scripts/run_phase3.sh --config config/config.yaml
```

Outputs:

```
data/derived/tags.jsonl
data/reports/nirgun_sagun_distribution.csv
```

---

# Configuration

All phases accept:

```
--config config/config.yaml
--input <path>
--output <dir>
--force
--dry-run
```

Example `config.yaml`:

```yaml
ang_start: 1
ang_end: 1430

request_delay_ms_min: 500
request_delay_ms_max: 1500
max_retries: 5

normalize_mode: NFC

lexicon_paths:
  entities: lexicon/entities.yaml
  nirgun: lexicon/nirgun.yaml
  sagun: lexicon/sagun_narrative.yaml
```

---

# Reproducibility

Each phase produces:

```
run_manifest.json
```

Includes:

* git_commit
* lexicon hashes
* schema_version
* artifact checksums

Corpus validation is enforced before analysis.

---

# Stable Identifiers

Each line contains:

* `line_id` — human readable
* `line_uid` — stable hash-based identifier

All downstream artifacts reference `line_uid`.

---

# Testing

Run:

```
pytest
```

Includes:

* Parser regression tests
* Lexicon lint tests
* Matching fixtures
* Smoke pipeline tests (Ang 1–5 fixtures)

CI does **not** scrape live site.

---

# Docker (Optional)

Build:

```
docker build -t ggs-analysis .
```

Run:

```
docker run -it ggs-analysis ./scripts/run_phase1.sh
```

---

# Web Application

After running Phases 0–3:

```
data/web_bundle/
```

is ready for consumption by the frontend described in `PLAN_WEBAPP.md`.

---

# Design Principles

* Evidence-first
* No silent data loss
* All claims link to Gurmukhi lines
* Statistical claims include uncertainty
* Interpretive claims include rule trace

---

# Important Notes

* This project is descriptive, not doctrinal.
* No theological claims are made.
* Interpretive tagging is rule-based and auditable.
* All results must be reproducible from corpus.

---

# License

Code: MIT / Apache 2.0
Data artifacts: Published with source acknowledgement.

---

# Roadmap

* Improve lexicon coverage
* Expand gold set for interpretive tagging
* Add statistical dashboards
* Deploy read-only webapp
* Add search index

---

# Contributing

1. Run corpus validator before submitting changes.
2. Do not modify canonical Gurmukhi text.
3. Include tests for lexicon additions.
4. Document schema changes in `docs/migrations/`.

---

# Status

Initial scaffold ready.
Next milestone: Phase 0 corpus validation stability.

---

If you'd like, I can now:

* Generate the initial `config.yaml`
* Generate `requirements.txt`
* Generate the `Dockerfile`
* Scaffold the Python package layout
* Or generate a Phase 0 implementation outline to start coding immediately

