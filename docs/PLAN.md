Guru Granth Sahib Multi-Layer Textual Analysis Platform
0. Vision

Build a reproducible, auditable, line-level corpus of the Guru Granth Sahib, and implement multi-layer analysis:

Phase 0 — Canonical Extraction

Phase 1 — Lexical Analysis (strict counting)

Phase 2 — Structural Analysis

Phase 3 — Interpretive Tagging (bounded semantics)

Phase 3.5 — Optional Unsupervised Discovery

Phase 4 — Web Application (separate document)

Core principle:

Gurmukhi text is the ground truth.
All analysis is derived from preserved Unicode Gurmukhi.
No English translation drives analysis logic.

Everything must be:

Deterministic

Versioned

Reproducible

Auditable

Publicly reviewable

Pipeline Data Flow:

Phase 0: (network) --> ggs_lines.jsonl + manifest.json
            |
Phase 1: ggs_lines.jsonl + lexicon/*.yaml --> matches.jsonl
            |
Phase 2: ggs_lines.jsonl + matches.jsonl + lexicon/*.yaml --> features.jsonl
            |
Phase 3: ggs_lines.jsonl + matches.jsonl + features.jsonl + config/tagging --> tags.jsonl
            |
Bundle:  matches.jsonl + features.jsonl + tags.jsonl + ggs_lines.jsonl --> web_bundle/

Each phase reads only its declared inputs.
Each phase writes only its declared outputs.
No phase modifies upstream artifacts.

Phase validation: before starting, each phase checks that its required
input artifacts exist and pass schema validation. Missing inputs =
abort with actionable error message naming the missing file and the
command to produce it.

1. Repository Structure
/
  PLAN.md
  PLAN_WEBAPP.md
  README.md
  LICENSE
  NOTICE.md
  Dockerfile
  pyproject.toml / uv.lock

  config/
    config.yaml
    ragas.yaml

  lexicon/
    _schema.yaml
    entities.yaml
    nirgun.yaml
    sagun_narrative.yaml
    perso_arabic.yaml
    sanskritic.yaml
    polysemy.yaml

  data/
    raw_html/
    corpus/
      ggs_lines.jsonl
      cross_validation.jsonl
      manifest.json
      validation_report.json
    derived/
      matches.jsonl
      features.jsonl
      tags.jsonl
    reports/
      *.csv
    web_bundle/
      manifest.json
      aggregates.json
      cooccurrence.json
      corpus/
        lines_001_100.json
        lines_101_200.json
        ...
        lines_1401_1430.json
      search_index.json
      lineage.json
    gold/
      gold_labels.jsonl

  .cache/
    phase1_input_hash.json
    phase2_input_hash.json
    phase3_input_hash.json

  src/
    ggs/
      __init__.py
      cli.py
      corpus/
        __init__.py
        scrape.py
        parse_srigranth.py
        normalize.py
        tokenize.py
        validate.py
      analysis/
        __init__.py
        match.py
        features.py
        tagger.py
        stats.py
      lexicon/
        __init__.py
        lint.py
        loader.py
      output/
        __init__.py
        report.py
        web_bundle.py
        audit.py

  tests/
    conftest.py
    fixtures/
    test_parse.py
    test_normalize.py
    test_tokenize.py
    test_match.py
    test_features.py
    test_tagger.py
    test_roundtrip.py
    test_properties.py

2. Data Contract & Versioning

Provenance is tracked at two levels:

File-level (in each phase's run_manifest.json):

schema_version

generator_version

generated_at

git_commit

lexicon_hashes

input_manifest_hash

config_hash

output_artifact_hashes

Record-level (in each JSONL record):

schema_version (only this, for forward-compatibility parsing)

Rationale: provenance fields like git_commit and lexicon_hashes are
identical across all records in a single run. Repeating them per-record
wastes ~24MB on a 60,000-line corpus. The run_manifest.json is the
provenance anchor; individual records carry only schema_version so
parsers can detect format changes.

Major version = breaking change
Minor version = additive change

Every run produces:

run_manifest.json

Each phase tracks input/output hashes for incremental runs.
Cache is stored at project root (.cache/), gitignored, separate from
data artifacts:

.cache/
  phase1_input_hash.json
  phase2_input_hash.json
  phase3_input_hash.json

Incremental behavior:

On run, compute hash of all inputs (corpus file hash + lexicon hashes + config hash).
If hash matches cached value AND output artifacts exist, skip phase.
--force flag bypasses cache and runs regardless.
Cache invalidation is automatic when inputs change.

2.1 Pipeline Error Model

All phases follow a uniform error handling contract:

Error severity levels:

FATAL — pipeline cannot continue. Abort immediately.
  Examples: missing input file, schema validation failure,
  corpus integrity violation.

ERROR — single record cannot be processed. Skip record, continue pipeline.
  Record is written to <phase>_errors.jsonl with error details.
  Examples: malformed lexicon entry, unparseable line,
  division by zero in density computation.

WARNING — record processed but with degraded quality. Continue pipeline.
  Warning recorded in run_manifest.json summary.
  Examples: token count unusually high (>100), match confidence LOW,
  shabad boundary ambiguous.

Error record schema (written to <phase>_errors.jsonl):

{
  "line_uid": "...",
  "phase": "lexical",
  "severity": "ERROR",
  "error_type": "DIVISION_BY_ZERO",
  "message": "Token count is 0 after structural marker removal",
  "context": { "ang": 433, "line_id": "433:07" }
}

Pipeline completion rules:

FATAL errors: abort, exit non-zero, print actionable message.

ERROR count > threshold (configurable, default 100): abort pipeline,
likely indicates a systematic issue, not isolated bad records.

Warnings: always continue, summarize in run_manifest.json.

Config:

error_handling:
  max_record_errors: 100
  strict_mode: false

3. Phase 0 — Canonical Corpus Extraction
3.1 Sources

Primary: SriGranth servlet

https://www.srigranth.org/servlet/gurbani.gurbani?Action=Page&Param=<ANG>

Secondary (for cross-validation, not primary):

iGurbani.com

SearchGurbani.com

GurbaniNow API (JSON, no scraping needed)

Source strategy:

1. Scrape primary source for all 1430 angs
2. For validation: sample N angs (e.g., 50) from secondary source
3. Compare normalized Gurmukhi text line-by-line
4. Log discrepancies to data/corpus/cross_validation.jsonl
5. Discrepancies are warnings, not errors (sources may differ in whitespace/nukta)

Fallback: If primary is unavailable, corpus can be bootstrapped from
a committed snapshot (data/corpus/ggs_lines.jsonl published as a
GitHub Release artifact).

3.1.1 Parser Abstraction

Each source has its own parser (parse_srigranth.py, parse_igurbani.py, etc.).
All parsers produce the same canonical record format (Section 3.3).
Parser selection is config-driven:

source:
  primary: srigranth
  cross_validate: [gurbaninow]
  sample_size: 50

3.1.2 Structural Metadata Extraction

Each parser must extract the following structural metadata per line:

author:
  Identified from the Mahalla notation (ਮਹਲਾ ੧, ਮ: ੧, etc.)
  or from explicit author headers in the source HTML.
  Canonical author IDs: M1 (Guru Nanak), M2, M3, M4, M5, M9,
  KABIR, FARID, NAMDEV, RAVIDAS, etc.
  Unmapped authors stored as raw text with a validation warning.

raga:
  Identified from raga headers in the source HTML.
  Canonical raga list maintained in config/ragas.yaml.

shabad boundaries:
  Identified by shabad separator elements in source HTML.
  On srigranth.org: the shabad number annotation and visual separators.
  On GurbaniNow API: explicit shabad_id field in JSON response.
  Parser assigns sequential shabad_id per raga section (e.g., ASA-001).
  If boundary detection fails, the entire ang is flagged in
  validation_report.json with error SHABAD_BOUNDARY_AMBIGUOUS.

pauri / stanza numbering:
  Extracted from numeral markers (੧, ੨, ...) in source.
  null if not present (not all compositions have pauri numbering).

rahao detection:
  Set to true when the line contains ਰਹਾਉ (or variant spellings).
  The ਰਹਾਉ token is extracted to structural_markers by the tokenizer
  (Section 3.5) but the boolean is set here during parsing, before
  tokenization.

3.2 Scraping Protocol

500-1500ms jitter delay

Exponential backoff retry

Resumable scrape_state.json

Clear User-Agent:
ggs-text-analysis/<version>

Respect robots/terms

Stop on repeated 403/429

Failure classification:

FETCH_HTTP_ERROR

FETCH_TIMEOUT

FETCH_BLOCKED

PARSE_SELECTOR_FAIL

PARSE_HEURISTIC_FAIL

OUTPUT_WRITE_FAIL

Failures logged to:

data/raw_html/failures.jsonl

3.3 Canonical Record Format
{
  "schema_version": "1.0.0",
  "ang": 1,
  "line_id": "1:01",
  "line_uid": "ang1:sha256:abcdef...",
  "shabad_uid": "shabad:sha256:...",
  "line_in_shabad": 1,
  "gurmukhi_raw": "ੴ ਸਤਿ ਨਾਮੁ...",
  "gurmukhi": "...",
  "tokens": ["ੴ", "ਸਤਿ", "ਨਾਮੁ"],
  "token_spans": [[0,1], [2,5], [6,10]],
  "meta": {
    "raga": "Japuji",
    "author": "Mahalla 1",
    "section_header": null,
    "shabad_id": "J001",
    "pauri": null,
    "rahao": false,
    "structural_markers": []
  },
  "source_ang_url": "...srigranth...?Param=1"
}

Per-ang source details (url, retrieved_at, sha256, parser_version)
are recorded in data/corpus/manifest.json under a per-ang index,
keyed by ang number. Individual line records carry only source_ang_url
as a cross-reference.

Field definitions:

gurmukhi_raw — exact Unicode text as scraped from source HTML,
  before any processing. Preserved for audit/diffing.
  Never used for analysis. Never displayed in webapp.

gurmukhi — output of the normalization pipeline (Section 3.4).
  This is the canonical analysis text. All matching,
  tokenization, and feature computation runs against
  this field. Displayed in webapp concordance views.

tokens — output of the tokenizer (Section 3.5) applied to
  gurmukhi. All density scores, counts, and co-occurrence
  are computed over this list.

token_spans — parallel array to tokens, recording each token's
  [start, end] character offset in the gurmukhi string.
  Enables mapping match spans to token indices and
  concordance highlighting in the webapp.

line_uid is computed from hash(ang + gurmukhi), i.e., from the
normalized form. This means normalization changes DO change line_uids.
This is intentional: a normalization fix is a corpus change and should
be versioned as such.

Convention: every module that reads text uses `gurmukhi` (normalized).
Only the scraper writes `gurmukhi_raw`. Only the validator reads both.

Identifier Rules

line_id = human-readable sequence

line_uid = stable ID = hash(ang + gurmukhi)

shabad_uid = stable ID = hash(ang of first line + line_id of first line)

Rationale: shabad_uid must be content-independent so that a
normalization change to one line does not invalidate every sibling
line's shabad_uid. Position-based identity is stable because the
structural layout of the GGS is fixed (the text is canonical).

All downstream artifacts use line_uid

3.4 Normalization Pipeline

normalize.py applies a multi-step, ordered pipeline:

Step 1 — Unicode NFC
Step 2 — Zero-width character stripping (ZWJ, ZWNJ)
Step 3 — Nukta policy (configurable: PRESERVE | STRIP | DUAL)
  PRESERVE: keep nukta variants distinct (default)
  STRIP: collapse ਖ਼→ਖ, ਗ਼→ਗ, etc.
  DUAL: produce both normalized and nukta-aware token lists
Step 4 — Nasal marker normalization (configurable: CANONICAL_TIPPI | CANONICAL_BINDI | PRESERVE)
  CANONICAL_TIPPI: normalize Bindi (ਂ) to Tippi (ੰ) everywhere (default)
  CANONICAL_BINDI: normalize Tippi (ੰ) to Bindi (ਂ) everywhere
  PRESERVE: keep source form as-is
  Rationale: Tippi and Bindi represent the same nasal sound.
  Sources vary in which they use. Canonicalizing to one form
  prevents the same word from fragmenting into two token types.
Step 5 — Vishram marker handling (STRIP | PRESERVE_SEPARATE)
Step 6 — Halant/conjunct canonicalization (configurable: DECOMPOSE | PRESERVE)
  DECOMPOSE: decompose pre-composed conjunct forms into
    base consonant + halant (੍) + second consonant (default)
    Example: if a source uses a pre-composed ligature,
    decompose to base + halant + second consonant
  PRESERVE: keep source conjunct encoding as-is
  Rationale: different Gurmukhi fonts and input methods produce
  different conjunct encodings for the same visual glyph. Decomposing
  ensures the same sound always produces the same byte sequence.
Step 7 — Whitespace normalization (collapse runs, trim)

Each step is independently testable and logged.
The pipeline version is recorded in run_manifest.json.

Config:

normalization:
  unicode: NFC
  nukta_policy: PRESERVE
  nasal_policy: CANONICAL_TIPPI
  vishram_policy: STRIP
  zwj_policy: STRIP
  halant_policy: DECOMPOSE

3.5 Tokenization

tokenize.py performs:

Input: gurmukhi (post-normalization string)

Step 1 — Extract and remove structural markers (ਰਹਾਉ, numerals like ੧੨੩, ॥)
         Store in meta.structural_markers
Step 2 — Split on whitespace
Step 3 — Strip residual punctuation from token boundaries
Step 4 — Filter empty tokens

Output: tokens list + token_spans list + structural_markers metadata

token_spans is a parallel array to tokens, recording each token's
[start, end] character offset in the gurmukhi string.

Example:
  gurmukhi: "ਸਤਿ ਨਾਮੁ ਕਰਤਾ"
  tokens:      ["ਸਤਿ",  "ਨਾਮੁ",  "ਕਰਤਾ"]
  token_spans: [[0,3],   [4,8],    [9,14]]

Token spans enable:
  Mapping match spans (character offsets) to token indices
  Concordance highlighting in the webapp (span to display position)
  Validation: every match span must align to token boundaries

Tokenizer version recorded in run_manifest.json.
Token count recorded per line for downstream sanity checks.

3.6 Corpus Integrity Validation

validate.py enforces:

Unique line_uid

Non-empty gurmukhi

Valid normalization (full pipeline applied, idempotent check)

Provenance fields present

Schema version supported

Normalization pipeline version matches current

Token count sanity check (flag lines with 0 tokens or >200 tokens)

Character repertoire check (flag non-Gurmukhi Unicode outside expected set)

Shabad integrity (all lines in a shabad are contiguous, shabad_uid is consistent)

token_spans alignment (each span falls within gurmukhi length, no gaps/overlaps)

Outputs:

validation_report.json


Failure = abort pipeline.

4. Phase 1 — Lexical Analysis

Strict, non-interpretive matching.

Inputs:
  data/corpus/ggs_lines.jsonl     (from Phase 0)
  lexicon/*.yaml                  (entity definitions)

Outputs:
  data/derived/matches.jsonl
  data/reports/entity_counts*.csv
  data/web_bundle/aggregates.json

4.1 Lexicon Schema

Each lexicon file (entities.yaml, nirgun.yaml, etc.) conforms to _schema.yaml.

Entry schema:

entity:
  id: ALLAH
  canonical_form: ਅੱਲਾਹ
  aliases:
    - form: ਅਲਾਹੁ
      type: exact
    - form: ਅਲਹ
      type: exact
  category: divine_name
  tradition: islamic
  register: perso_arabic
  notes: "Arabic name for God, used in GGS in universalist context"
  polysemous: false
  added_version: "1.0.0"

Required fields: id, canonical_form, aliases, category
Optional fields: tradition, register, notes, polysemous, added_version

Field constraints:
  id:          unique, UPPER_SNAKE_CASE
  category:    one of:
    divine_name       — names/epithets for the divine (ਅੱਲਾਹ, ਰਾਮ, ਹਰਿ)
    concept           — abstract theological/philosophical terms (ਹੁਕਮ, ਨਾਮ)
    marker            — register/style indicator (Perso-Arabic or Sanskritic term)
    narrative         — proper nouns from stories/examples (ਧ੍ਰੂ, ਪ੍ਰਹਿਲਾਦ)
    place             — geographic references (ਕਾਸ਼ੀ, ਬਨਾਰਸ, ਮੱਕਾ)
    practice          — ritual/worship practices (ਤੀਰਥ, ਜਪ, ਪੂਜਾ)
    negation          — negation words used in co-occurrence analysis (ਨਾ, ਬਿਨੁ)
    temporal          — cosmological/time terms (ਜੁਗ, ਕਲਿਜੁਗ)
  tradition:   one of:
    islamic           — Perso-Arabic / Sufi tradition
    vedantic          — Vedanta / Brahmanical tradition
    vaishnava         — Vaishnava bhakti (Ram/Krishna devotion)
    yogic             — Nath/Yoga tradition (Gorakh, Nath, Jog)
    bhakti            — Sant/bhakti tradition (Kabir, Namdev, Ravidas)
    universal         — not specific to any tradition
    sikh              — distinctly Sikh terminology
    null              — tradition not applicable
  register:    one of: perso_arabic, sanskritic, mixed, neutral

Polysemy registry (lexicon/polysemy.yaml):
  Maps surface forms to multiple entity_ids with context hints
  for downstream disambiguation.

4.2 Lexicon QA

lint.py checks:

All entries conform to _schema.yaml

Duplicate aliases

Missing required fields

Normalization collisions

YAML schema validity

Cross-file ID uniqueness (no entity_id appears in two files)

Alias coverage (every alias normalizes to a valid Gurmukhi string)

Category/tradition/register values are from controlled vocabulary

Tests include:

Must-match fixtures

Must-not-match fixtures

4.3 Matching Engine

Aho-Corasick multi-pattern scan

Boundary enforcement post-match

Compiled regex cache

--profile mode for performance diagnostics

Span coordinate system:

All spans are character offsets into the `gurmukhi` field (normalized form).
This is the same string used for matching. Concordance UIs display
`gurmukhi` and can use spans directly for highlighting.

Overlap resolution:

When two matches overlap in the same line:
  1. If one span contains the other (nested): keep BOTH.
     The longer match is the "primary"; the shorter is "nested".
     Example: SATNAM [0,9] contains NAAM [5,9] — both are valid.
  2. If spans partially overlap (crossing): keep the LONGER match,
     discard the shorter. Log discarded match at DEBUG level.
  3. Equal-length overlaps: keep the match with higher confidence.
     If tied, keep both and flag for review.

Each match record includes a nested_in field (null if top-level,
or the entity_id of the containing match if nested).

Match record:

{
  "line_uid": "...",
  "entity_id": "ALLAH",
  "matched_form": "ਅਲਾਹੁ",
  "span": [12, 18],
  "rule_id": "alias_exact",
  "confidence": "HIGH",
  "ambiguity": null,
  "nested_in": null
}

Confidence levels:

HIGH    — unambiguous match (unique surface form, e.g., ਅਲਾਹੁ -> ALLAH)
MEDIUM  — match is valid but surface form has known polysemy
LOW     — match depends on context (flagged for review)

Ambiguity record (when confidence < HIGH):

"ambiguity": {
  "alternative_entities": ["RAM_DIVINE", "RAM_NARRATIVE"],
  "disambiguation_rule": null
}

Ambiguity is populated from lexicon/polysemy.yaml.
disambiguation_rule is filled by Phase 3 if context resolves it.

4.4 Outputs

matches.jsonl

entity_counts.csv

entity_counts_by_author.csv

entity_counts_by_raga.csv

entity_counts_by_ang_bucket.csv

entity_counts_by_shabad.csv

Concordance exports

web_bundle/aggregates.json

Normalized metrics:

Per 1,000 lines

Per 10,000 tokens

Per 100 shabads

5. Phase 2 — Structural Analysis

Inputs:
  data/corpus/ggs_lines.jsonl     (from Phase 0)
  data/derived/matches.jsonl      (from Phase 1)
  lexicon/*.yaml                  (for register classification)

Outputs:
  data/derived/features.jsonl
  data/web_bundle/cooccurrence.json

Phase 2 does NOT re-run matching. It consumes Phase 1's match results
and classifies them by register using lexicon metadata.

Compute per-line feature vector.

Each feature is a continuous density score (0.0-1.0) = count / total_tokens.
Boolean convenience fields derived as density > 0.

perso_arabic_density
sanskritic_density
nirgun_density
sagun_narrative_density
ritual_density
cleric_density

Feature record:

{
  "line_uid": "...",
  "shabad_uid": "...",
  "token_count": 18,
  "features": {
    "perso_arabic":      {"count": 3, "density": 0.167, "matched_tokens": ["ਅਲਾਹ", "..."]},
    "sanskritic":        {"count": 0, "density": 0.0,   "matched_tokens": []},
    "nirgun":            {"count": 2, "density": 0.111, "matched_tokens": ["..."]},
    "sagun_narrative":   {"count": 0, "density": 0.0,   "matched_tokens": []},
    "ritual":            {"count": 1, "density": 0.056, "matched_tokens": ["..."]},
    "cleric":            {"count": 0, "density": 0.0,   "matched_tokens": []}
  }
}

5.1 Co-occurrence Matrix

Co-occurrence definition:

Two entities co-occur when they appear in the same WINDOW.

Window levels (all computed):

LINE:   same line (tightest, most conservative)
SHABAD: same shabad (captures thematic co-occurrence)

Pair computation:

For each window, collect set of unique entity_ids.
For each pair (A, B) where A < B (alphabetical, avoid double-count):
  Increment raw co-occurrence count.

Metrics per pair:

raw_count:       number of windows containing both A and B
pmi:             pointwise mutual information = log2(P(A,B) / (P(A) * P(B)))
normalized_pmi:  pmi / -log2(P(A,B))    (bounded to [-1, 1])
jaccard:         |windows with both| / |windows with either|

Output matrix is sparse (only pairs with raw_count >= 2).

PMI stability measures:

Minimum entity frequency: entities appearing fewer than min_entity_freq
times in the corpus are excluded from co-occurrence computation entirely.
Default: 10 occurrences. Prevents rare entities from producing
extreme PMI values.

Laplace smoothing: add-k smoothing (default k=1) applied to all
frequency counts before PMI computation.
Smoothed PMI = log2((count(A,B) + k) * N / ((count(A) + k*V) * (count(B) + k*V)))
where V = number of unique entities, N = number of windows.

Minimum co-occurrence for PMI reporting: raw_count >= 5.
(raw_count >= 2 still stored in data; PMI only reported for >= 5.)
Pairs with 2-4 co-occurrences get raw_count and jaccard but PMI = null.

Config:

cooccurrence:
  min_entity_freq: 10
  smoothing_k: 1
  min_pmi_support: 5

Cross-tradition pairing:

Filter pairs where A.tradition != B.tradition.
Rank by normalized PMI.
This surfaces the most distinctive cross-tradition associations.

Ritual + negation patterns:

Special co-occurrence: ritual_marker + negation token in same line.
Uses a small negation lexicon (ਨਾ, ਨਾਹੀ, ਬਿਨੁ, ਬਾਝੁ, etc.).
Captures the GGS's critique-of-ritual pattern quantitatively.

Output:

web_bundle/cooccurrence.json

5.2 Register Density

Compute:

Sanskritic density

Perso-Arabic density

These are direct aggregations of per-line density scores
(mean, median, std) rather than proportions of boolean flags.

Conditioned by:

Author

Raga

Ang progression

Windowed analysis:

Sliding window of W angs (configurable, default 20).
Compute rolling mean density per register.
Enables visualization of register shifts across the text.

5.3 Statistical Guardrails

Log-odds ratio (with smoothing prior)

Bootstrap confidence intervals

Minimum support threshold (e.g., >= 20)

Rank by effect size and support

Explicitly labeled "descriptive distinctiveness"

No causal claims.

6. Phase 3 — Interpretive Tagging

Inputs:
  data/corpus/ggs_lines.jsonl     (from Phase 0)
  data/derived/matches.jsonl      (from Phase 1, for entity context)
  data/derived/features.jsonl     (from Phase 2, for density scores)
  config/config.yaml              (tagging rules and thresholds)

Outputs:
  data/derived/tags.jsonl
  data/reports/nirgun_sagun_distribution.csv

6.1 Score Computation

Each dimension score is computed from Phase 1 matches and Phase 2 features
for the line (and optionally its shabad context).

Score formula per dimension D for line L:

  raw_signal(D, L) = sum of weights for all rules that fire on L for dimension D
  context_signal(D, L) = mean(raw_signal(D, neighbor)) for neighbors in same shabad
  combined(D, L) = (1 - context_weight) * raw_signal + context_weight * context_signal
  score(D, L) = sigmoid(combined(D, L))

  context_weight is configurable (default: 0.2)
  sigmoid: 1 / (1 + exp(-k * (x - x0)))
    k (steepness) and x0 (midpoint) are configurable per dimension

Rules and weights are defined in config:

tagging:
  context_weight: 0.2
  dimensions:
    nirgun:
      sigmoid_k: 2.0
      sigmoid_x0: 1.5
      rules:
        - match_entity: [WAHEGURU, NIRANKAR, FORMLESS_EPITHETS]
          weight: 1.0
        - match_register: sanskritic
          weight: 0.3
        - has_negation_of_form: true
          weight: 0.8
    sagun_narrative:
      sigmoid_k: 2.0
      sigmoid_x0: 1.5
      rules:
        - match_entity: [RAM_NARRATIVE, KRISHNA_NARRATIVE, SHIVA]
          weight: 1.0
        - match_register: perso_arabic
          weight: 0.0
    critique_ritual:
      sigmoid_k: 2.5
      sigmoid_x0: 1.0
      rules:
        - match_entity: [RITUAL_MARKERS]
          weight: 0.5
        - co_occurs_negation: true
          weight: 1.5

6.2 Taxonomy (derived from continuous scores)

Tag record:

{
  "line_uid": "...",
  "scores": {
    "nirgun":          0.82,
    "sagun_narrative": 0.05,
    "universalism":    0.45,
    "critique_ritual": 0.70,
    "critique_clerics": 0.0
  },
  "primary_tag": "nirgun_leaning",
  "secondary_tags": ["critique_ritual"],
  "rules_fired": ["..."],
  "evidence_tokens": ["..."],
  "score_breakdown": {
    "nirgun": [
      {"rule": "match_entity:WAHEGURU", "weight": 1.0, "matched": "ਵਾਹਿਗੁਰੂ"},
      {"rule": "has_negation_of_form", "weight": 0.8, "matched": "ਰੂਪੁ ਨ ਰੇਖ"}
    ],
    "critique_ritual": [
      {"rule": "co_occurs_negation:RITUAL", "weight": 1.5, "matched": "ਤੀਰਥਿ...ਨਾ"}
    ]
  }
}

Category derivation (configurable thresholds):

nirgun_leaning:          nirgun > 0.6 AND sagun < 0.3
sagun_narrative_leaning: sagun > 0.6 AND nirgun < 0.3
mixed:                   |nirgun - sagun| < 0.3 AND both > 0.2
universalism:            universalism > 0.5
critique_ritual:         critique_ritual > 0.5
critique_clerics:        critique_clerics > 0.5

Thresholds are explicit config, not buried in code.
Multiple secondary tags can co-occur (a line can be nirgun AND critique_ritual).

Rule-first approach.

Each tag includes:

Rules fired

Evidence tokens

Score breakdown (which rules contributed what weight)

Gold set:

Stratified sampling

Manual annotation

Precision/recall evaluation

Evaluated per-category and per-threshold-boundary.

Outputs:

tags.jsonl

nirgun_sagun_distribution.csv

Tag-based concordances

7. Phase 3.5 — Unsupervised Discovery (Optional)

Topic modeling

Token clustering

Embedding-based clustering

Guardrail:
Clusters are descriptive, not theological claims.

8. Web Bundle Contract

Each full run produces:

data/web_bundle/
  manifest.json
  aggregates.json
  cooccurrence.json
  corpus/
    lines_001_100.json
    lines_101_200.json
    ...
    lines_1401_1430.json
  search_index.json
  lineage.json

Webapp must consume only this bundle.

Concordance data is organized by ang range, not by entity.
Each corpus chunk contains all lines in that ang range with their
matches, features, and tags inlined:

{
  "ang_range": [1, 100],
  "lines": [
    {
      "line_uid": "...",
      "ang": 1,
      "gurmukhi": "...",
      "tokens": ["..."],
      "token_spans": [[0,3], [4,8]],
      "matches": ["..."],
      "features": {"..."},
      "tags": {"..."}
    }
  ]
}

This produces ~15 files instead of ~1000+.
The webapp loads a chunk when the user navigates to an ang in that range.
Entity-specific concordances are computed client-side by filtering
the loaded chunk — no separate entity files needed.

manifest.json schema:

{
  "schema_version": "1.0.0",
  "generated_at": "...",
  "git_commit": "abc123",
  "corpus_stats": {
    "total_angs": 1430,
    "total_lines": 60403,
    "total_tokens": 432891,
    "total_shabads": 5894
  },
  "lexicon_stats": {
    "total_entities": 247,
    "total_aliases": 1893,
    "lexicon_hashes": { "entities": "sha256:...", "..." : "..." }
  },
  "pipeline_versions": {
    "normalizer": "1.2.0",
    "tokenizer": "1.0.0",
    "matcher": "1.1.0",
    "tagger": "1.0.0"
  },
  "artifacts": [
    {"file": "aggregates.json", "sha256": "...", "records": 247}
  ]
}

search_index.json:

Pre-built search index (MiniSearch or Lunr) generated from corpus.
Index fields: gurmukhi, entity matches, author, raga.
Client loads index on first search interaction (lazy).
Index size target: <5MB compressed for full corpus.

lineage.json:

Maps each aggregate/chart to the exact pipeline step, config parameters,
and lexicon files that produced it. Consumed by the webapp's
"How computed" tooltips.

9. Execution & CLI Contract

CLI is a single typer application with subcommands:

ggs corpus extract --config config/config.yaml
ggs corpus validate
ggs corpus cross-validate
ggs analysis lexical --config config/config.yaml
ggs analysis structural --config config/config.yaml
ggs analysis tags --config config/config.yaml
ggs pipeline run --phases 0,1,2,3
ggs lexicon lint
ggs bundle build

All subcommands accept:

--config <path>   (default: config/config.yaml)
--output <dir>
--force
--dry-run
--verbose / -v
--workers N       (parallel workers, default: cpu_count)

Each run emits:

run_manifest.json

Artifact hashes

Record counts

Git commit hash

Wall-clock duration

Error/warning summary

Parallelism strategy:

Phase 0: sequential (rate-limited HTTP, parallelism would violate scraping protocol)
Phase 1: parallel by ang (each ang's lines processed independently)
Phase 2: parallel by ang (features computed per-line, no cross-line dependency)
Phase 3: parallel by shabad (tagging may use shabad-level context)
Bundle:  sequential (aggregation step, fast)

Implementation: concurrent.futures.ProcessPoolExecutor.
Each worker receives a partition of lines and returns results.
Results merged and sorted by line_uid before writing.
Deterministic output regardless of worker count.

10. CI & Reproducibility

GitHub Actions must:

Run unit tests

Run parser regression tests

Run property-based tests (with fixed seed for determinism)

Run lexicon lint

Run smoke pipeline on Ang 1-5 (fixtures only)

Validate JSON schemas of all output artifacts

No CI step scrapes live site.

Dependencies pinned.
Dockerfile provided.

Testing strategy:

Unit tests (pytest):

test_parse.py       — parser regression on fixture HTML
test_normalize.py   — normalization pipeline idempotency, known transforms
test_tokenize.py    — tokenizer edge cases (empty lines, all-punctuation, etc.)
test_match.py       — must-match and must-not-match fixtures
test_features.py    — feature computation on known lines
test_tagger.py      — rule firing on known lines, threshold boundary cases

Property-based tests (hypothesis):

test_properties.py:
  Normalization is idempotent: normalize(normalize(x)) == normalize(x)
  Tokenization roundtrip: " ".join(tokenize(line)) approximates line (modulo vishram)
  Match spans are valid: all spans fall within gurmukhi string length
  Match spans align to token_spans boundaries
  Match spans don't partially overlap for the same entity
  Feature densities are in [0.0, 1.0]
  Feature densities sum correctly: density = count / token_count

Roundtrip tests:

test_roundtrip.py:
  Full pipeline on fixture corpus (Ang 1-5) produces deterministic output
  Running pipeline twice produces byte-identical artifacts
  JSON schema validation on all output artifacts

11. Publication Strategy

Code: MIT / Apache 2.0
Data: GitHub Releases
Raw HTML snapshots optional

Include:

NOTICE.md

Reproduction instructions

Checksums

12. Quality Bar

Project succeeds if:

Rebuild from scratch produces identical corpus

All counts link to Gurmukhi lines

Statistical claims include uncertainty

Interpretive claims include rule evidence

No silent data loss occurs

Polysemous matches are flagged, not silently conflated

Normalization pipeline is idempotent and version-tracked

Co-occurrence PMI uses smoothing; rare-entity noise is controlled

Pipeline errors are classified, counted, and surfaced — never silently swallowed
