# 5. Co-occurrence Analysis

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Method

Co-occurrence is measured at the ang level: two entities co-occur if they both
appear on the same ang (page). Pointwise Mutual Information (PMI) measures
whether a pair co-occurs more than expected by chance.

- **1,430 angs** analyzed as co-occurrence units
- **2,687 entity pairs** with co-occurrence count >= 5

## Top Entity Pairs by PMI (Surprising Associations)

**PMI (Pointwise Mutual Information)** measures *surprise* -- how much more
often two entities co-occur than their individual frequencies would predict.
High PMI pairs are the *unexpected* associations: rare entities that
nevertheless appear together with unusual regularity. PMI corrects for base
rate, so common entities like HARI and NAAM (which co-occur everywhere simply
because both are frequent) score lower than rare-but-tightly-linked pairs
like HINDU-TURK.

| Entity 1 | Entity 2 | PMI | Co-occur Count |
|----------|----------|-----|----------------|
| HINDU | TURK | 6.174 | 10 |
| MULLAH | QAZI | 5.344 | 5 |
| AJOONI | AKAL | 4.958 | 34 |
| AJOONI | SATNAM | 4.901 | 27 |
| HINDU | QAZI | 4.660 | 7 |
| HAJI | KHUDA | 4.634 | 5 |
| AJOONI | NIRVAIR | 4.581 | 33 |
| AKAL | SATNAM | 4.465 | 27 |
| BISN | BRAHMA | 4.397 | 28 |
| ALLAH | KHUDA | 4.366 | 6 |
| NIRVAIR | SATNAM | 4.234 | 29 |
| AKAL | NIRVAIR | 4.230 | 35 |
| KHUDA | QAZI | 4.192 | 9 |
| AJOONI | MOORAT | 3.809 | 34 |
| AKAL | MOORAT | 3.712 | 43 |
| HINDU | KHUDA | 3.634 | 5 |
| SHASTAR | SIMRIT | 3.598 | 32 |
| MOORAT | SATNAM | 3.369 | 28 |
| AJOONI | NIRBHAU | 3.282 | 34 |
| MOORAT | NIRVAIR | 3.161 | 37 |
| PURAN | SIMRIT | 3.036 | 8 |
| BARAT | POOJA | 3.022 | 7 |
| AKAL | NIRBHAU | 3.006 | 38 |
| BISN | SHIV | 2.971 | 15 |
| KANT | SOHAGAN | 2.958 | 15 |
| NIRBHAU | SATNAM | 2.892 | 29 |
| INDR | SHIV | 2.879 | 10 |
| NIRBHAU | NIRVAIR | 2.746 | 40 |
| BRAHMA | QAZI | 2.700 | 5 |
| PURAN | SHASTAR | 2.595 | 11 |

## Top Entity Pairs by Frequency (The Everyday Vocabulary)

**Frequency** counts raw co-occurrence -- how many angs contain both entities.
Unlike PMI, frequency is dominated by common entities. These pairs appear
together constantly because both entities are individually very frequent. They
represent the *backbone* of the GGS's theological vocabulary rather than
surprising associations.

| Entity 1 | Entity 2 | Co-occur Count |
|----------|----------|----------------|
| NAAM | NANAK | 1,217 |
| HARI | NAAM | 1,153 |
| HARI | NANAK | 1,153 |
| GUR | NANAK | 1,138 |
| GUR | NAAM | 1,130 |
| GUR | HARI | 1,074 |
| NAAM | SATGUR | 962 |
| NANAK | SATGUR | 955 |
| HARI | SATGUR | 936 |
| GUR | SATGUR | 921 |
| NAAM | NA_NEGATION | 893 |
| NANAK | NA_NEGATION | 870 |
| NANAK | PRABH | 848 |
| HARI | NA_NEGATION | 840 |
| HARI | PRABH | 823 |

## Interpretation

### The Identity Co-occurrence (New Finding)

**HINDU-TURK is the highest PMI pair in the entire corpus (6.174).** When the GGS
names religious communities, it almost always names them together -- "Hindu" and
"Turk" (the Gurmukhi term for Muslims) appear on the same ang in 10 of their
combined appearances. This is structurally significant: the text treats religious
identity as a paired concept, typically in lines that assert the transcendence
of both categories. The GGS does not critique one community without addressing
both.

### The Mool Mantar (The Core Mantra) Cluster

The Mool Mantar attributes form a tight co-occurrence cluster: AJOONI, AKAL,
SATNAM, NIRVAIR, NIRBHAU, and MOORAT (PMI 2.7-5.0). These are the attributes
listed in the opening declaration of the GGS:

> ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ
>
> *One Creator, Truth is the Name, Creative Being, Without Fear, Without
> Enmity, Timeless Form, Beyond Birth, Self-Existent, By Guru's Grace.*

The data confirms that when the Gurus invoke one Mool Mantar attribute, they
tend to invoke multiple attributes together -- reinforcing the holistic nature
of this theological formula.

### The Islamic Vocabulary Cluster

MULLAH-QAZI (PMI 5.344), HAJI-KHUDA (4.634), ALLAH-KHUDA (4.366), and
KHUDA-QAZI (4.192) form another tight cluster. These terms overwhelmingly
co-occur in compositions that address Islamic practice and belief.

### The Scriptural Reference Cluster (New Finding)

SHASTAR-SIMRIT (PMI 3.598), PURAN-SIMRIT (3.036), PURAN-SHASTAR (2.595)
show that Hindu scriptural references cluster tightly. When the GGS mentions
one scripture (Vedas, Puranas, Shastras, Smritis), it tends to list multiple
scriptures together -- typically in compositions that either survey or
critique textual authority.

### The Brahma/Vishnu/Shiva Trinity Cluster

BISN-BRAHMA (PMI 4.397), BISN-SHIV (2.971), INDR-SHIV (2.879) confirm that
the Hindu Trinity (Brahma the Creator, Vishnu the Preserver, Shiva the
Destroyer) appears as a constellation, not individually. When the GGS mentions
one member of the Trinity, it tends to mention the others -- typically in
compositions that assert the formless divine is beyond all three forms.

### The Bridal Mysticism Cluster (New Finding)

KANT-SOHAGAN (PMI 2.958) reveals the bridal metaphor vocabulary: the
Husband-Lord (ਕੰਤ) and the blessed bride (ਸੋਹਾਗਣਿ) appear together,
confirming the structured devotional-romantic framework of Gurbani.

### The Ritual Critique Cluster

BARAT-POOJA (PMI 3.022), HAVAN-POOJA (PMI 2.537), and HAVAN-TEERATH
(PMI 2.331) cluster together, typically in passages critiquing external
ritual practices as insufficient for spiritual realization.

### The BRAHMA-QAZI Cross-Tradition Pair

BRAHMA-QAZI (PMI 2.700, 5 angs) is notable as a cross-tradition pairing:
the Hindu creator deity and the Islamic judge appearing together. This echoes
the HINDU-TURK identity finding (PMI 6.174) -- the GGS's pattern of naming
traditions in pairs extends even to its mythological and clerical vocabulary.

### The Frequency Core

By raw frequency, the top pairs are all from the core nirgun/Sikh vocabulary:
NAAM-NANAK (1,217 angs), HARI-NAAM (1,153), GUR-NANAK (1,138). These entities
are so frequent that they appear together on nearly every ang. The high
co-occurrence of NA_NEGATION (ਨਾ) with core terms reflects the GGS's
characteristic apophatic theology -- defining the divine through negation
("without fear," "without enmity," "without form").
