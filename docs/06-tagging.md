# 6. Interpretive Tagging

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Method

Each line is assigned a primary interpretive tag based on the presence and
combination of feature dimensions. The tagging logic follows a priority
hierarchy:

1. If both nirgun AND sagun_narrative features are present: `mixed_nirgun_sagun`
2. If nirgun only: `nirgun_leaning`
3. If sagun_narrative only: `sagun_narrative`
4. If both ritual AND cleric: `critique_both`
5. If ritual only: `ritual_reference`
6. If cleric only: `cleric_reference`
7. If both perso_arabic AND sanskritic: `mixed_register`
8. If perso_arabic only: `perso_arabic_register`
9. If sanskritic only: `sanskritic_register`
10. Otherwise: `unmarked`

## Primary Tag Distribution

| Tag | Lines | % of Corpus |
|-----|-------|-------------|
| unmarked | 34,328 | 56.62% |
| nirgun_leaning | 23,087 | 38.08% |
| sanskritic_register | 2,034 | 3.35% |
| cleric_reference | 342 | 0.56% |
| ritual_reference | 325 | 0.54% |
| perso_arabic_register | 261 | 0.43% |
| sagun_narrative | 179 | 0.30% |
| mixed_nirgun_sagun | 66 | 0.11% |
| critique_both | 7 | 0.01% |

## Feature Presence (Secondary Markers)

These counts show how many lines have *any* presence of each feature,
regardless of primary tag assignment.

| Marker | Lines | % of Corpus |
|--------|-------|-------------|
| has_nirgun | 23,153 | 38.19% |
| has_sanskritic | 15,630 | 25.78% |
| has_ritual | 841 | 1.39% |
| has_cleric | 460 | 0.76% |
| has_perso_arabic | 441 | 0.73% |
| has_sagun_narrative | 245 | 0.40% |

## Interpretation

**56.6% of lines are "unmarked"** -- they contain no entities from our lexicon.
This is expected: many lines consist of narrative connectives, emotional
expressions, or vocabulary not covered by the 70-entity lexicon. The lexicon
is deliberately focused on theologically significant terms, not exhaustive
vocabulary.

**38.1% are nirgun-leaning** -- the single largest tagged category. This
confirms the GGS as primarily a nirgun text: over a third of all lines
contain vocabulary associated with the formless, attributeless divine.

**Only 3.35% are purely sanskritic** (without nirgun overlap). Most sanskritic
vocabulary (Vedantic concepts like Maya, Brahm, Karam) appears *alongside*
nirgun terms, reflecting the GGS's strategy of engaging with Indic philosophy
while reinterpreting it through a nirgun lens.

**The "critique_both" tag (7 lines)** captures extremely rare passages where
both ritual and cleric vocabulary appear on the same line -- direct
simultaneous critique of both institutional religion and empty ritual.

**Mixed nirgun+sagun (66 lines)** identifies lines where incarnation mythology
and nirgun theology coexist -- theologically significant passages where the
Gurus use narrative to serve nirgun teaching.
