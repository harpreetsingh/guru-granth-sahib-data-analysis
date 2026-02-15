# Computational Theology: What Happens When You Run NLP on a 500-Year-Old Scripture

*A data science perspective on analyzing the Guru Granth Sahib*

---

## The Problem

The Guru Granth Sahib (GGS) is a 1,430-page scripture in Gurmukhi script, composed by 18 authors across two centuries (15th-17th century). It contains 60,629 lines and 396,036 tokens. Scholars have studied it for centuries, but almost always through close reading and theological interpretation.

What happens when you treat it as a corpus and apply computational text analysis?

## The Pipeline

### Architecture

The analysis pipeline is a six-phase system:

1. **Corpus extraction** -- Scrape all 1,430 angs from srigurugranth.com, normalize Unicode Gurmukhi, tokenize
2. **Entity matching** -- Aho-Corasick multi-pattern matching against a 124-entity lexicon (346 aliases)
3. **Feature engineering** -- 11-dimensional feature vector per line (density scoring)
4. **Co-occurrence analysis** -- Ang-level PMI for all entity pairs
5. **Author profiling** -- Regex-based Mahalla header extraction, per-author register density
6. **Semantic analysis** -- Entity co-occurrence networks, cross-tradition detection, composite indices

### Key Technical Decisions

**Why Aho-Corasick, not regex?** With 346 surface forms to match against 60,629 lines, a naive regex approach would be O(patterns * text). Aho-Corasick builds a finite automaton that scans each line once, matching all patterns simultaneously in O(text + matches). This gives us 60,012 matches in under 4 seconds.

**Why exact string matching, not word embeddings?** Gurmukhi is a low-resource language with no pre-trained transformer models that handle the GGS's archaic register. Exact matching against a curated lexicon with known spelling variants is more reliable than embedding-based approaches. We flag polysemous forms (ਕਰਮ = karma/grace/action, ਕਾਮ = lust/work, ਜਗ = sacrifice/world) rather than attempting disambiguation.

**Why density, not boolean presence?** Each line is scored as `entity_count / token_count`, giving a continuous density score in [0, 1]. This is more informative than binary presence -- a line with 3 nirgun entities in 5 tokens (density 0.6) is qualitatively different from a line with 1 nirgun entity in 20 tokens (density 0.05).

**Why PMI, not raw co-occurrence?** Pointwise Mutual Information corrects for base rate. HARI and NAAM co-occur on 1,153 of 1,430 angs -- but they're both extremely common, so this is expected. HINDU and TURK co-occur on only 10 angs -- but they're both extremely rare (~30 occurrences each), so their PMI of 6.174 is the highest in the corpus. PMI surfaces the *surprising* associations, not just the frequent ones.

## The Lexicon: Controlled Vocabulary Design

### Schema

Each entity has:
- `id`: UPPER_SNAKE_CASE identifier
- `canonical_form`: Primary Gurmukhi form
- `aliases`: List of spelling variants with match type (exact)
- `category`: One of 13 categories (divine_name, concept, marker, narrative, place, practice, negation, temporal, ethical, devotional, identity, scriptural, oneness)
- `tradition`: One of 7 values (islamic, vedantic, vaishnava, yogic, bhakti, universal, sikh)
- `register`: One of 4 values (perso_arabic, sanskritic, mixed, neutral)
- `polysemous`: Boolean flag for known ambiguous forms

### Coverage

| Metric | Value |
|--------|-------|
| Entities | 124 |
| Aliases | 346 |
| Matches | 60,012 |
| Unique entities matched | 114 / 124 |
| Lines with matches | 34,712 (57.3%) |
| Corpus coverage | ~1 match per line on average |

### Feature Dimensions

The 11 dimensions are derived from entity metadata, not learned:

| Dimension | Lines Hit | % Corpus |
|-----------|----------|----------|
| nirgun | 25,618 | 42.25% |
| sanskritic | 18,319 | 30.21% |
| devotional | 4,392 | 7.24% |
| ethical | 3,311 | 5.46% |
| ritual | 1,331 | 2.20% |
| oneness | 1,210 | 2.00% |
| cleric | 578 | 0.95% |
| sagun_narrative | 311 | 0.51% |
| scriptural | 298 | 0.49% |
| perso_arabic | 174 | 0.29% |
| identity | 31 | 0.05% |

The dimension distribution follows a power law. The top 2 dimensions account for 72.46% of coverage, while the bottom 5 account for 1.78%.

## Results: What the Numbers Show

### 1. Register Asymmetry

The corpus is overwhelmingly nirgun-Sanskritic. The Sanatan-to-Islamic vocabulary ratio is **99.9:1** (16,677 Sanatan entity hits vs 167 Islamic). The Perso-Arabic register dropped from 0.73% to 0.29% after reclassifying SAHIB (ਸਾਹਿਬ) from perso_arabic to neutral -- a correction that removes a major confound from the earlier analysis.

### 2. RAM Semantic Behavior

This is the most analytically interesting finding. RAM (ਰਾਮ, 2,019 occurrences) has a co-occurrence profile that is statistically indistinguishable from HARI's:

| Co-occurring Entity | With RAM | With HARI |
|--------------------|----------|-----------|
| NAAM | 547 | 1,153 |
| GUR | 139 | 1,074 |
| PRABH | 91 | 823 |
| SATGUR | 57 | 936 |

Both RAM and HARI co-occur overwhelmingly with nirgun-register entities. RAM co-occurs with sagun narrative entities only 7 times (ang-level). This provides computational evidence for the theological claim that "Ram" in the GGS is a nirgun name, not a Ramayana reference.

### 3. Author Register Fingerprints

Each of the 18 authors has a distinctive register density profile. Treating the 11 dimensions as a feature vector, we can characterize each author:

