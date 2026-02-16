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
| unmarked | 30,131 | 49.69% |
| nirgun_leaning | 25,535 | 42.12% |
| sanskritic_register | 3,547 | 5.85% |
| ritual_reference | 585 | 0.96% |
| cleric_reference | 412 | 0.68% |
| sagun_narrative | 228 | 0.38% |
| perso_arabic_register | 97 | 0.16% |
| mixed_nirgun_sagun | 83 | 0.14% |
| critique_both | 9 | 0.01% |
| mixed_register | 2 | <0.01% |

## Feature Presence (Secondary Markers)

These counts show how many lines have *any* presence of each feature,
regardless of primary tag assignment.

| Marker | Lines | % of Corpus |
|--------|-------|-------------|
| has_nirgun | 25,618 | 42.25% |
| has_sanskritic | 18,319 | 30.21% |
| has_devotional | 4,392 | 7.24% |
| has_ethical | 3,311 | 5.46% |
| has_ritual | 1,331 | 2.20% |
| has_oneness | 1,210 | 2.00% |
| has_cleric | 578 | 0.95% |
| has_sagun_narrative | 311 | 0.51% |
| has_scriptural | 298 | 0.49% |
| has_perso_arabic | 174 | 0.29% |
| has_identity | 31 | 0.05% |

## Interpretation

**49.7% of lines are "unmarked"** -- they contain no entities from the original
six register dimensions used in the tagging hierarchy. This has dropped from
56.6% (70-entity lexicon) because the expanded 124-entity lexicon now captures
ethical, devotional, oneness, scriptural, and identity vocabulary that was
previously invisible.

**Important caveat:** The tagging hierarchy only uses the original 6 dimensions
(nirgun, sanskritic, sagun_narrative, ritual, cleric, perso_arabic). The 5 newer
dimensions (devotional, ethical, oneness, scriptural, identity) are measured in
the Feature Presence table above but do **not** affect primary tag assignment.
A line with strong devotional or ethical content but no nirgun/sagun/ritual/cleric
markers will be tagged "unmarked."

**42.1% are nirgun-leaning** -- the single largest tagged category (up from
38.1% with the 70-entity lexicon). This confirms the GGS as primarily a
nirgun text: over two-fifths of all lines contain vocabulary associated with
the formless, attributeless divine.

**5.85% are purely sanskritic** (without nirgun overlap), up from 3.35%
(70-entity lexicon). The expanded Sanskritic lexicon now captures additional
scriptural references (Ved, Puran, Shastar, Simrit), clerical markers
(Brahmin, Siddh), and ritual terms (Moorat, Yagya).

**The mixed_nirgun_sagun tag (83 lines)** identifies lines where incarnation
mythology and nirgun theology coexist -- theologically significant passages
where the Gurus use narrative to serve nirgun teaching. This is up from 66
lines, reflecting the expanded sagun_narrative lexicon (now includes Sita,
Dasrath, Ravan, Valmik, Durga, Lakshmi, Sarasvati, Kans, Gopi, Indr).

**Perso-Arabic-only lines total 97** -- genuinely Islamic/Sufi vocabulary:
Allah, Khuda, Rabb, Maula, Noor, etc.

**The "critique_both" tag (9 lines)** captures rare passages where both ritual
and cleric vocabulary appear on the same line -- direct simultaneous critique
of both institutional religion and empty ritual.
