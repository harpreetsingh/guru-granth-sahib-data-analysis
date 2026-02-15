# 3. Feature Dimensions

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## The Three Pillars of the GGS

The data reveals three dominant modes of discourse that together define the
character of the Guru Granth Sahib:

1. **Nirgun theology (42.25%)** -- The formless divine, Naam, Sabad, Guru.
   Nearly half the text is explicitly about a God who has no form, no image,
   no incarnation.
2. **Sanskritic philosophy (30.21%)** -- Deep engagement with Vedantic concepts
   (Maya, Brahm, Atma, Karam, Mukti). The Gurus did not reject Vedantic
   philosophy -- they engaged with it deeply and recontextualized it within
   a nirgun framework.
3. **Devotional-ethical practice (12.7%)** -- Love/longing/surrender (7.24%)
   combined with inner moral struggle (5.46%). The GGS is simultaneously a
   philosophical treatise *and* a collection of love songs, grounded in
   ethical self-discipline.

Together these three pillars account for **85.2%** of the GGS's theological
vocabulary. Ritual critique, interfaith engagement, and mythological narrative
serve as important but quantitatively minor registers.

## Eleven-Dimensional Register Analysis

Each line in the corpus is scored across eleven feature dimensions based on the
presence and density of entities belonging to each category. Density is computed
as `entity_count / token_count` for each line.

## Results

| Dimension | Total Hits | Lines Hit | % of Corpus | Avg Density | Max Density |
|-----------|-----------|-----------|-------------|-------------|-------------|
| nirgun | 39,857 | 25,618 | 42.25% | 0.0938 | 1.0 |
| sanskritic | 25,564 | 18,319 | 30.21% | 0.0590 | 1.0 |
| devotional | 4,592 | 4,392 | 7.24% | 0.0111 | 0.67 |
| ethical | 3,829 | 3,311 | 5.46% | 0.0094 | 0.80 |
| ritual | 1,439 | 1,331 | 2.20% | 0.0034 | 1.0 |
| oneness | 1,379 | 1,210 | 2.00% | 0.0035 | 0.75 |
| cleric | 616 | 578 | 0.95% | 0.0016 | 0.50 |
| sagun_narrative | 337 | 311 | 0.51% | 0.0009 | 0.50 |
| scriptural | 398 | 298 | 0.49% | 0.0011 | 1.0 |
| perso_arabic | 195 | 174 | 0.29% | 0.0005 | 0.50 |
| identity | 42 | 31 | 0.05% | 0.0001 | 0.50 |

## Interpretation

**Nirgun vocabulary is pervasive.** 42.25% of all lines contain at least one
nirgun-register entity (names for the formless divine, core Sikh concepts).
This makes nirgun the dominant theological register of the GGS by a wide margin.

**Sanskritic vocabulary is the second-largest register** at 30.21%. This
includes Vedantic concepts (Maya, Brahm, Gian, Karam, Mukti), divine names
from Indic traditions (Hari, Ram, Prabh, Gobind), and yogic/ascetic terminology
(Jogi, Teerath).

**Devotional vocabulary (7.24%) is the third-largest dimension** -- a new finding
from the expanded lexicon. Nearly 1 in 14 lines contains love/longing vocabulary:
bridal metaphors (Pir, Kant, Sohagan), separation-longing (Birha), devotional
surrender (Bhagat, Prem). This quantifies the Bhakti character of the text.

**Ethical vocabulary (5.46%) is substantial.** Over 1 in 18 lines references
inner moral life -- the Five Thieves (Haumai, Kaam, Krodh, Lobh, Moh, Ahankar)
or cardinal virtues (Daya, Santokh, Nimrata, Seva). This is significant: the GGS
devotes more textual space to ethical-psychological concerns than to ritual (2.2%),
cleric critique (0.95%), or interfaith engagement (0.29%) combined.

**Oneness markers (2.0%)** capture non-duality language: ਇਕੋ (the One), ਏਕ (One),
ਜੋਤਿ (divine light pervading all). These lines assert the collapse of metaphysical
duality -- a key Advaita-adjacent theme in the GGS.

**Perso-Arabic is the second-rarest register at 0.29%.** After reclassifying
SAHIB from perso-arabic to neutral (its actual usage is register-neutral), the
true Perso-Arabic register drops to under 1 in 300 lines. This is consistent
with the GGS being primarily composed in a Sanskritic-Punjabi register, with
selective Perso-Arabic borrowings concentrated in specific compositions.

**Identity vocabulary is the rarest dimension (0.05%).** Only 31 lines in the
entire corpus contain explicit religious identity labels (Hindu, Musalman, Turk).
The GGS almost never names religious communities directly.

## Density Comparison

```
nirgun:          0.0938  ████████████████████████████████████████████████
sanskritic:      0.0590  ██████████████████████████████
devotional:      0.0111  █████▌
ethical:         0.0094  ████▋
oneness:         0.0035  █▊
ritual:          0.0034  █▋
cleric:          0.0016  ▊
scriptural:      0.0011  ▌
sagun_narrative: 0.0009  ▍
perso_arabic:    0.0005  ▎
identity:        0.0001  ▏
```

Nirgun density is 188x higher than Perso-Arabic density and 938x higher than
identity density. The GGS is, quantitatively, overwhelmingly a nirgun text
that draws heavily on Sanskritic philosophical vocabulary, with significant
devotional and ethical dimensions.

## Summary

The Three Pillars framework (detailed at the top of this page) is the key
takeaway: nirgun theology (42.25%), Sanskritic philosophy (30.21%), and
devotional-ethical practice (12.7%) account for 85.2% of the GGS's theological
vocabulary.