- **Guru Ram Das**: [nirgun=62.27, sanskritic=48.97, devotional=6.90, ethical=6.35, ...] -- the nirgun maximalist
- **Farid**: [nirgun=10.13, perso_arabic=5.70, devotional=8.23, ...] -- the Islamic outlier
- **Ravidas**: [devotional=13.89, sanskritic=25.05, nirgun=19.58, ...] -- the devotional peak

The register vectors could serve as input features for author attribution models or stylistic clustering.

### 4. Co-occurrence Network Structure

With 2,687 entity pairs at count >= 5, the co-occurrence network reveals several distinct clusters:

**Cluster 1 -- Mool Mantar:** AJOONI-AKAL-SATNAM-NIRVAIR-NIRBHAU-MOORAT (PMI 2.7-5.0). This is the tightest cluster, reflecting the GGS's opening declaration.

**Cluster 2 -- Islamic vocabulary:** MULLAH-QAZI, HAJI-KHUDA, ALLAH-KHUDA (PMI 4.2-5.3). These terms form a self-contained semantic neighborhood.

**Cluster 3 -- Identity:** HINDU-TURK (PMI 6.174), HINDU-QAZI (4.66), HINDU-KHUDA (3.63). Religious identity terms always co-occur, suggesting deliberate parallel treatment.

**Cluster 4 -- Hindu mythology:** BISN-BRAHMA (4.4), BISN-SHIV (3.0), INDR-SHIV (2.9). Mythological figures appear as constellations (the Trimurti).

**Cluster 5 -- Scriptural references:** SHASTAR-SIMRIT (3.6), PURAN-SIMRIT (3.0), PURAN-SHASTAR (2.6). Scriptures are cited as groups.

### 5. Cross-Register Mixing

The register mixing rate is **0.12%** -- only 22 lines in 60,629 contain both Perso-Arabic and Sanskritic vocabulary. This is far below what random co-occurrence would predict (expected: ~52 lines given the base rates).

This means the GGS achieves its multi-traditional character through *composition-level* juxtaposition, not *line-level* blending. The Bhagats and Gurus work within one register at a time and switch between compositions.

### 6. The Composite Triangle

Mapping each author onto a Stoic-Bhakti-Advaita triangle (using ethical, devotional, and nirgun+oneness dimensions):

| Author | Stoic | Bhakti | Advaita |
|--------|-------|--------|---------|
| Guru Ram Das | 6.35% | 6.90% | 63.57% |
| Guru Amar Das | 7.31% | 7.73% | 55.38% |
| Sundar | 7.83% | 3.69% | 53.23% |
| Guru Nanak | 4.28% | 6.21% | 39.88% |
| Ravidas | 4.21% | 13.89% | 22.32% |
| Farid | 1.27% | 8.23% | 10.13% |

The triangle shows that the GGS is primarily Advaita-adjacent (non-dual), with Bhakti and Stoic dimensions that vary by author.

## Methodological Notes

### What This Analysis Can and Cannot Do

**Can:** Count entities, measure density, compute co-occurrence, identify register, profile authors, detect cross-tradition lines.

**Cannot:** Disambiguate polysemy (ਕਰਮ as karma vs. grace), detect sarcasm or irony, understand grammatical function, assess poetic quality, determine authorial intent.

### Polysemy Problem

Five entities are flagged as polysemous:
- KARAM (ਕਰਮ): karma, action, or divine grace
- KAAM (ਕਾਮ): lust or work
- YAGYA (ਜਗ): sacrifice or world
- PIR (ਪਿਰ): beloved/husband-lord or Sufi saint
- MOORAT (ਮੂਰਤਿ): idol or form (as in ਅਕਾਲ ਮੂਰਤਿ)

These are counted under single entities with polysemy flags. A disambiguation layer would require contextual embedding models trained on Gurmukhi, which don't currently exist at the quality level needed.

### Limitations

1. **Ang-level co-occurrence** is coarser than ideal. The corpus lacks shabad (hymn) boundary markers, so we use ang (page) as the co-occurrence unit. This inflates co-occurrence counts for common entities.

2. **Author attribution** is regex-based and may misattribute lines near section boundaries. The 18-author identification covers known Mahalla headers and major Bhagats.

3. **Coverage ceiling**: 57.3% of lines match at least one entity, meaning 42.7% of lines contain no recognized entities. The lexicon is deliberately focused on theologically significant terms, not exhaustive vocabulary.

4. **No syntactic analysis**: Density measures treat all matches equally regardless of grammatical role. A negation like "ਨਾ ਕੋਈ ਹਿੰਦੂ" (no one is Hindu) and an assertion would be treated identically.

## Reproducibility

The pipeline is fully deterministic:
- All source text is preserved in Unicode Gurmukhi
- The lexicon is version-controlled YAML
- Matching uses Aho-Corasick (deterministic, no randomness)
- PMI uses standard formula with Laplace smoothing
- Author extraction uses fixed regex patterns
- All results are traceable to specific lines and entities

Running the pipeline twice produces identical output. The full analysis completes in under 4 seconds on a modern laptop.

## What's Next

This analysis provides the ground truth for several potential extensions:

1. **Shabad boundary detection** would enable finer-grained co-occurrence analysis
2. **Raga-level profiling** would reveal whether musical setting correlates with register
3. **Temporal drift analysis** across the Guru succession (Mahalla 1 through 9)
4. **Gurmukhi embedding model** trained on the GGS corpus for polysemy disambiguation
5. **Interactive visualization** -- a web application for exploring the corpus with entity highlighting and co-occurrence graphs

---

*Built with Python 3.14, Aho-Corasick multi-pattern matching, 124-entity curated lexicon, 11-dimensional feature engineering. Full source and data available at [the project repository].*
