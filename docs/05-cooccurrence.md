# 5. Co-occurrence Analysis

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Method

Co-occurrence is measured at the ang level: two entities co-occur if they both
appear on the same ang (page). Pointwise Mutual Information (PMI) measures
whether a pair co-occurs more than expected by chance.

- **1,430 angs** analyzed as co-occurrence units
- **1,042 entity pairs** with co-occurrence count >= 5

## Top Entity Pairs by PMI

High PMI indicates that these pairs appear together far more often than their
individual frequencies would predict.

| Entity 1 | Entity 2 | PMI | Co-occur Count |
|----------|----------|-----|----------------|
| MULLAH | QAZI | 5.344 | 5 |
| AJOONI | AKAL | 4.958 | 34 |
| AJOONI | SATNAM | 4.901 | 27 |
| HAJI | KHUDA | 4.634 | 5 |
| AJOONI | NIRVAIR | 4.581 | 33 |
| AKAL | SATNAM | 4.465 | 27 |
| ALLAH | KHUDA | 4.366 | 6 |
| NIRVAIR | SATNAM | 4.234 | 29 |
| AKAL | NIRVAIR | 4.230 | 35 |
| KHUDA | QAZI | 4.192 | 9 |
| AJOONI | NIRBHAU | 3.282 | 34 |
| BARAT | POOJA | 3.022 | 7 |
| AKAL | NIRBHAU | 3.006 | 38 |
| NIRBHAU | SATNAM | 2.892 | 29 |
| NIRBHAU | NIRVAIR | 2.746 | 40 |
| BRAHMA | QAZI | 2.700 | 5 |
| BRAHMA | SHIV | 2.575 | 15 |
| HAVAN | POOJA | 2.537 | 5 |
| HAVAN | TEERATH | 2.331 | 6 |
| NIRANKAR | WAHEGURU | 2.119 | 6 |

## Top Entity Pairs by Frequency

These are the most commonly co-occurring pairs regardless of statistical
significance.

| Entity 1 | Entity 2 | Co-occur Count |
|----------|----------|----------------|
| HARI | NAAM | 1,153 |
| GUR | NAAM | 1,130 |
| GUR | HARI | 1,074 |
| NAAM | SATGUR | 962 |
| HARI | SATGUR | 936 |
| GUR | SATGUR | 921 |
| NAAM | NA_NEGATION | 893 |
| HARI | NA_NEGATION | 840 |
| HARI | PRABH | 823 |
| GUR | NA_NEGATION | 818 |

## Interpretation

### The Mool Mantar Cluster

The highest-PMI pairs reveal a striking pattern: **the Mool Mantar attributes
form a tight co-occurrence cluster.** AJOONI, AKAL, SATNAM, NIRVAIR, and
NIRBHAU almost always appear together (PMI 2.7-5.0). These are the attributes
listed in the opening declaration of the GGS:

> ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ

The data confirms that when the Gurus invoke one Mool Mantar attribute, they
tend to invoke multiple attributes together -- reinforcing the holistic nature
of this theological formula.

### The Islamic Vocabulary Cluster

MULLAH-QAZI (PMI 5.344), HAJI-KHUDA (4.634), ALLAH-KHUDA (4.366), and
KHUDA-QAZI (4.192) form another tight cluster. These terms overwhelmingly
co-occur in compositions that address Islamic practice and belief, often in
the context of critiquing empty ritual or asserting the universality of the
divine.

### The Ritual Critique Cluster

BARAT-POOJA (3.022), HAVAN-POOJA (2.537), HAVAN-TEERATH (2.331) cluster
together, typically in passages critiquing external ritual practices as
insufficient for spiritual realization.

### Hindu Mythological Cluster

BRAHMA-SHIV (2.575) and BRAHMA-QAZI (2.700) show that mythological figures
tend to be mentioned together, often in compositions that survey multiple
religious traditions.

### The Frequency Core

By raw frequency, the top pairs are all from the core nirgun/Sikh vocabulary:
HARI-NAAM (1,153 angs), GUR-NAAM (1,130), GUR-HARI (1,074). These entities
are so frequent that they appear together on nearly every ang. The high
co-occurrence of NA_NEGATION (ਨਾ) with core terms reflects the GGS's
characteristic apophatic theology -- defining the divine through negation
("without fear," "without enmity," "without form").
