# 2. Lexical Matching Results

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Summary

| Metric                  | Value         |
|------------------------|---------------|
| Total matches           | 60,012        |
| Unique entities matched | 114 of 124    |
| Lines with matches      | 34,712 (57.3%) |
| Nested matches          | 40            |
| Confidence level        | 100% HIGH     |

Over half of all lines in the Guru Granth Sahib contain at least one
recognized theological/conceptual entity from our 124-entity lexicon.

## Top 40 Entities by Frequency

| # | Entity ID | Gurmukhi | Count | Dimension(s) |
|---|-----------|----------|-------|-------------|
| 1 | HARI | ਹਰਿ | 9,341 | nirgun, sanskritic |
| 2 | NAAM | ਨਾਮੁ | 5,464 | nirgun |
| 3 | NANAK | ਨਾਨਕ | 5,000 | nirgun |
| 4 | GUR | ਗੁਰ | 4,774 | nirgun |
| 5 | RAHAU | ਰਹਾਉ | 2,685 | devotional |
| 6 | PRABH | ਪ੍ਰਭ | 2,647 | nirgun, sanskritic |
| 7 | SATGUR | ਸਤਿਗੁਰ | 2,613 | nirgun |
| 8 | NA_NEGATION | ਨਾ | 2,229 | -- |
| 9 | SACH | ਸਚੁ | 2,196 | nirgun |
| 10 | RAM | ਰਾਮ | 2,019 | nirgun, sanskritic |
| 11 | SABAD | ਸਬਦ | 1,748 | nirgun |
| 12 | BINU_NEGATION | ਬਿਨੁ | 1,656 | -- |
| 13 | BHAGAT | ਭਗਤ | 1,106 | devotional |
| 14 | SAHAJ | ਸਹਜ | 976 | nirgun |
| 15 | IK | ਇਕੋ/ਏਕ | 967 | oneness |
| 16 | MAYA | ਮਾਇਆ | 833 | sanskritic |
| 17 | SEVA | ਸੇਵਾ | 814 | ethical |
| 18 | MOH | ਮੋਹ | 781 | ethical |
| 19 | HAUMAI | ਹਉਮੈ | 627 | ethical |
| 20 | KARAM | ਕਰਮ | 620 | sanskritic |
| 21 | DAYA | ਦਇਆ | 581 | ethical |
| 22 | JAP | ਜਪ | 576 | sanskritic, ritual |
| 23 | GIAN | ਗਿਆਨ | 572 | sanskritic |
| 24 | JOTI | ਜੋਤਿ | 412 | oneness |
| 25 | THAKUR | ਠਾਕੁਰ | 402 | nirgun, sanskritic |
| 26 | HUKAM | ਹੁਕਮੁ | 395 | nirgun |
| 27 | YAGYA | ਜਗ | 393 | sanskritic, ritual |
| 28 | KAAM | ਕਾਮ | 387 | ethical |
| 29 | GOBIND | ਗੋਬਿੰਦ | 367 | nirgun, sanskritic |
| 30 | PIR | ਪਿਰ | 359 | devotional |
| 31 | MUKTI | ਮੁਕਤਿ | 335 | sanskritic |
| 32 | JOGI | ਜੋਗੀ | 324 | sanskritic, cleric |
| 33 | SAHIB | ਸਾਹਿਬ | 307 | nirgun |
| 34 | JUG | ਜੁਗ | 296 | sanskritic |
| 35 | AGAM | ਅਗਮ | 284 | nirgun |
| 36 | DHARAM | ਧਰਮ | 269 | sanskritic |
| 37 | BRAHM | ਬ੍ਰਹਮ | 260 | sanskritic |
| 38 | LOBH | ਲੋਭ | 232 | ethical |
| 39 | PREM | ਪ੍ਰੇਮ | 228 | devotional |
| 40 | VED | ਵੇਦ | 225 | sanskritic, scriptural |

## Observations

### HARI vs WAHEGURU: The GGS's Own Vocabulary

This is one of the most striking findings. In modern Sikh practice, **Waheguru**
is the primary name for God. But the GGS text itself tells a different story:

| Divine Name | Count | Ratio to WAHEGURU |
|-------------|-------|-------------------|
| HARI (ਹਰਿ) | 9,341 | **55:1** |
| NAAM (ਨਾਮੁ) | 5,464 | 32:1 |
| PRABH (ਪ੍ਰਭ) | 2,647 | 15:1 |
| RAM (ਰਾਮ) | 2,019 | 12:1 |
| WAHEGURU (ਵਾਹਿਗੁਰੂ) | 171 | 1:1 |

