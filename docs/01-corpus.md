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
compositions) and an epilogue (angs 1352-1430, containing Salok Sehskritee,
Mundavani, Raagmala, etc.).

### Ragas by Size

**Largest ragas** (the bulk of the GGS):

| Raga | Angs | Span | Lines |
|------|------|------|-------|
| Gauri | 151-346 | 196 | 9,626 |
| Aasaa | 347-488 | 142 | 6,200 |
| Maru | 989-1106 | 118 | 5,181 |
| Ramkali | 876-974 | 99 | 4,466 |
| Sri Raag | 14-93 | 80 | 3,161 |
| Suhi | 728-794 | 67 | 2,657 |
| Sorath | 595-659 | 65 | 2,642 |
| Bilawal | 795-858 | 64 | 2,613 |

**Smallest ragas** (concentrated, specialized compositions):

| Raga | Angs | Span | Lines |
|------|------|------|-------|
| Bairari | 719-720 | 2 | 51 |
| Mali Gaura | 984-988 | 5 | 200 |
| Tilang | 721-727 | 7 | 275 |
| Kedara | 1118-1124 | 7 | 227 |
| Todi | 711-718 | 8 | 282 |
| Kalyan | 1319-1326 | 8 | 259 |
| Nat Narayan | 975-983 | 9 | 289 |
| Devgandhari | 527-536 | 10 | 344 |

Gauri alone (196 angs, 9,626 lines) contains more text than the 10 smallest
ragas combined. The range from 2 angs (Bairari) to 196 angs (Gauri) reflects
the varying depth of compositional engagement with each musical mode.

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

```
Guru Arjan:        42.9%  ████████████████████████████████████████████
Guru Nanak:        18.5%  ██████████████████▌
Guru Amar Das:     14.9%  ██████████████▉
Guru Ram Das:      11.6%  ███████████▌
Kabir:              6.9%  ██████▉
Guru Angad:         1.5%  █▌
Guru Tegh Bahadur:  1.0%  █
All other Bhagats:  2.7%  ██▋
```

**Guru Arjan dominates the corpus** with 42.9% of all lines -- nearly as much
as the next three Gurus combined. The six Gurus (Mahalla 1-5 and 9) collectively
account for 90.4% of the text, with the 12 Bhagats and Sundar contributing the
remaining 9.6%.

**Guru Gobind Singh (the 10th Guru)** compiled the final edition of the GGS
(1706) but contributed none of his own compositions to it. His bani is collected
separately in the Dasam Granth.

**Kabir is the largest Bhagat contributor** at 6.9%, exceeding Guru Angad (1.5%)
and Guru Tegh Bahadur (1.0%) individually. Among Bhagats, Kabir's 4,187 lines
dwarf all others combined (1,630 lines).

**Note on Sundar (434 lines):** Sundar is not a Bhagat in the traditional sense.
He was a relative of Guru Ram Das who narrated the passing of the Guruship from
Guru Ram Das to Guru Arjan in the composition "Ramkali Sadd" (Ang 923). His
434 lines are classified as a single narrative work, not as independent
theological compositions like the Bhagat Bani.

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
considering the Gurus' 90.4% share of total lines.

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
