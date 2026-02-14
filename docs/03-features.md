# 3. Feature Dimensions

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Six-Dimensional Register Analysis

Each line in the corpus is scored across six feature dimensions based on the
presence and density of entities belonging to each register. Density is computed
as `entity_count / token_count` for each line.

## Results

| Dimension | Total Hits | Lines Hit | % of Corpus | Avg Density | Max Density |
|-----------|-----------|-----------|-------------|-------------|-------------|
| nirgun | 34,361 | 23,153 | 38.19% | 0.0806 | 1.0 |
| sanskritic | 20,791 | 15,630 | 25.78% | 0.0473 | 1.0 |
| ritual | 936 | 841 | 1.39% | 0.0023 | 1.0 |
| cleric | 486 | 460 | 0.76% | 0.0013 | 0.5 |
| perso_arabic | 460 | 441 | 0.73% | 0.0012 | 0.5 |
| sagun_narrative | 264 | 245 | 0.40% | 0.0007 | 0.5 |

## Interpretation

**Nirgun vocabulary is pervasive.** 38% of all lines contain at least one
nirgun-register entity (names for the formless divine, core Sikh concepts).
This makes nirgun the dominant theological register of the GGS.

**Sanskritic vocabulary is the second-largest register** at 25.78%. This
includes Vedantic concepts (Maya, Brahm, Gian, Karam, Mukti), divine names
from Indic traditions (Hari, Ram, Prabh, Gobind), and yogic/ascetic terminology
(Jogi, Teerath).

**Ritual, cleric, and Perso-Arabic registers are marginal.** Together they
account for under 3% of lines. This does not mean these themes are unimportant
-- their low frequency makes them stand out when they do appear, often in
compositions that directly engage with Islamic or Hindu ritual practice.

**Sagun (incarnation/mythological) narrative is the rarest register** at 0.40%.
References to Krishna, Shiv, Brahma, and Narad are scattered and typically
appear in compositions that retell mythology to make a theological point,
not as devotional invocations.

## Density Comparison

The average density gap between registers tells the story clearly:

```
nirgun:          0.0806  ████████████████████████████████████████
sanskritic:      0.0473  ███████████████████████▌
ritual:          0.0023  █▏
cleric:          0.0013  ▋
perso_arabic:    0.0012  ▋
sagun_narrative: 0.0007  ▎
```

Nirgun density is 67x higher than Perso-Arabic density and 115x higher than
sagun_narrative density. The GGS is, quantitatively, overwhelmingly a nirgun
text that draws heavily on Sanskritic philosophical vocabulary.
