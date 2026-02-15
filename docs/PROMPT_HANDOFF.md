# Session Handoff -- Next Session Prompt

Read this file first, then AGENTS.md, then execute.

## Context

This is a computational analysis of the Guru Granth Sahib (GGS) -- 60,629 lines, 396,036 tokens, 1,430 angs, 124-entity lexicon, 11 feature dimensions, 18 authors. The full analysis pipeline is built, tested (733 tests), and all results are in `data/derived/analysis_results.json`. The analysis docs are in `docs/01-corpus.md` through `docs/10-findings.md` plus `docs/glossary.md`.

## Strategic Decision (Made This Session)

**The webapp is deprioritized.** The user decided the right distribution strategy is:

1. **Blog on formeditators.com** -- the being-harpreet post (extensive rewrite needed)
2. **YouTube videos** -- English-dominant and Hindi/Punjabi versions
3. **GitHub repo** -- already done, docs are solid (the "show your work" layer for the 1%)

The webapp (React SPA in `docs/PLAN_WEBAPP.md`) is not being built. The `web_bundle.py` backend exists but frontend work is shelved indefinitely.

## What Needs Doing

### 1. Blog Rewrite: `docs/blog-being-harpreet.md`

The current draft is functional but needs an **extensive rewrite** per the user's feedback:

- **Lead with the Three Pillars** (nirgun 42.25%, sanskritic 30.21%, devotional-ethical 12.7%) -- this is the most powerful framing of what the GGS actually is
- **Advaita framing**: The user's thesis is that the Gurus leaned heavily into Advaita (non-dual) philosophy but made it far more accessible by framing it as nirgun. This should be a central argument, not a footnote.
- **Add the authors table** -- each Guru's distinctive voice (Guru Ram Das = nirgun maximalist, Guru Nanak = balanced founder, Farid = Sufi outlier, etc.)
- **Add verse/composition count** -- ~2,685 shabads with RAHAU markers
- **Add the languages section** -- 6 languages (Punjabi, Braj Bhasha, Sanskrit, Persian/Arabic, Marathi, Multani), derived from corpus analysis (see `docs/01-corpus.md` Languages section for data)
- **The "convergence text" conclusion** deserves more emphasis -- the GGS is quantitatively unique, no other scripture combines nirgun metaphysics + devotional longing + ethical discipline + Sanskritic vocabulary + selective cross-civilizational synthesis
- **HARI vs WAHEGURU** (55:1 ratio) -- already in the draft, good
- **RAM as nirgun name** -- already in the draft, good
- The user's framing: "The Gurus didn't reject Vedantic philosophy -- they engaged with it deeply and recontextualized it within a nirgun framework" should be sharpened to: they took Advaita philosophy and made it accessible through nirgun framing
- **Audience**: Sikh diaspora, spiritual seekers, meditation practitioners (formeditators.com readers). Not academics. Personal, first-person voice.

### 2. YouTube Script Outline

Not yet started. Should draw from the same 13 findings but structured for video:
- Hook: "I ran NLP on every single line of the Guru Granth Sahib. Here's what the data says."
- Two versions planned: English-dominant and Hindi/Punjabi
- Key visual moments: Three Pillars chart, HARI vs WAHEGURU comparison, author fingerprints table, RAM co-occurrence data, HINDU-TURK PMI
- The Stoic-Bhakti-Advaita triangle is a great visual

### 3. Presentation Deck

Not yet started. User mentioned Gamma or React-based. Should be the visual companion to the YouTube video.

## Key Data Points (Quick Reference)

- Corpus: 60,629 lines, 396,036 tokens, 29,514 unique vocabulary, 1,430 angs, ~2,685 RAHAU shabads
- 6 languages: Punjabi, Braj Bhasha, Sanskrit vocab, Persian/Arabic, Marathi, Multani
- Three Pillars: nirgun (42.25%), sanskritic (30.21%), devotional-ethical (12.7%) = 85.2%
- HARI: 9,341 vs WAHEGURU: 171 (55:1)
- RAM: 2,019 occurrences, nirgun-to-sagun co-occurrence 3.86:1
- Ethical > Ritual: 5.46% vs 2.20% (2.5x)
- Sagun narrative: 0.51% (83:1 ratio to nirgun)
- Perso-Arabic: 0.29% (after SAHIB reclassification). Civilizational ratio: 99.9:1
- HINDU-TURK: highest PMI (6.174) in entire corpus
- ALLAH: 19 lines (0.03%), 21% also contain Indic divine names
- Register mixing: 0.12% (22 lines mix Perso-Arabic + Sanskritic)
- Guru Arjan: 42.9% of corpus (compiler-poet)
- Authors: Guru Ram Das = nirgun maximalist (62.27%), Farid = Sufi outlier (5.70% perso_arabic), Ravidas = devotional peak (13.89%)
- Stoic-Bhakti-Advaita triangle: Advaita 44.25%, Bhakti 7.24%, Stoic 5.46%
- "Convergence text" -- combines non-dual metaphysics + devotional practice + ethical self-discipline into unique synthesis

## What's NOT Needed

- No webapp work
- No new pipeline features
- No new lexicon entities
- No beads/tickets to create (all 20 closed)
- All quality gates pass (ruff clean, 733 tests)

## Files to Read

- `docs/blog-being-harpreet.md` -- current draft to rewrite
- `docs/blog-ai-ds.md` -- technical blog (lower priority, may fold triangle into being-harpreet)
- `docs/10-findings.md` -- the 13 key findings
- `docs/03-features.md` -- Three Pillars framework
- `docs/09-semantic.md` -- RAM, ALLAH, triangle, civilizational density
- `docs/08-authors.md` -- per-author profiles
- `docs/01-corpus.md` -- languages, verse counts, compositional history
- `docs/glossary.md` -- term definitions for non-Sikh audience
