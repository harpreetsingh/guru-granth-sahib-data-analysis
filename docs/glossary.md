# Glossary

[Back to Table of Contents](./ANALYSIS_RESULTS.md)

This glossary defines key terms used throughout the analysis for readers
unfamiliar with Sikh scripture and South Asian religious traditions.

## Scripture & Structure

| Term | Meaning |
|------|---------|
| **Guru Granth Sahib (GGS)** | The central scripture of Sikhism, compiled in the 17th century. Sikhs regard it as a living Guru. |
| **Ang** | Literally "limb" -- the Sikh term for a page of the GGS. There are 1,430 angs. Sikhs say "ang" rather than "page" out of reverence. |
| **Shabad** | A hymn or composition. Our pipeline identifies **2,685 RAHAU markers**, each indicating a distinct compositional unit with a refrain structure. Traditional counts cite ~5,894 shabads (including compositions without RAHAU markers); this number is from external scholarly sources, not our pipeline. Our corpus does not contain shabad boundary markers, so we cannot independently verify the total shabad count. |
| **Mool Mantar** | "The Core Mantra" -- the opening declaration of the GGS (ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ). Translation: One Creator, Truth is the Name, Creative Being, Without Fear, Without Enmity, Timeless Form, Beyond Birth, Self-Existent, By Guru's Grace. |
| **Rahau** | "Pause" -- a refrain marker (ਰਹਾਉ) indicating the central theme of a shabad. Appears 2,685 times. |
| **Raga** | A melodic mode/framework from Indian classical music. The GGS is organized into 31 ragas, prescribing how each composition should be sung. Each raga has a distinct emotional and seasonal character. See the Ragas section below for the full list. |
| **Mahalla** | "Seat/household" -- identifies which Guru authored a composition (Mahalla 1 = Guru Nanak, Mahalla 5 = Guru Arjan, etc.). |
| **Bhagat** | A devotee-saint. The GGS includes compositions by 13 Bhagats from diverse traditions (Kabir, Namdev, Ravidas, Farid, etc.). |
| **Gurbani** | "The Guru's Word" -- the sacred text of the GGS. |

## The Ten Sikh Gurus

| # | Guru | Period | Role in the GGS |
|---|------|--------|-----------------|
| 1 | **Guru Nanak** | 1469-1539 | Founder of Sikhism. 11,230 lines (18.5%). Composed Japji Sahib and set the template for all subsequent Gurus. |
| 2 | **Guru Angad** | 1504-1552 | Standardized Gurmukhi script. 895 lines (1.5%). |
| 3 | **Guru Amar Das** | 1479-1574 | 9,041 lines (14.9%). Highest ethical register density among the Gurus. |
| 4 | **Guru Ram Das** | 1534-1581 | Founded Amritsar. 7,005 lines (11.6%). Highest nirgun density (62.27%). |
| 5 | **Guru Arjan** | 1563-1606 | Compiled the Adi Granth (1604). 26,036 lines (42.9%) -- the largest single contributor. Both the editor and the dominant voice of the GGS. |
| 6 | **Guru Hargobind** | 1595-1644 | Introduced the concept of Miri-Piri (temporal and spiritual authority). No compositions in the GGS. |
| 7 | **Guru Har Rai** | 1630-1661 | No compositions in the GGS. |
| 8 | **Guru Har Krishan** | 1656-1664 | No compositions in the GGS. Became Guru at age 5. |
| 9 | **Guru Tegh Bahadur** | 1621-1675 | 605 lines (1.0%). Highest devotional density (11.40%). Added by Guru Gobind Singh in the Damdami Bir (1706). |
| 10 | **Guru Gobind Singh** | 1666-1708 | Compiled the final edition of the GGS (Damdami Bir, 1706) but contributed none of his own compositions to it. His bani is collected in the Dasam Granth. Declared the GGS as the eternal Guru. |

