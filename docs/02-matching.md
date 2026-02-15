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

**HARI dominates overwhelmingly.** With 9,341 occurrences, ਹਰਿ (Hari) is by far
the most frequent divine name -- nearly double the next entity (NAAM at 5,464).
This reflects HARI's role as a universal, register-neutral name for the divine
in Gurbani.

**NANAK appears 5,000 times** -- a new finding from the expanded lexicon. The
name ਨਾਨਕ serves as both a signature line marker (Gurus signing compositions
as "Nanak") and a devotional invocation. Its frequency makes it the third most
common entity in the corpus.

**RAHAU (ਰਹਾਉ) appears 2,685 times** -- marking the refrain/pause line in
shabads. This structural marker reveals that the GGS contains approximately
2,685 distinct compositional units with refrain structures.

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

**Perso-Arabic terms are sparse.** After reclassifying SAHIB from perso_arabic
to neutral (it functions as a universal divine name, not an Islamic marker),
the top Perso-Arabic entities are: KHUDA (45), FAQIR (34), QAZI (25), ALLAH (19).

**WAHEGURU is relatively rare (171).** Despite being the central name for God in
modern Sikh practice, it appears far less than HARI (55x more frequent) or
NAAM (32x). This is consistent with WAHEGURU becoming the primary divine name
in the later Sikh tradition rather than in the GGS text itself.
