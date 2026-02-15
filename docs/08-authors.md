# 8. Per-Author Analysis

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Method

Authors were extracted from the corpus using regex-based header detection:

- **Guru attribution:** Pattern `ਮਹਲਾ` + Gurmukhi numeral (੧-੯) maps to the
  corresponding Guru (Mahalla 1 = Guru Nanak, Mahalla 5 = Guru Arjan, etc.)
- **Bhagat attribution:** Short header lines containing known Bhagat names
  (Kabir, Farid, Ravidas, Namdev, etc.) with suffixes like ਜੀਉ, ਜੀ, ਕੀ, ਕਾ
- **Default:** Opening Japji section defaults to Guru Nanak

This yielded **18 distinct authors** across 60,629 lines.

## Register Profiles by Author

The table below shows the percentage of each author's lines that contain
vocabulary from each register dimension. This is the key to understanding
each author's distinctive theological voice.

### The Five Gurus

| Dimension | Guru Nanak | Guru Angad | Guru Amar Das | Guru Ram Das | Guru Arjan | Guru Tegh Bahadur |
|-----------|-----------|-----------|--------------|-------------|-----------|-------------------|
| Lines | 11,230 | 895 | 9,041 | 7,005 | 26,036 | 605 |
| nirgun | 37.35% | 26.59% | 53.67% | **62.27%** | 39.92% | 39.50% |
| sanskritic | 23.54% | 11.17% | 30.26% | **48.97%** | 29.58% | 42.81% |
| devotional | 6.21% | 1.90% | 7.73% | 6.90% | 7.47% | **11.40%** |
| ethical | 4.28% | 4.25% | **7.31%** | 6.35% | 5.59% | 5.29% |
| oneness | 2.53% | 1.01% | 1.71% | 1.30% | 1.97% | 1.32% |
| ritual | 2.55% | 1.68% | 1.71% | 2.94% | 1.89% | **6.28%** |
| cleric | 1.51% | 0.89% | 0.88% | 0.56% | 0.72% | 1.32% |
| scriptural | 0.61% | 0.89% | 0.50% | 0.34% | 0.41% | 0.99% |
| sagun_narrative | 0.54% | 0.34% | 0.38% | 0.54% | 0.36% | 0.99% |
| perso_arabic | 0.28% | 0.56% | 0.01% | 0.13% | 0.22% | 0.00% |
| identity | 0.00% | 0.34% | 0.00% | 0.01% | 0.02% | 0.00% |

### Key Bhagats

| Dimension | Kabir | Ravidas | Farid | Namdev | Trilochan | Sundar |
|-----------|-------|---------|-------|--------|-----------|--------|
| Lines | 4,187 | 475 | 158 | 257 | 86 | 434 |
| nirgun | 21.04% | 19.58% | 10.13% | 19.46% | 16.28% | 50.23% |
| sanskritic | 24.15% | 25.05% | 6.33% | 22.18% | 29.07% | 37.33% |
| devotional | 7.86% | **13.89%** | 8.23% | 11.28% | 9.30% | 3.69% |
| ethical | 2.87% | 4.21% | 1.27% | 3.50% | 3.49% | 7.83% |
| oneness | 2.77% | 2.74% | 0.00% | 1.95% | 0.00% | 3.00% |
| ritual | 2.17% | 2.74% | 1.27% | 0.78% | 2.33% | 4.61% |
| cleric | 1.65% | 0.84% | 0.00% | 0.78% | 0.00% | 2.30% |
| scriptural | 0.72% | 0.63% | 0.00% | 0.39% | 0.00% | 1.38% |
| sagun_narrative | 1.34% | 0.63% | 0.00% | 1.95% | 2.33% | 2.30% |
| perso_arabic | **1.43%** | 0.00% | **5.70%** | 0.39% | 0.00% | 0.00% |
| identity | **0.55%** | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

## Author Distinctiveness

### Guru Ram Das: The Nirgun Maximalist

Guru Ram Das shows the **highest nirgun density (62.27%)** and **highest
sanskritic density (48.97%)** of any author in the corpus. His compositions
are saturated with HARI (3,663 occurrences -- more than double any other Guru
per line), NAAM (1,009), and GUR (877). Nearly two-thirds of his lines
contain nirgun vocabulary. His top entity HARI appears on average once
every 1.9 lines.

### Guru Amar Das: The Ethical Voice

Guru Amar Das shows the **highest ethical density (7.31%)** among the Gurus.
His compositions emphasize inner moral transformation -- SABAD (801), SACH
(880), and SAHAJ (318) dominate his vocabulary. He also has the highest
nirgun density among the first three Gurus at 53.67%.

### Guru Tegh Bahadur: The Devotional-Detachment Philosopher

Guru Tegh Bahadur has the **highest devotional density (11.40%)** and
**highest ritual density (6.28%)** among all Gurus. His compositions uniquely
combine devotional longing with extensive engagement with ritual vocabulary
(YAGYA/ਜਗ appears 26 times). His register profile also shows **zero
Perso-Arabic vocabulary** -- the only Guru with no Islamic register at all.

### Guru Nanak: The Balanced Founder

Guru Nanak's register profile is remarkably balanced. He engages with every
register: nirgun (37.35%), sanskritic (23.54%), devotional (6.21%), ethical
(4.28%), oneness (2.53%), ritual (2.55%), cleric (1.51%), scriptural (0.61%),
sagun (0.54%), and perso_arabic (0.28%). His breadth of engagement sets the
template that subsequent Gurus develop in different directions.

### Kabir: The Cross-Tradition Voice

Kabir shows the **highest Perso-Arabic density among Bhagats (1.43%)** and
the **highest identity marker density (0.55%)**. His compositions are where
Hindu-Muslim vocabulary most frequently appears. He also has the highest
sagun_narrative density (1.34%) among Bhagats, reflecting his engagement
with mythological critique.

### Farid: The Islamic Register

Farid is the only author whose **Perso-Arabic density (5.70%) exceeds his
nirgun density (10.13%)**. His compositions use Islamic vocabulary extensively
-- RABB, KHUDA, KANT -- and show the highest devotional-longing density
among Bhagats (BIRHA = 5 occurrences in only 158 lines). His register is
distinctively Sufi-Islamic rather than Sanskritic.

### Ravidas: The Devotional Maximalist

Ravidas shows the **highest devotional density (13.89%)** of any author in
the entire corpus. His 475 lines are rich in BHAGAT (23), NAAM (31), RAHAU
(41), and IK (12). His compositions represent the most intensely devotional
voice in the GGS.

## Top Entities by Author

### Guru Ram Das's Top 5
1. HARI (3,663) -- 52.3% of all his lines
2. NAAM (1,009)
3. GUR (877)
4. NANAK (714)
5. SATGUR (695)

### Guru Nanak's Top 5
1. NAAM (991)
2. GUR (846)
3. NANAK (775)
4. HARI (730)
5. NA_NEGATION (576)

### Kabir's Top 5
1. RAHAU (256)
2. NA_NEGATION (252)
3. RAM (237)
4. HARI (219)
5. NAAM (150)

### Farid's Top 5
1. NA_NEGATION (12)
2. BIRHA (5)
3. RAHAU (4)
4. KANT (4)
5. SACH (3)

Note: Farid's low absolute counts reflect his small corpus (158 lines), but
the relative density of devotional-longing vocabulary (BIRHA, KANT, PIR) is
the highest in the GGS.
