# 9. Semantic Analysis

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## RAM: Nirgun or Sagun?

One of the most contested questions in Sikh studies: when the GGS says "Ram"
(ਰਾਮ), does it mean the epic hero of the Ramayana (sagun) or the formless
Absolute (nirgun)?

### The Data

| Metric | Value |
|--------|-------|
| Total RAM matches | 2,019 |
| Unique lines containing RAM | 1,894 |
| RAM lines with nirgun co-occurrence | 27 ang-level |
| RAM lines with sagun co-occurrence | 7 ang-level |
| Nirgun-to-sagun ratio | **3.86:1** |

### Top Co-occurring Entities with RAM

| Entity | Co-occurrences | Register |
|--------|---------------|----------|
| NAAM | 547 | nirgun |
| HARI | 399 | nirgun |
| NANAK | 146 | nirgun |
| GUR | 139 | nirgun |
| RAHAU | 121 | devotional |
| PRABH | 91 | nirgun |
| JAP | 70 | ritual |
| BHAGAT | 67 | devotional |
| BINU_NEGATION | 63 | -- |
| NA_NEGATION | 59 | -- |
| SATGUR | 57 | nirgun |
| ATMA | 48 | sanskritic |
| SABAD | 38 | nirgun |
| MAYA | 29 | sanskritic |
| SACH | 23 | nirgun |
| IK | 23 | oneness |
| SAHAJ | 20 | nirgun |
| SEVA | 20 | ethical |
| MOH | 20 | ethical |
| PIR | 19 | devotional |

### Interpretation

**RAM behaves overwhelmingly as a nirgun divine name.** Its top co-occurring
entities are NAAM (547), HARI (399), NANAK (146), GUR (139) -- all nirgun-register
vocabulary. The sagun narrative entities (Krishna, Shiv, Brahma, Sita, Ravan)
co-occur with RAM only 7 times at the ang level, compared to 27 nirgun
co-occurrences.

**RAM's semantic neighborhood is indistinguishable from HARI's.** The top
co-occurring entities for RAM (NAAM, HARI, GUR, PRABH, SATGUR) are the same
entities that co-occur with HARI. This confirms that in the GGS, RAM functions
as a synonym for the formless divine, not as a reference to the Ramayana prince.

**ATMA (48) and MAYA (29) co-occur with RAM** at rates typical of philosophical
discourse, not narrative. RAM appears alongside discussions of the soul and
illusion, not alongside Sita, Hanuman, or Lanka.

## ALLAH: Context Analysis

### The Data

| Metric | Value |
|--------|-------|
| Lines containing ALLAH | 19 |
| ALLAH lines with Indic divine name | 4 (21%) |

### Co-occurring Entities with ALLAH

| Entity | Co-occurrences |
|--------|---------------|
| KHUDA | 3 |
| RAM | 3 |
| ALAKH | 2 |
| NOOR | 2 |
| NA_NEGATION | 1 |
| SAHIB | 1 |
| AGAM | 1 |
| HARI | 1 |
| GUR | 1 |

### Interpretation

**ALLAH appears in only 19 lines** of the 60,629-line corpus (0.03%).
This is extraordinarily rare -- HARI appears 492x more often.

These 19 lines are distributed across 9 ragas:

| Raga | ALLAH Lines |
|------|------------|
| Epilogue | 4 |
| Parbhati | 4 |
| Gauri | 3 |
| Aasaa | 2 |
| Maru | 2 |
| Sri Raag | 1 |
| Tilang | 1 |
| Bhairav | 1 |
| Ramkali | 1 |

No single raga concentrates ALLAH usage -- the references are scattered
across the text, consistent with occasional rather than systematic use.

**21% of ALLAH lines also contain Indic divine vocabulary.** In 4 of 19
appearances, ALLAH co-occurs with RAM (3 times), HARI (1 time), or ALAKH (2
times, a nirgun epithet). These are the "civilizational synthesis" lines --
moments where the text explicitly equates Islamic and Indic divine names.

**ALLAH co-occurs with KHUDA (3 times)** -- the two Islamic divine names tend
to appear together, reinforcing each other. NOOR (divine light, 2 co-occurrences)
suggests a Sufi-mystical context rather than a legalistic-Islamic one.