Six of the ten Gurus (1-5 and 9) have compositions in the GGS, collectively
accounting for 90.4% of the text.

## Theological Concepts

| Term | Meaning |
|------|---------|
| **Nirgun** | "Without attributes" (nir = without, gun = qualities) -- the formless, attributeless aspect of the divine. The GGS is overwhelmingly nirgun in orientation (42.25% of lines). Contrasted with Sagun. |
| **Sagun** | "With attributes" (sa = with, gun = qualities) -- the divine as manifest in forms, names, and incarnations. Sagun narrative appears in only 0.51% of GGS lines. When the GGS references incarnation stories (Krishna, Shiv, Brahma), it almost always subordinates them to nirgun teaching. |
| **Naam** | "The Name" / "The Divine Name" -- a central concept in Sikh theology referring to the immanent presence of the divine in all creation. Not a specific word but a state of consciousness. Appears 5,464 times. |
| **Waheguru** | "Wonderful Lord" (Wahe = wonderful, Guru = teacher/lord) -- the most commonly used name for God in modern Sikh practice. Appears only 171 times in the GGS, far less than Hari (9,341). Waheguru became the primary name in the later Sikh tradition (post-GGS period), not in the scriptural text itself. |
| **Hari** | The most frequent divine name in the GGS (9,341 occurrences). While Hari is a name of Vishnu in broader Hindu tradition, in the GGS it is repurposed as a nirgun name for the formless, all-pervading divine consciousness -- not a reference to Vishnu as a specific deity. This is the single most important vocabulary finding in our analysis. |
| **Ram** | Appears 2,019 times. In the GGS, Ram functions as a nirgun name for the formless divine, not as a reference to the Ramayana prince Ramchandra. Co-occurrence analysis confirms this: RAM's top co-occurring entities are all nirgun-register (NAAM, HARI, GUR, PRABH). |
| **Prabh** | "Lord" -- the third most frequent divine name (2,647 occurrences). |
| **Hukam** | "Divine Will/Order" -- the principle that all of creation operates under one divine command. |
| **Maya** | "Illusion" -- the phenomenal world of attachment and duality that obscures the divine reality. From Sanskrit, used throughout the GGS (833 occurrences). |
| **Haumai** | "Ego/Self-centeredness" (hau = I, mai = me) -- the primary spiritual obstacle in Sikh theology. The root from which the Five Thieves arise. |

## Mool Mantar Attributes

These terms appear in the Mool Mantar (the opening declaration of the GGS)
and form the tightest co-occurrence cluster in the entire corpus (PMI 2.7-5.0):

| Term | Gurmukhi | Meaning |
|------|----------|---------|
| **Ik Onkar** | ੴ | "One Creator" -- the GGS opens with this symbol asserting the oneness of the divine. |
| **Satnam** | ਸਤਿ ਨਾਮੁ | "Truth is the Name" -- the divine is identified with truth itself. |
| **Nirbhau** | ਨਿਰਭਉ | "Without Fear" -- the divine is beyond all fear. |
| **Nirvair** | ਨਿਰਵੈਰੁ | "Without Enmity" -- the divine holds no hatred or animosity toward any being. |
| **Akal** | ਅਕਾਲ | "Timeless" / "Beyond Death" -- the divine exists outside of time. |
| **Moorat** | ਮੂਰਤਿ | "Form" / "Image" -- in the Mool Mantar, Akal Moorat = "Timeless Form." |
| **Ajooni** | ਅਜੂਨੀ | "Beyond Birth" / "Unborn" -- the divine does not enter the cycle of birth and death. |

## The Five Thieves (Panj Chor)

| Term | Meaning |
|------|---------|
| **Kaam** | Lust/desire (also polysemous: can mean "work") |
| **Krodh** | Anger/wrath |
| **Lobh** | Greed/avarice |
| **Moh** | Attachment/worldly entanglement |
| **Ahankar** | Pride/arrogance |

