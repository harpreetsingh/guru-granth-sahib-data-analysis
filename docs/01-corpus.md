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
| Unique vocabulary | 29,514 tokens |
| Compositions (shabads with RAHAU) | ~2,685 |
| Authors identified | 18 |
| Languages / dialects | 6+ |

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

## Languages

The GGS is written entirely in **Gurmukhi script**, but the underlying text
draws on at least six distinct languages and dialects. Our corpus-level
vocabulary analysis reveals their presence through grammatical markers,
loanwords, and register-specific vocabulary:

| Language | Evidence from corpus | Primary authors |
|----------|---------------------|-----------------|
| **Punjabi** | Base grammar and vocabulary; markers like ਹੋਇ (1,503), ਤੂ (896), ਮੈ (742), postpositions ਦਾ/ਦੀ/ਦੇ | All six Gurus, Farid |
| **Braj Bhasha** | Literary Hindi pronouns ਮੋਹਿ (341), ਕੋ (982), ਸੋ (1,530); verb forms ਕਰਤ (170), ਹੋਤ (83) — 4,678 markers total | Kabir, Namdev, Ravidas, Trilochan, Beni |
| **Sanskrit** (vocabulary) | Philosophical terms pervade all compositions: ਮਾਇਆ (827), ਕਰਮ (388), ਬ੍ਰਹਮ (165), ਜੋਤਿ (311), ਮੁਕਤਿ (266) | All authors (embedded vocabulary) |
| **Persian/Arabic** | ਦਰਗਹ (229), ਦੁਨੀਆ (55), ਕਾਜੀ (24), ਅਲਾਹ (4), ਖੁਦਾਇ (32) — 460 tokens total | Farid (5.7% register), Kabir |
| **Marathi** (influence) | Namdev's 257 lines carry Marathi vocabulary and idiom, transliterated into Gurmukhi | Namdev |
| **Multani/Lehndi Punjabi** | Farid's distinctive western Punjabi dialect | Farid |

Scholars call the composite literary language of the Bhagats **"Sant Bhasha"**
(saint's language) -- a lingua franca blending Braj Bhasha, Awadhi, Punjabi,
and regional vocabularies, unified by Gurmukhi script.

**Key finding:** Braj Bhasha grammatical markers (4,678) slightly outnumber
Punjabi-specific markers (3,656) in raw token count, reflecting the substantial
Bhagat Bani contribution. However, Punjabi is the dominant base language when
considering the Gurus' 88.4% share of total lines.

**Note:** Our source text (srigranth.com) normalizes away Persian-specific nukta
diacritics (ਖ਼→ਖ, ਗ਼→ਗ, ਜ਼→ਜ, ਫ਼→ਫ), so Persian/Arabic loanwords appear in
their Punjabi-adapted spellings. Zero lines contain Persian-specific nukta in
our corpus.

## Compositional History

The GGS was compiled in two major stages:

1. **Adi Granth (1604)** -- Guru Arjan compiled the first edition, incorporating
   compositions by Guru Nanak through Guru Arjan (Mahalla 1-5), plus the 13
   Bhagats. Guru Arjan is both the largest single contributor (42.9%) and the
   editor who shaped the text's overall structure and character.

2. **Damdami Bir (1706)** -- Guru Gobind Singh added Guru Tegh Bahadur's
   compositions (Mahalla 9, 605 lines). Tradition holds that Guru Arjan had
   left space in the original compilation anticipating future compositions --
   Guru Tegh Bahadur's bani was inserted into the existing raga framework
   rather than appended as a separate section.

This editorial design explains why Guru Tegh Bahadur's compositions appear
distributed across the same ragas as the earlier Gurus, maintaining the
organizational integrity of the original compilation.

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
