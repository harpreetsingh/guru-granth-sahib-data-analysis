# 10. Key Findings

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Summary

This computational analysis of the entire Guru Granth Sahib (60,629 lines,
396,036 tokens) using a 124-entity theological lexicon across 11 feature
dimensions produces the following quantitative findings.

## The Three Pillars (Headline Finding)

The data reveals three dominant modes of discourse that together account for
**85.2%** of the GGS's theological vocabulary:

| Pillar | Register(s) | % of Lines |
|--------|------------|------------|
| Nirgun theology | nirgun | 42.25% |
| Sanskritic philosophy | sanskritic | 30.21% |
| Devotional-ethical practice | devotional + ethical | 12.70% |

```
Nirgun theology:          42.25%  ████████████████████████████████████████████
Sanskritic philosophy:    30.21%  ██████████████████████████████
Devotional-ethical:       12.70%  ████████████▋
Everything else:          14.84%  ██████████████▊
```

Everything else -- ritual critique, interfaith engagement, mythological
narrative, identity labeling -- occupies the remaining 14.8%. This framing
structures all subsequent findings.

## Finding 1: The GGS is quantitatively a nirgun text

**42.25% of all lines** contain nirgun-register vocabulary, making it the
dominant theological register by a wide margin. Combined with oneness markers
(2.0%), nearly half the corpus (44.25%) engages with formless, non-dual
theology. Sagun narrative appears in only 0.51% of lines -- a 83:1 ratio.

## Finding 2: HARI is the dominant divine name, not WAHEGURU

HARI (ਹਰਿ) appears **9,341 times** -- 55x as often as WAHEGURU (171 times).
The GGS text uses HARI, NAAM (5,464), GUR (4,774), PRABH (2,647), and RAM
(2,019) as its primary divine vocabulary. WAHEGURU became the primary name
in the later Sikh tradition, not in the scriptural text itself.

## Finding 3: RAM functions as a nirgun name

RAM appears 2,019 times across 1,894 lines. Its co-occurrence profile is
overwhelmingly nirgun: NAAM (547), HARI (399), GUR (139), PRABH (91). It
co-occurs with sagun narrative entities only 7 times (ang-level), compared
to 27 nirgun co-occurrences. **RAM in the GGS behaves statistically as a
synonym for the formless divine, not as a reference to the Ramayana prince.**

## Finding 4: The ethical dimension is larger than the ritual dimension

**5.46% of lines** contain ethical vocabulary (Five Thieves + virtues),
compared to 2.20% for ritual references. The GGS devotes 2.5x more textual
space to inner moral psychology (ego, attachment, anger, greed, compassion,
contentment) than to ritual practice (pilgrimage, fire ritual, idol worship).
This supports reading the GGS as primarily an ethical-philosophical text.

## Finding 5: The devotional dimension is the third pillar

**7.24% of lines** contain devotional vocabulary -- bridal metaphors (Pir,
Kant, Sohagan), love-longing (Birha, Prem), and devotional identity (Bhagat).
This exceeds the ethical dimension alone (5.46%) but is slightly smaller than
ethical and ritual combined (5.46% + 2.20% = 7.66%). Nonetheless, devotional
vocabulary is the single largest non-theological register, confirming the GGS
as a Bhakti text alongside its nirgun theology.

## Finding 6: Perso-Arabic vocabulary occupies 0.29% of the text

Only **174 lines** (0.29%) contain Perso-Arabic register vocabulary. The
civilizational density ratio is **99.9:1** (Sanatan to Islamic). The GGS
expresses its universal theology through overwhelmingly Sanskritic-Punjabi
vocabulary.

## Finding 7: HINDU and TURK almost always appear together

The HINDU-TURK co-occurrence has the **highest PMI (6.174) in the entire
corpus** -- higher than any divine name pair, any mythological cluster, or
any ritual grouping. When the GGS names religious communities, it names
them together. This is not incidental; it is a structural feature of how
the text treats religious identity: always as a paired concept to transcend.

## Finding 8: Guru Arjan dominates the corpus

Guru Arjan (Mahalla 5) contributes **42.9% of all lines** (26,036 of 60,629).
He is the compiler-poet -- both the editor of the GGS and its largest single
contributor. His register profile is broadly representative of the corpus
mean, suggesting his editorial choices shaped the overall character of the text.

## Finding 9: Authors have distinctive register signatures

Each author gravitates toward different dimensions:

| Author | Distinctive Register | Value |
|--------|---------------------|-------|
| Guru Arjan | Largest contributor, corpus-representative | 42.9% of lines |
| Guru Nanak | Most balanced register profile | Engages all 11 dimensions |
| Guru Ram Das | Highest nirgun and sanskritic | 62.27% / 48.97% |
| Guru Amar Das | Highest ethical | 7.31% |
| Guru Tegh Bahadur | Highest devotional and ritual | 11.40% / 6.28% |
| Kabir | Highest identity (names Hindu/Muslim communities), cross-tradition | 0.55% identity |
| Farid | Highest perso_arabic, Sufi voice | 5.70% |
| Ravidas | Highest devotional among Bhagats | 13.89% |

## Finding 10: The Mool Mantar functions as a cohesive unit

Co-occurrence analysis confirms that AJOONI, AKAL, SATNAM, NIRVAIR, NIRBHAU,
and MOORAT form the tightest theological cluster (PMI 2.7-5.0). These
attributes travel together across diverse compositions, not just in the Mool
Mantar itself.

## Finding 11: The GGS is a unique hybrid -- not purely Stoic, Bhakti, or Advaita

The Stoic-Bhakti-Advaita triangle shows:
- **Advaita axis: 44.25%** (nirgun + oneness)
- **Bhakti axis: 7.24%** (devotional)
- **Stoic axis: 5.46%** (ethical)

Every author engages with all three axes in different proportions. The GGS
cannot be reduced to any single philosophical tradition. It is a convergence
text that combines non-dual metaphysics, devotional practice, and ethical
self-discipline into a unique synthesis.

## Finding 12: Register mixing is rare at the line level but systematic at the compositional level

Only **0.12%** of register-carrying lines mix Perso-Arabic and Sanskritic
vocabulary. The GGS achieves its multi-traditional character through
composition-level juxtaposition (the HINDU-TURK PMI of 6.174 confirms they
appear on the same *ang*), not through line-level blending. This is a
deliberate rhetorical strategy, not a limitation.

## Finding 13: ALLAH is exceptionally rare, but contextually significant

ALLAH appears in only **19 lines** (0.03%). Of those, **21% also contain
Indic divine names** -- a co-occurrence rate far higher than chance. When
the GGS does invoke ALLAH, it tends to place the name alongside RAM, HARI,
or nirgun epithets, performing civilizational synthesis at the lexical level.

## Limitations

- The 124-entity lexicon captures theologically significant terms but not
  the full vocabulary of the GGS. 49.7% of lines are "unmarked" by the
  original six-dimension tagging system.
- Co-occurrence is measured at ang level (not shabad level), which is a
  coarser unit than ideal. The corpus lacks shabad boundary markers.
- Density measurements treat all token matches equally regardless of
  grammatical role or semantic context.
- The pipeline performs string matching, not disambiguation. Polysemous
  terms (e.g., ਕਰਮ = karma/action/grace, ਕਾਮ = lust/work, ਜਗ = sacrifice/world,
  ਪਿਰ = beloved/husband, ਮੂਰਤਿ = idol/form) are counted under single entities
  with polysemy flags.
- Author attribution is regex-based and may misattribute lines near
  section boundaries. The 18-author identification covers known Mahalla
  headers and major Bhagats but may miss minor contributors.
