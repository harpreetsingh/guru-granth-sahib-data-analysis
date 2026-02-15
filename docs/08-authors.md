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

### The Six Gurus

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

| Dimension | Kabir | Ravidas | Farid | Namdev | Trilochan |
|-----------|-------|---------|-------|--------|-----------|
| Lines | 4,187 | 475 | 158 | 257 | 86 |
| nirgun | 21.04% | 19.58% | 10.13% | 19.46% | 16.28% |
| sanskritic | 24.15% | 25.05% | 6.33% | 22.18% | 29.07% |
| devotional | 7.86% | **13.89%** | 8.23% | 11.28% | 9.30% |
| ethical | 2.87% | 4.21% | 1.27% | 3.50% | 3.49% |
| oneness | 2.77% | 2.74% | 0.00% | 1.95% | 0.00% |
| ritual | 2.17% | 2.74% | 1.27% | 0.78% | 2.33% |
| cleric | 1.65% | 0.84% | 0.00% | 0.78% | 0.00% |
| scriptural | 0.72% | 0.63% | 0.00% | 0.39% | 0.00% |
| sagun_narrative | 1.34% | 0.63% | 0.00% | 1.95% | 2.33% |
| perso_arabic | **1.43%** | 0.00% | **5.70%** | 0.39% | 0.00% |
| identity | **0.55%** | 0.00% | 0.00% | 0.00% | 0.00% |

### Minor Bhagats

| Author | Lines | Top Entity | 2nd Entity | 3rd Entity |
|--------|-------|------------|------------|------------|
| Beni | 99 | SATGUR (4) | RAM (4) | RAHAU (4) |
| Ramanand | 44 | SATGUR (4) | RAHAU (4) | BRAHM (3) |
| Sain | 34 | HARI (10) | PRABH (5) | NANAK (4) |
| Jaidev | 16 | SATGUR (1) | RAM (1) | NAAM (1) |
| Bhikhan | 16 | HARI (2) | RAHAU (2) | NA_NEGATION (2) |
| Parmanand | 11 | NAAM (2) | JAP (2) | HARI (2) |

The six minor Bhagats collectively contribute 220 lines (0.36% of the corpus).
Their small corpora make register profiling unreliable, but their top entities
consistently reflect the nirgun vocabulary (HARI, NAAM, SATGUR, RAM) that
dominates the GGS as a whole.

### Sundar (Narrative Contributor)

| Dimension | Sundar |
|-----------|--------|
| Lines | 434 |
| nirgun | 50.23% |
| sanskritic | 37.33% |
| devotional | 3.69% |
| ethical | 7.83% |
| oneness | 3.00% |
| ritual | 4.61% |
| cleric | 2.30% |
| scriptural | 1.38% |
| sagun_narrative | 2.30% |
| perso_arabic | 0.00% |
| identity | 0.00% |

Sundar is not a Bhagat in the traditional sense. He was a relative of Guru Ram
Das who narrated the passing of the Guruship in the composition "Ramkali Sadd"
(Ang 923). His 434 lines are a single narrative work, not independent
theological compositions.

## Author Distinctiveness

### Guru Arjan: The Compiler-Poet

Guru Arjan (Mahalla 5) contributes **42.9% of all lines** (26,036 of 60,629),
making him by far the largest single author. As both the compiler of the Adi
Granth (1604) and its most prolific contributor, his register profile is broadly
representative of the corpus mean: nirgun (39.92%), sanskritic (29.58%),
devotional (7.47%), ethical (5.59%). His top entities -- HARI (3,061), NANAK
(2,567), NAAM (1,946), PRABH (1,781), GUR (1,762) -- mirror the overall
corpus rankings. This is not coincidental: his editorial choices shaped the
character of the text as a whole. His absence from 6 of the 10 rarest ragas
(by size) suggests he concentrated his compositions in the major ragas.

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
-- RABB, KHUDA -- alongside devotional-longing vocabulary (KANT, BIRHA = 5
occurrences in only 158 lines). Note: KANT (beloved/husband) is a devotional
term, not Perso-Arabic. His register is distinctively Sufi-Islamic rather
than Sanskritic.

### Ravidas: The Devotional Maximalist

Ravidas shows the **highest devotional density (13.89%)** of any author in
the entire corpus. His 475 lines are rich in BHAGAT (23), NAAM (31), RAHAU
(41), and IK (12). His compositions represent the most intensely devotional
voice in the GGS.

## Top Entities by Author

### Guru Arjan's Top 5
1. HARI (3,061)
2. NANAK (2,567)
3. NAAM (1,946)
4. PRABH (1,781)
5. GUR (1,762)

### Guru Ram Das's Top 5
1. HARI (3,663) -- 52.3% of all his lines
2. NAAM (1,009)
3. GUR (877)
4. NANAK (714)
5. SATGUR (695)

### Guru Amar Das's Top 5
1. HARI (1,488)
2. NAAM (1,159)
3. GUR (1,032)
4. SACH (880)
5. SABAD (801)

### Guru Nanak's Top 5
1. NAAM (991)
2. GUR (846)
3. NANAK (775)
4. HARI (730)
5. NA_NEGATION (576)

### Guru Tegh Bahadur's Top 5
1. NANAK (114)
2. HARI (64)
3. RAHAU (62)
4. RAM (55)
5. NAAM (36)

### Kabir's Top 5
1. RAHAU (256)
2. NA_NEGATION (252)
3. RAM (237)
4. HARI (219)
5. NAAM (150)

### Ravidas's Top 5
1. RAHAU (41)
2. NAAM (31)
3. BHAGAT (23)
4. HARI (23)
5. SATGUR (21)

### Farid's Top 5
1. NA_NEGATION (12)
2. BIRHA (5)
3. RAHAU (4)
4. KANT (4)
5. SACH (3)

Note: Farid's low absolute counts reflect his small corpus (158 lines), but
the relative density of devotional-longing vocabulary (BIRHA, KANT, PIR) is
the highest in the GGS.