The traditional Five Thieves (using AHANKAR) collectively appear **1,699 times**
in the GGS. If HAUMAI (ego, 627 occurrences) is substituted for AHANKAR (89),
the total rises to 2,237. In Sikh theology, Haumai is the root from which the
Five Thieves arise; our pipeline tracks HAUMAI as a distinct entity. The text
devotes more space to inner moral struggle (5.46% of lines) than to ritual
practice (2.2%).

## Religious Identity Terms

| Term | Meaning |
|------|---------|
| **Hindu** | Refers to followers of Indic/Dharmic traditions. Appears in only ~31 lines. |
| **Turk** | The GGS's term for Muslims (from the Turkic Muslim rulers of medieval India). Almost always appears paired with "Hindu" -- the HINDU-TURK co-occurrence has the highest PMI (6.174) in the entire corpus. |
| **Musalman** | Muslim. Appears in ~7 lines. |
| **Qazi** | An Islamic judge/scholar. Referenced 26 times, often in compositions critiquing empty ritualism. |
| **Pandit** | A Hindu priest/scholar. Often paired with Qazi in passages that transcend both traditions. |
| **Mullah** | An Islamic cleric. Appears 22 times. |

## Mythological & Epic Figures

These figures from Hindu mythology appear in the GGS, typically invoked to
illustrate nirgun teaching rather than as objects of worship.

| Term | Meaning |
|------|---------|
| **Krishna** | An avatar of Vishnu; one of the most widely worshipped Hindu deities. In the GGS (68 matches), Krishna references are subordinated to nirgun theology. |
| **Vishnu (Bisn)** | The Preserver in the Hindu Trinity. In the GGS (40 matches), referred to as ਬਿਸਨ (Bisn). |
| **Shiv** | The Destroyer in the Hindu Trinity. 86 matches. Often invoked alongside Brahma and Vishnu to argue that all three are subordinate to the formless divine. |
| **Brahma** | The Creator in the Hindu Trinity. 50 matches. |
| **Indra (Indr)** | King of the gods in Vedic mythology. 27 matches. Referred to as ਇੰਦ੍ਰ (Indr) in Gurmukhi. |
| **Sita** | Consort of Ramchandra in the Ramayana epic. 8 matches. |
| **Ravan** | The demon king of Lanka in the Ramayana. 9 matches. |
| **Prahlad** | A devotee of Vishnu saved from his father Hiranyakashipu. 18 matches. Often cited as an exemplar of unwavering faith. |
| **Dhru** | The steadfast devotee who became the Pole Star through his devotion. 16 matches. |

## Devotional Vocabulary

| Term | Meaning |
|------|---------|
| **Pir** | Beloved / husband-lord. A bridal-mysticism term (359 matches) where the devotee is the bride and God is the husband. |
| **Kant** | Husband-lord / beloved. Another bridal-metaphor term (145 matches). |
| **Sohagan** | A blessed/fortunate bride -- one who has found union with the divine. |
| **Birha** | Separation-longing -- the pain of being apart from the divine beloved. A core Bhakti emotion (26 matches). |
| **Prem** | Love / divine love (228 matches). |
| **Sahaj** | Equipoise / natural state of spiritual balance (976 matches). |

## Ragas of the GGS

The GGS is organized into 31 ragas (melodic modes). Each raga carries a
particular emotional and seasonal character. The largest by size:

