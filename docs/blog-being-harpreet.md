# What Does the Guru Granth Sahib Actually Say? A Computational Reading

*A data-driven exploration of the world's most unique scripture*

---

I grew up hearing the Guru Granth Sahib. The melodies, the words, the feeling of sitting in the Darbar Sahib at Harmandir Sahib -- these are woven into my earliest memories. But I always had questions. Not the kind you ask in Sunday school. The kind that keep you up at night.

What does the text actually *say*, if you read every single line? Not what we were told it says. Not what any particular tradition claims. What does the data show?

So I built a computational pipeline to find out. Every line. Every word. Every divine name. Every metaphor. Every critique. 60,629 lines. 396,036 tokens. 124 theological entities tracked across 346 spelling variants.

Here's what the numbers reveal.

---

## The Formless Divine Dominates Everything

The first and most striking finding: **42.25% of all lines** in the Guru Granth Sahib contain vocabulary associated with the formless, attributeless divine (nirgun). That's not a tendency -- it's a structural fact. Nearly half the text is explicitly about a God who has no form, no image, no incarnation.

The sanskritic philosophical vocabulary (Maya, Brahm, Atma, Karam) appears in 30.21% of lines. But here's the key: most of it appears *alongside* nirgun vocabulary. The Gurus didn't reject Vedantic philosophy -- they engaged with it deeply and recontextualized it within a nirgun framework.

Sagun narrative -- references to Krishna, Shiv, Brahma, Sita, Ravan -- appears in only **0.51% of lines**. For every line that mentions an incarnation, there are 83 lines about the formless divine. And when incarnation narratives do appear, 27% of those lines *also* contain nirgun vocabulary. The Gurus used mythology to teach formlessness, not as devotion to particular deities.

## HARI, Not WAHEGURU

This surprised me when I first saw the data, though it shouldn't have.

HARI (ਹਰਿ) appears **9,341 times** -- more than any other entity in the text. WAHEGURU (ਵਾਹਿਗੁਰੂ) appears 171 times. That's a 55:1 ratio.

The five most frequent divine names in the GGS are:
1. HARI -- 9,341
2. NAAM -- 5,464
3. PRABH -- 2,647
4. RAM -- 2,019
5. WAHEGURU -- 171

Modern Sikh practice centers on "Waheguru" as the primary name. The text itself centers on Hari, Naam, and Prabh. This isn't a contradiction -- it's an evolution. WAHEGURU became the primary name in the later tradition. But the GGS itself speaks a different lexical language.

## What Does "Ram" Actually Mean in the GGS?

This is the question that started this whole project for me. When the Gurus say "Ram" (ਰਾਮ), do they mean the prince of Ayodhya, the hero of the Ramayana? Or do they mean the formless Absolute?

The data is unambiguous. RAM appears 2,019 times across 1,894 lines. Its top co-occurring entities are:

- NAAM (547 co-occurrences)
- HARI (399)
- GUR (139)
- PRABH (91)
- JAP (70)
- BHAGAT (67)

These are all nirgun-register terms. RAM co-occurs with sagun narrative entities (Krishna, Shiv, Brahma, Sita) only 7 times at the ang level, compared to 27 nirgun co-occurrences.

**RAM in the GGS behaves statistically as a synonym for the formless divine.** Its semantic neighborhood is indistinguishable from HARI's. When the Gurus say "Ram," they don't mean Dasharatha's son. They mean the One without form.

## The Five Thieves Are Real (and Measurable)

The Guru Granth Sahib doesn't just preach theology. It's deeply concerned with the inner life. The "Five Thieves" (Panj Chor) -- ego (ਹਉਮੈ), lust (ਕਾਮ), anger (ਕ੍ਰੋਧ), greed (ਲੋਭ), attachment (ਮੋਹ) -- collectively appear **2,237 times**.

The ethical dimension accounts for **5.46% of all lines**. That's more than ritual references (2.2%), cleric critique (0.95%), and interfaith engagement (0.29%) combined.

The virtues are equally present: compassion (ਦਇਆ, 581), service (ਸੇਵਾ, 814), contentment (ਸੰਤੋਖ), humility (ਨਿਮਰਤਾ).

This maps remarkably well to Stoic philosophy. The GGS's ethical framework is about *inner sovereignty* -- mastery of the passions, cultivation of virtue, equanimity in the face of the world. Marcus Aurelius would recognize the language.

## A Love Poem to the Infinite

But the GGS is not just philosophy. It's a love poem.

**7.24% of all lines** contain devotional vocabulary -- bridal metaphors (ਪਿਰ, ਕੰਤ, ਸੋਹਾਗਣਿ), separation-longing (ਬਿਰਹਾ, ਪ੍ਰੇਮ), and devotional surrender (ਭਗਤ).

The RAHAU (ਰਹਾਉ) marker appears 2,685 times -- indicating the refrain lines where the emotional core of each composition resides. Every shabad is structured around a pause, a moment of emotional intensity, a heart-cry.

The devotional dimension is the third-largest register in the GGS, after nirgun theology and Sanskritic philosophy. The text moves constantly between metaphysical abstraction and raw emotional devotion.