HARI appears 55 times for every 1 occurrence of WAHEGURU. This is not a
contradiction but an evolution -- WAHEGURU became the primary name in the later
Sikh tradition (post-GGS), while the scripture itself speaks through HARI,
NAAM, and PRABH. The text's own lexical choices are overwhelmingly rooted in
Sanskritic divine names repurposed for nirgun theology.

### Top Entity Patterns

**NANAK appears 5,000 times** -- the name ਨਾਨਕ serves as both a signature line
marker (Gurus signing compositions as "Nanak") and a devotional invocation.

**RAHAU (ਰਹਾਉ) appears 2,685 times** -- marking the refrain/pause line in
shabads, revealing approximately 2,685 distinct compositional units with refrain
structures.

**The core Sikh vocabulary cluster (NAAM, GUR, SATGUR, SACH, SABAD, HUKAM,
SAHAJ)** accounts for ~18,166 matches -- 30% of all matches. These are the
distinctive theological concepts of the Sikh tradition.

**Ethical vocabulary is substantial.** SEVA (814), MOH (781), HAUMAI (627),
DAYA (581), KAAM (387), LOBH (232), KRODH (210) collectively account for
3,832 matches. The Five Thieves (Panj Chor) alone appear 2,237 times, showing
how deeply the GGS engages with inner moral struggle.

**Devotional vocabulary is pervasive.** BHAGAT (1,106), PIR (359), PREM (228),
KANT (145), and BIRHA (62) account for 1,900+ matches, revealing the bridal
mysticism and love-longing vocabulary that pervades the text.

### Ramayana and Epic Narrative Entities

The lexicon includes characters from the major Indian epics. Their rarity
is itself a finding -- the GGS uses these figures sparingly, almost always
subordinated to nirgun teaching:

| Entity | Gurmukhi | Lines | Notes |
|--------|----------|-------|-------|
| INDR | ਇੰਦ੍ਰ | ~148 | King of gods (Vedic) |
| SHIV | ਸ਼ਿਵ | ~124 | The Destroyer (Trimurti) |
| KRISHNA | ਕ੍ਰਿਸ਼ਨ | ~86 | Avatar of Vishnu |
| BISN (Vishnu) | ਬਿਸਨ | ~73 | The Preserver (Trimurti) |
| BRAHMA | ਬ੍ਰਹਮਾ | ~64 | The Creator (Trimurti) |
| RAVAN | ਰਾਵਣ | ~45 | Demon king of Lanka (Ramayana) |
| PRAHLAD | ਪ੍ਰਹਿਲਾਦ | ~32 | Devotee saved by Vishnu |
| DHRU | ਧ੍ਰੂ | ~20 | The steadfast devotee |
| SITA | ਸੀਤਾ | ~9 | Consort of Ramchandra (Ramayana) |
| RAMCHANDRA | ਰਾਮਚੰਦ | ~9 | Avatar of Vishnu (distinct from RAM as divine name) |
| VALMIK | ਵਾਲਮੀਕ | ~4 | Author of the Ramayana |
| DURGA | ਦੁਰਗਾ | ~4 | The warrior goddess |
| LACHMAN | ਲਛਮਣ | ~3 | Brother of Ramchandra (Ramayana) |
| DASRATH | ਦਸਰਥ | ~1 | Father of Ramchandra (Ramayana) |
| HANUMAN | ਹਨੂਮਾਨ | ~1 | Devotee of Ram (Ramayana) |

The complete Ramayana cast (Sita, Dasrath, Ravan, Lachman, Hanuman, Valmik,
Ramchandra) appears in only ~72 lines combined -- compared to 9,341 for HARI
alone. References to the Mahabharata and Bhagavad Gita are not explicit in the
GGS; instead, individual figures like Krishna and Arjun are invoked within the
nirgun framework.

### Scriptural References

| Scripture | Entity | Lines |
|-----------|--------|-------|
| Vedas | VED | ~324 |
| Shastras | SHASTAR | ~148 |
| Smritis | SIMRIT | ~96 |
| Puranas | PURAN | ~48 |
| Quran | QURAN | ~11 |

The GGS references Hindu scriptures far more often than Islamic ones (Vedas
alone: 324 lines vs Quran: 11 lines), typically in compositions that either
survey or critique textual authority.

### Perso-Arabic Entities

**Perso-Arabic terms are sparse.** After reclassifying SAHIB from perso_arabic
to neutral (it functions as a universal divine name, not an Islamic marker),
the top Perso-Arabic entities are: KHUDA (45), FAQIR (34), QAZI (25), ALLAH (19).