## Cross-Tradition Lines

### Lines Where Hindu + Muslim Markers Appear Together

| Metric | Value |
|--------|-------|
| Cross-tradition lines | 10 |
| Identity marker lines | 31 |

Only **10 lines** in the entire corpus contain both Hindu-tradition and
Muslim-tradition vocabulary on the same line. These are the rarest and most
structurally significant lines in the GGS -- moments of explicit civilizational
dialogue.

By contrast, **31 lines** contain explicit religious identity labels (Hindu,
Musalman, Turk). The majority of these (21 lines) name only one community,
while 10 name both traditions together.

The HINDU-TURK PMI of 6.174 (highest in the corpus) confirms that when the
GGS names one community, it almost always names both. Religious identity is
structurally treated as a paired concept to be transcended, not a single
target for critique.

## Civilizational Density Index

| Register | Total Entity Hits |
|----------|------------------|
| Sanatan (Indic) markers | 16,677 |
| Islamic markers | 167 |
| **Ratio** | **99.9:1** |

The GGS's civilizational vocabulary is **99.9% Sanatan-derived.** For every
1 Islamic-register entity hit, there are 99.9 Sanatan-register hits. This
includes both sanskritic-philosophical and nirgun-theological vocabulary.

This does not mean the GGS is "Hindu" -- the nirgun theology explicitly
transcends Indic tradition just as it transcends Islamic tradition. But the
*vocabulary* through which this transcendence is expressed is overwhelmingly
drawn from the Sanskritic-Punjabi lexical register.

## Stoic-Bhakti-Advaita Triangle

The GGS can be mapped onto a three-axis framework. **Note:** "Stoic" is used
as an analogy to the Greco-Roman tradition of inner self-mastery, not a claim
of historical derivation. The GGS's ethical dimension parallels Stoic philosophy
(equanimity, detachment, virtue cultivation) but is independently grounded in
South Asian spiritual traditions.

- **Stoic axis (ethical dimension):** Inner moral regulation, Five Thieves,
  virtue cultivation -- 5.46% of lines
- **Bhakti axis (devotional dimension):** Love/longing, bridal metaphor,
  emotional surrender -- 7.24% of lines
- **Advaita axis (nirgun + oneness dimensions):** Non-duality, formless
  divine, collapse of subject-object -- 44.25% of lines (42.25% nirgun
  + 2.0% oneness)

### By Author

| Author | Stoic (ethical) | Bhakti (devotional) | Advaita (nirgun+oneness) |
|--------|----------------|--------------------|-----------------------|
| Guru Nanak | 4.28% | 6.21% | 39.88% |
| Guru Angad | 4.25% | 1.90% | 27.60% |
| Guru Amar Das | **7.31%** | 7.73% | 55.38% |
| Guru Ram Das | 6.35% | 6.90% | **63.57%** |
| Guru Arjan | 5.59% | 7.47% | 41.89% |
| Guru Tegh Bahadur | 5.29% | **11.40%** | 40.82% |
| Kabir | 2.87% | 7.86% | 23.81% |
| Ravidas | 4.21% | **13.89%** | 22.32% |
| Farid | 1.27% | 8.23% | 10.13% |
| Sundar | 7.83% | 3.69% | 53.23% |

### Interpretation

**The GGS is primarily an Advaita-adjacent text** (44.25% of lines), with
significant Bhakti (7.24%) and Stoic (5.46%) dimensions. It is not purely
any of these -- it is a unique hybrid that combines non-dual theology with
devotional practice and ethical self-discipline.

**Guru Ram Das is the most Advaita-leaning** (63.57%), while **Ravidas is
the most Bhakti-leaning** (13.89%). **Guru Amar Das has the strongest
Stoic dimension** (7.31%). Farid is the most distinctly Bhakti with the
lowest Advaita ratio (10.13%), reflecting his Sufi devotional orientation.

The triangle reveals that every author in the GGS engages with all three
axes, but in different proportions. There is no author who is purely Stoic,
purely Bhakti, or purely Advaita. The GGS is a convergence text.