| Raga | Angs | Lines | Character |
|------|------|-------|-----------|
| **Gauri** | 151-346 | 9,626 | Serious, contemplative. The largest single raga. |
| **Aasaa** | 347-488 | 6,200 | Hope, aspiration. |
| **Maru** | 989-1106 | 5,181 | Desolation of the desert; longing. Contains concentrated Perso-Arabic vocabulary. |
| **Ramkali** | 876-974 | 4,466 | Philosophical. Contains Sidh Gosht and other major compositions. |
| **Sri Raag** | 14-93 | 3,161 | The first raga after the preamble. Noble, introductory. |
| **Suhi** | 728-794 | 2,657 | Emotional, intimate. Contains concentrated cleric-critique vocabulary. |
| **Sorath** | 595-659 | 2,642 | Separation, yearning. |
| **Bilawal** | 795-858 | 2,613 | Joyful, celebratory. |
| **Vadhans** | 557-594 | -- | Devotion, separation. Contains highest nirgun and devotional density peaks. |
| **Dhanasri** | 660-695 | -- | Devotional, emotional. Second-highest devotional density. |
| **Majh** | 94-150 | -- | Foundational. Contains Guru Nanak's compositions with highest oneness density. |
| **Tilang** | 721-727 | 275 | One of the smaller ragas. Notable for Perso-Arabic vocabulary. |
| **Bairari** | 719-720 | 51 | The smallest raga (2 angs). |

## Philosophical Traditions

| Term | Meaning |
|------|---------|
| **Advaita** | "Non-dual" -- the Vedantic philosophical tradition asserting that ultimate reality is one, without a second. The GGS is strongly Advaita-adjacent (44.25% nirgun + oneness). |
| **Bhakti** | Devotion/love -- a pan-Indian spiritual movement emphasizing personal devotion to the divine. The GGS has a substantial Bhakti dimension (7.24% devotional). |
| **Stoic** | Used in this analysis to describe the GGS's ethical dimension (5.46%) -- inner self-mastery, cultivation of virtue, equanimity. An analogy to Greco-Roman Stoicism, not a direct lineage. |
| **Vedantic** | Relating to Vedanta, the philosophical tradition derived from the Upanishads. The GGS engages deeply with Vedantic vocabulary (30.21% sanskritic register). |
| **Sufi** | Islamic mysticism. Farid's compositions (158 lines) represent the Sufi voice in the GGS. |
| **Sant Bhasha** | "Saint's language" -- the literary lingua franca used by medieval North Indian saints. A blend of Punjabi, Braj Bhasha, and regional dialects, all written in Gurmukhi script. |

## Linguistic Terms

| Term | Meaning |
|------|---------|
| **Gurmukhi** | "From the Guru's mouth" -- the script used to write the GGS. All text is in Gurmukhi regardless of the underlying language. |
| **Sanskritic register** | Vocabulary derived from Sanskrit philosophical tradition (Brahm, Maya, Atma, Karam, Dharma). |
| **Perso-Arabic register** | Vocabulary derived from Persian and Arabic (Allah, Khuda, Noor, Qazi). |
| **Braj Bhasha** | A literary dialect of Hindi used by many Bhagats (Kabir, Namdev, Ravidas). Detectable through distinctive pronouns (ਮੋਹਿ, ਤੋਹਿ) and verb forms (ਕਰਤ, ਹੋਤ). |

## Analysis Terms

| Term | Meaning |
|------|---------|
| **PMI (Pointwise Mutual Information)** | A statistical measure of how much more often two entities co-occur than expected by chance. High PMI = surprisingly frequent co-occurrence. |
| **Density** | Entity count divided by token count for a line or ang. A density of 0.30 means 30% of the tokens on that ang are recognized entities from a given register. Values range from 0 to 1. |
| **Total Hits** | The number of individual entity matches across all lines. A single line can produce multiple hits if it contains multiple entities. |
| **Lines Hit** | The number of unique lines containing at least one entity from a given dimension. Always less than or equal to Total Hits. |
| **Co-occurrence** | Two entities appearing on the same ang (page). Used to discover semantic relationships between entities. |
| **Register** | The linguistic origin/tradition of vocabulary: sanskritic, perso_arabic, neutral, or mixed. |
| **Polysemous** | Having multiple meanings. Five entities in our lexicon are flagged as polysemous (e.g., ਕਰਮ = karma/action/grace). |
