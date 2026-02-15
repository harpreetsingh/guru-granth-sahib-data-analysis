# 1. Corpus Overview

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Source

The corpus was downloaded from [srigurugranth.com](https://srigurugranth.com),
which provides the full text of the Guru Granth Sahib in Unicode Gurmukhi.
Each of the 1,430 angs (pages) was fetched, parsed, normalized, and tokenized
into a canonical JSONL database.

## Corpus Statistics

| Metric       | Value   |
|-------------|---------|
| Total angs   | 1,430   |
| Total lines  | 60,629  |
| Total tokens | 396,036 |
| Authors identified | 18 |

Each record in `data/corpus/ggs_lines.jsonl` contains:

- `ang` -- page number (1-1430)
- `line_uid` -- unique line identifier
- `gurmukhi_raw` -- original text as scraped
- `gurmukhi` -- normalized Gurmukhi text
- `tokens` -- whitespace-tokenized list
- `token_spans` -- character offsets for each token
- `source_url` -- provenance URL

## Structure

The Guru Granth Sahib is organized into 31 ragas (musical modes), with a
preamble section (angs 1-13, containing Japji Sahib and other foundational
compositions) and an epilogue (angs 1354-1430, containing Salok Sehskritee,
Mundavani, Raagmala, etc.).

The largest ragas by ang span:
- Gauri (151-346, 196 angs)
- Aasaa (347-488, 142 angs)
- Maru (989-1106, 118 angs)
- Ramkali (876-974, 99 angs)

## Authorship

The GGS is a multi-author scripture. Authors were extracted via regex-based
Mahalla header detection (ਮਹਲਾ + Gurmukhi numeral for Gurus, named patterns
for Bhagats).

### Author Distribution

| Author | Lines | % of Corpus |
|--------|-------|-------------|
| Guru Arjan (Mahalla 5) | 26,036 | 42.9% |
| Guru Nanak (Mahalla 1) | 11,230 | 18.5% |
| Guru Amar Das (Mahalla 3) | 9,041 | 14.9% |
| Guru Ram Das (Mahalla 4) | 7,005 | 11.6% |
| Kabir | 4,187 | 6.9% |
| Guru Angad (Mahalla 2) | 895 | 1.5% |
| Guru Tegh Bahadur (Mahalla 9) | 605 | 1.0% |
| Ravidas | 475 | 0.8% |
| Sundar | 434 | 0.7% |
| Namdev | 257 | 0.4% |
| Farid | 158 | 0.3% |
| Beni | 99 | 0.2% |
| Trilochan | 86 | 0.1% |
| Ramanand | 44 | 0.1% |
| Sain | 34 | 0.1% |
| Jaidev | 16 | <0.1% |
| Bhikhan | 16 | <0.1% |
| Parmanand | 11 | <0.1% |

**Guru Arjan dominates the corpus** with 42.9% of all lines -- nearly as much
as the next three Gurus combined. The five Gurus collectively account for 88.4%
of the text, with the 13 Bhagats contributing the remaining 11.6%.

**Kabir is the largest Bhagat contributor** at 6.9%, exceeding Guru Angad (1.5%)
and Guru Tegh Bahadur (1.0%) individually. Among Bhagats, Kabir's 4,187 lines
dwarf all others combined (1,696 lines).

## Lexicon

The entity lexicon defines **124 entities** with **346 aliases** (spelling
variants in Gurmukhi), organized across eleven feature dimensions:

| Dimension | Description |
|-----------|------------|
| `nirgun` | Names/concepts for the formless divine (Hari, Naam, Prabh, etc.) |
| `sanskritic` | Vedantic/yogic vocabulary (Brahm, Maya, Atma, etc.) |
| `devotional` | Love/longing/surrender vocabulary (Pir, Kant, Birha, Prem, etc.) |
| `ethical` | Inner vices and virtues (Haumai, Krodh, Lobh, Daya, Santokh, etc.) |
| `ritual` | Ritual practice references (Pooja, Teerath, Havan, etc.) |
| `cleric` | Religious authority references (Pandit, Qazi, Mullah, etc.) |
| `oneness` | Non-duality markers (Iko, Ek, Joti, etc.) |
| `sagun_narrative` | Mythological/incarnation references (Krishna, Shiv, Brahma, Sita, etc.) |
| `scriptural` | References to specific scriptures (Ved, Quran, Puran, etc.) |
| `perso_arabic` | Islamic/Sufi vocabulary (Allah, Khuda, Qazi, Noor, etc.) |
| `identity` | Religious identity labels (Hindu, Musalman, Turk) |
