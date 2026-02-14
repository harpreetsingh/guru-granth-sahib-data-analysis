# 8. Key Findings

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

## Summary

This computational analysis of the entire Guru Granth Sahib (60,629 lines,
396,036 tokens) using a 70-entity theological lexicon produces several
quantitative findings.

## Finding 1: The GGS is quantitatively a nirgun text

**38.19% of all lines** contain nirgun-register vocabulary, making it the
dominant theological register by a wide margin. The next-largest register
(sanskritic) appears in 25.78% of lines, and most of that vocabulary
co-occurs with nirgun terms. Only 3.35% of lines are purely sanskritic
without nirgun overlap.

## Finding 2: HARI is the dominant divine name, not WAHEGURU

HARI (ਹਰਿ) appears **9,341 times** -- more than 54x as often as WAHEGURU
(ਵਾਹਿਗੁਰੂ, 171 times). Despite WAHEGURU being the primary divine name in
modern Sikh practice, the GGS text itself overwhelmingly uses HARI, followed
by NAAM (5,464), GUR (4,774), PRABH (2,647), and RAM (2,019).

## Finding 3: Perso-Arabic vocabulary is highly localized

Only **0.73%** of lines contain Perso-Arabic register vocabulary (441 lines
out of 60,629). These concentrate in specific sections -- particularly Raag
Maru (angs 1083-1084) and Raag Parbhati. This is consistent with
Perso-Arabic terms appearing primarily in compositions by Bhagats like Kabir
and Sheikh Farid, and in compositions specifically addressing Islamic practice.

## Finding 4: The Mool Mantar functions as a cohesive unit

Co-occurrence analysis reveals that the Mool Mantar attributes (AJOONI, AKAL,
SATNAM, NIRVAIR, NIRBHAU) form the tightest co-occurrence cluster in the
entire corpus (PMI 2.7-5.0). When one attribute is invoked, the others tend
to follow. This is not merely because they appear together in the Mool Mantar
itself -- they co-occur across diverse compositions throughout the GGS.

## Finding 5: Register mixing is rare at the line level

Only **0.3%** of register-carrying lines mix Perso-Arabic and Sanskritic
vocabulary on the same line. The GGS achieves its multi-traditional character
through composition-level juxtaposition, not through line-level blending.

## Finding 6: Sagun narrative is subordinate to nirgun theology

Sagun narrative (mythological references to Krishna, Shiv, Brahma, etc.)
appears in only **0.40%** of lines. When it does appear, **27% of those lines
also contain nirgun vocabulary**, confirming that incarnation narratives serve
nirgun theological purposes rather than standing as independent devotional
content.

## Finding 7: Ritual and cleric references cluster in specific ragas

Ritual vocabulary (Pooja, Teerath, Havan) peaks in Raag Ramkali (ang 910)
and Bairari. Cleric references (Pandit, Qazi, Mullah) concentrate in Raag
Suhi (ang 730) and Ramkali (angs 908-909). These sections contain
compositions that directly engage with and critique institutional religious
practice.

## Finding 8: Islamic vocabulary forms tight semantic clusters

MULLAH-QAZI (PMI 5.3), HAJI-KHUDA (PMI 4.6), ALLAH-KHUDA (PMI 4.4) form
distinct co-occurrence clusters, appearing together in passages that address
Islamic practice. Similarly, BRAHMA-SHIV (PMI 2.6) cluster for Hindu
mythological references. These clusters reflect how the GGS engages with
each tradition as a coherent whole rather than cherry-picking individual terms.

## Limitations

- The 70-entity lexicon captures theologically significant terms but not
  the full vocabulary of the GGS. 56.6% of lines are "unmarked."
- Co-occurrence is measured at ang level (not shabad level), which is a
  coarser unit than ideal.
- Density measurements treat all token matches equally regardless of
  grammatical role or semantic context.
- The pipeline performs string matching, not disambiguation. Polysemous
  terms (e.g., ਕਰਮ which can mean karma, action, or grace) are counted
  under a single entity.
