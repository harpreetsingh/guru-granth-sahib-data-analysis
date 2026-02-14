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

## Lexicon

The entity lexicon defines **70 entities** with **206 aliases** (spelling
variants in Gurmukhi), organized across six registers:

| Register         | Description                                      |
|-----------------|--------------------------------------------------|
| `perso_arabic`   | Islamic/Sufi vocabulary (Allah, Khuda, Qazi, etc.)  |
| `sanskritic`     | Vedantic/yogic vocabulary (Brahm, Maya, Atma, etc.) |
| `nirgun`         | Names/concepts for the formless divine (Hari, Naam, Prabh, etc.) |
| `sagun_narrative`| Mythological/incarnation references (Krishna, Shiv, Brahma, etc.) |
| `ritual`         | Ritual practice references (Pooja, Teerath, Havan, etc.) |
| `cleric`         | Religious authority references (Pandit, Qazi, Mullah, etc.) |
