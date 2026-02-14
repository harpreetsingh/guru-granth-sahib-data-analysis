# 2. Lexical Matching Results

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Summary

| Metric                  | Value         |
|------------------------|---------------|
| Total matches           | 43,818        |
| Unique entities matched | 67 of 70      |
| Lines with matches      | 28,199 (46.5%) |
| Nested matches          | 40            |
| Confidence level        | 100% HIGH     |

Nearly half of all lines in the Guru Granth Sahib contain at least one
recognized theological/conceptual entity from our 70-entity lexicon.

## Top 30 Entities by Frequency

| # | Entity ID | Gurmukhi | Register | Category | Tradition | Count |
|---|-----------|----------|----------|----------|-----------|-------|
| 1 | HARI | ਹਰਿ | sanskritic | divine_name | universal | 9,341 |
| 2 | NAAM | ਨਾਮੁ | neutral | concept | sikh | 5,464 |
| 3 | GUR | ਗੁਰ | neutral | concept | sikh | 4,774 |
| 4 | PRABH | ਪ੍ਰਭ | sanskritic | divine_name | universal | 2,647 |
| 5 | SATGUR | ਸਤਿਗੁਰ | neutral | divine_name | sikh | 2,613 |
| 6 | NA_NEGATION | ਨਾ | neutral | negation | - | 2,229 |
| 7 | SACH | ਸਚੁ | neutral | concept | sikh | 2,196 |
| 8 | RAM | ਰਾਮ | sanskritic | divine_name | universal | 2,019 |
| 9 | SABAD | ਸਬਦ | neutral | concept | sikh | 1,748 |
| 10 | BINU_NEGATION | ਬਿਨੁ | neutral | negation | - | 1,656 |
| 11 | SAHAJ | ਸਹਜ | neutral | concept | sikh | 976 |
| 12 | MAYA | ਮਾਇਆ | sanskritic | concept | vedantic | 833 |
| 13 | KARAM | ਕਰਮ | sanskritic | concept | vedantic | 620 |
| 14 | JAP | ਜਪ | sanskritic | practice | universal | 576 |
| 15 | GIAN | ਗਿਆਨ | sanskritic | concept | vedantic | 572 |
| 16 | THAKUR | ਠਾਕੁਰ | sanskritic | divine_name | universal | 402 |
| 17 | HUKAM | ਹੁਕਮੁ | neutral | concept | sikh | 395 |
| 18 | GOBIND | ਗੋਬਿੰਦ | sanskritic | divine_name | universal | 367 |
| 19 | MUKTI | ਮੁਕਤਿ | sanskritic | concept | vedantic | 335 |
| 20 | JOGI | ਜੋਗੀ | sanskritic | marker | yogic | 324 |
| 21 | SAHIB | ਸਾਹਿਬ | perso_arabic | divine_name | universal | 307 |
| 22 | JUG | ਜੁਗ | sanskritic | temporal | vedantic | 296 |
| 23 | AGAM | ਅਗਮ | sanskritic | divine_name | universal | 284 |
| 24 | DHARAM | ਧਰਮ | sanskritic | concept | vedantic | 269 |
| 25 | BRAHM | ਬ੍ਰਹਮ | sanskritic | concept | vedantic | 260 |
| 26 | TEERATH | ਤੀਰਥ | sanskritic | practice | vedantic | 182 |
| 27 | WAHEGURU | ਵਾਹਿਗੁਰੂ | neutral | divine_name | sikh | 171 |
| 28 | NIRANJAN | ਨਿਰੰਜਨੁ | sanskritic | divine_name | universal | 169 |
| 29 | NIRBHAU | ਨਿਰਭਉ | neutral | divine_name | sikh | 163 |
| 30 | ALAKH | ਅਲਖ | sanskritic | divine_name | universal | 161 |

## Observations

**HARI dominates overwhelmingly.** With 9,341 occurrences, ਹਰਿ (Hari) is by far
the most frequent divine name -- more than the next two entities combined (NAAM +
GUR = 10,238). This reflects HARI's role as a universal, register-neutral name
for the divine in Gurbani.

**The core Sikh vocabulary cluster (NAAM, GUR, SATGUR, SACH, SABAD, HUKAM,
SAHAJ)** accounts for ~18,166 matches -- 41% of all matches. These are the
distinctive theological concepts of the Sikh tradition.

**Sanskritic divine names (HARI, PRABH, RAM, THAKUR, GOBIND)** collectively
account for 14,776 matches (34%), showing deep engagement with Indic theological
vocabulary.

**Perso-Arabic terms are sparse.** SAHIB (307) is the only Perso-Arabic entity
in the top 30. KHUDA appears 45 times, ALLAH 19 times, QAZI 25 times. This
aligns with the GGS being primarily composed in a Sanskritic-Punjabi register,
with selective Perso-Arabic borrowings.

**WAHEGURU is relatively rare (171).** Despite being the central name for God in
modern Sikh practice, it appears far less than HARI (55x more frequent) or
NAAM (32x). This is consistent with WAHEGURU becoming the primary divine name
in the later Sikh tradition rather than in the GGS text itself.