This is what makes the GGS unique: it's simultaneously a philosophical treatise *and* a collection of love songs. The Stoic and the Bhakti poet sit in the same line.

## The Stoic-Bhakti-Advaita Triangle

I call it the "triangle" because every author in the GGS engages with all three axes, but in different proportions:

- **Advaita axis (nirgun + oneness): 44.25%** of lines
- **Bhakti axis (devotional): 7.24%** of lines
- **Stoic axis (ethical): 5.46%** of lines

Guru Ram Das is the most Advaita-leaning (63.57% nirgun+oneness). Ravidas is the most Bhakti-leaning (13.89% devotional). Guru Amar Das has the strongest Stoic dimension (7.31% ethical).

No author is purely any one thing. The GGS is a convergence text -- it doesn't choose between non-dual metaphysics, devotional practice, and ethical self-discipline. It integrates all three.

## Each Guru Has a Distinctive Voice

The 18 authors of the GGS are not interchangeable. The data reveals striking differences:

**Guru Ram Das** saturates his compositions with HARI (3,663 times -- once every 1.9 lines). His nirgun density is the highest of any author at 62.27%. He is the nirgun maximalist.

**Guru Nanak** is the balanced founder. His register profile touches every dimension: nirgun (37.35%), sanskritic (23.54%), devotional (6.21%), ethical (4.28%), oneness (2.53%), ritual (2.55%), cleric (1.51%). He set the template.

**Guru Tegh Bahadur** has the highest devotional density (11.40%) and the highest ritual engagement (6.28%). He combines deep longing with sustained engagement with external practice. And he has *zero* Perso-Arabic vocabulary -- the only Guru with no Islamic register at all.

**Kabir** is the cross-tradition voice. His identity marker density is the highest (0.55%) -- he's where Hindu-Muslim vocabulary most frequently appears together. He also has the highest Perso-Arabic density among major contributors (1.43%).

**Farid** is the only author whose Perso-Arabic density (5.70%) exceeds his nirgun density (10.13%). His compositions read as Sufi devotional poetry. BIRHA (separation-longing) appears 5 times in only 158 lines.

## The Civilizational Question

Here's the finding that will generate the most debate: the GGS's vocabulary is **99.9% Sanatan-derived.**

For every 1 Islamic-register entity (Allah, Khuda, Qazi, Noor, etc.), there are 99.9 Sanatan-register entities (Hari, Naam, Brahm, Maya, Ram, etc.).

The Perso-Arabic register appears in only **0.29% of lines** (174 lines out of 60,629). By contrast, the Sanskritic register appears in 30.21% and the nirgun register in 42.25%.

This does *not* mean the GGS is "Hindu." The nirgun theology explicitly transcends both Hindu and Islamic categories. But the *vocabulary* through which that transcendence is expressed is overwhelmingly drawn from the Sanskritic-Punjabi lexical register.

## When ALLAH Appears

ALLAH appears in only 19 lines of the entire corpus. When it does appear:

- 21% of those lines *also* contain Indic divine names (RAM, HARI)
- ALLAH co-occurs with KHUDA (3 times) and NOOR (2 times)
- The context is consistently universalist-mystical, not legalistic

These are the "Aval Allah Noor Upaya" lines -- moments of explicit civilizational synthesis where the text deliberately bridges Islamic and Indic vocabulary.

## HINDU and TURK: Always Together

The most statistically surprising finding: HINDU and TURK have the **highest PMI (6.174) of any entity pair in the entire corpus.** Higher than any divine name cluster, any mythological grouping, any ritual pairing.

When the GGS names religious communities, it names them *together*. Always. In 10 of the angs where these terms appear, they appear on the same page. The text structurally refuses to critique one community without addressing both.

Only 31 lines in the entire 60,629-line corpus contain explicit religious identity labels. The GGS almost never names communities. When it does, it names them as a pair to transcend.

## What Kind of Text Is This?

Is the GGS a Bhakti text? An Advaita text? A Stoic-ethical text? An interfaith text?

The data says: it's all of these and none of them. It's a convergence text that:

1. Speaks overwhelmingly in nirgun vocabulary (42.25%)
2. Engages deeply with Sanskritic philosophy (30.21%)
3. Sustains a powerful devotional-emotional register (7.24%)
4. Prioritizes inner ethical transformation (5.46%) over ritual (2.2%)
5. Uses mythology to serve formless theology, never as standalone narrative
6. Engages with Islamic vocabulary rarely (0.29%) but deliberately
7. Treats religious identity as something to transcend, not to defend

The Guru Granth Sahib is quantitatively unique. No other scripture in the world has this particular combination: nirgun metaphysics expressed through devotional longing, ethical discipline, and Sanskritic philosophical vocabulary, with selective cross-civilizational synthesis.

The numbers don't interpret theology. They describe what the text actually does, line by line, word by word. And what it does is remarkable.

---

*This analysis was performed using a custom NLP pipeline processing the complete Unicode Gurmukhi text of the Guru Granth Sahib. 124 theological entities, 346 spelling variants, 11 feature dimensions, 18 identified authors. All claims are traceable to specific lines and entity matches. The full methodology and data are available at [the project repository].*
