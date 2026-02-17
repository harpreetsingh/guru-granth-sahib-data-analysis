# Newsletter Blog Notes (newsletter.harpreet.io)

Target: 1000-2000 word AI-focused blog post about building this project.

---

## What the project IS

Computational analysis of the Guru Granth Sahib (GGS) -- the central scripture and Living Guru of the Sikhs. 60,629 lines, 396,036 tokens, 1,430 pages, 18 authors, 6 languages, written over 200 years. All in Gurmukhi script.

**The personal motivation:** Harpreet grew up Sikh but couldn't truly read the GGS (6 languages woven into Gurmukhi script). Interpretation was outsourced to clerics. He'd been curious since his early 20s about basic questions: What's the core philosophy? How much is Advaita (non-dual)? What's the Sanatan (Hindu) vs Islamic influence? AI made this possible for a non-data-scientist in a long weekend.

---

## The AI Stack & Workflow

### PRD with ChatGPT
- Used ChatGPT to write the Product Requirements Document (PLAN.md)
- The PRD is *serious engineering*: 1,169 lines, 4 phases, data contracts, schema validation, error models, normalization pipeline, CI strategy
- This isn't "ask ChatGPT a question" -- it's using AI as a product manager/architect
- 10 iterations of the PRD to keep biases out

### Code with Claude Code
- Entire pipeline built with Claude Code (CLI)
- Methodology of analysis was *recommended by Claude Code*
- Key technical choices Claude made/helped with:
  - **Aho-Corasick** multi-pattern matching (not regex) -- scans 60K lines against 346 patterns in <4 seconds
  - **Density scoring** (continuous [0,1]) rather than boolean presence
  - **PMI** (Pointwise Mutual Information) for co-occurrence -- surfaces surprising associations, not just frequent ones
  - **11-dimensional feature vectors** per line -- engineered from lexicon metadata, not learned
  - **Exact string matching** over embeddings -- Gurmukhi is low-resource, no good pre-trained models for archaic register
- Python 3.14, uv, rich for console output
- 733 tests passing, ruff clean, all quality gates green

### What the human did
- Domain expertise: Built the 124-entity lexicon (346 spelling variants in Gurmukhi) across 11 theological dimensions
- Bias control: 10 iterations of checking/rechecking to keep personal biases out
- Interpretation: The data doesn't interpret theology -- the human does
- Strategic decisions: deprioritized webapp, chose blog + YouTube + GitHub as distribution

---

## Key Design Decisions & Why

### 1. Gurmukhi-first, no English translation
- Core principle: "Gurmukhi text is the ground truth. All analysis is derived from preserved Unicode Gurmukhi. No English translation drives analysis logic."
- Why: Translations carry the translator's interpretation. Working on the raw text means no intermediary bias.

### 2. Deterministic, reproducible, auditable
- Every run produces identical output
- Every count links back to specific Gurmukhi lines
- Version-controlled lexicon (YAML)
- Run manifests with git commit hashes, artifact hashes
- Full pipeline completes in <4 seconds

### 3. String matching over ML
- No transformers, no embeddings, no LLMs in the analysis pipeline
- Exact Gurmukhi token matching against a curated lexicon
- Polysemous terms flagged but not disambiguated (honest about limitations)
- Why: Gurmukhi is low-resource. No pre-trained models handle the archaic register. Exact matching is more reliable AND auditable.

### 4. Ang-level co-occurrence (a pragmatic limitation)
- Corpus has no shabad (hymn) boundary markers in the scraped data
- Used ang (page) as co-occurrence window -- coarser than ideal
- Acknowledged openly as a limitation rather than hand-waved

### 5. Lexicon as the knowledge layer
- 124 entities, 346 aliases, 11 dimensions, 7 traditions, 4 registers
- Each entity has: id, canonical Gurmukhi form, aliases, category, tradition, register, polysemy flag
- This is where the domain expertise lives -- not in the code
- The lexicon is the most valuable artifact, not the pipeline

### 6. SAHIB reclassification
- Initially classified SAHIB (ਸਾਹਿਬ) as perso_arabic -- this was wrong
- SAHIB is neutral (used across all registers in the GGS)
- Reclassification dropped Perso-Arabic register from 0.73% to 0.29%
- Example of how a single lexicon decision can materially change findings

---

## What AI enabled that wouldn't have been possible otherwise

1. **A non-data-scientist built a serious NLP pipeline** -- PRD-quality architecture, Aho-Corasick matching, PMI co-occurrence, 11-dimensional feature engineering
2. **A non-Punjabi-reader analyzed Gurmukhi text** -- the pipeline processes raw Unicode Gurmukhi directly
3. **Weekend timeline** -- what would have been a multi-month academic project became a long weekend
4. **Methodology suggestion** -- Claude Code recommended the analytical methodology, not just implemented it
5. **Quality engineering** -- 733 tests, property-based testing with Hypothesis, schema validation, CI pipeline. Professional-grade engineering from a non-engineer.

---

## The results (brief -- link to the main blog)

- 42.25% of lines are nirgun (formless divine) -- nearly half the text is about a nameless, formless reality
- HARI appears 55x more than WAHEGURU (modern Sikh practice centers on Waheguru; the text itself uses Hari)
- RAM behaves statistically as a synonym for the formless divine, not as a reference to the Ramayana hero
- 99.9:1 Sanatan-to-Islamic vocabulary ratio -- but the theology transcends both
- HINDU and TURK have the highest PMI in the entire corpus -- when the text names communities, it names them together
- The Five Thieves (inner vices) get 2.5x more attention than ritual
- 0.12% register mixing -- the multi-traditional character comes from editorial structure, not line-level blending

---

## Lessons / Themes for the newsletter

1. **AI as collaborator, not replacement** -- ChatGPT for product thinking, Claude for engineering, human for domain expertise and interpretation
2. **The PRD matters** -- the most important artifact was the requirements document, not the code. AI can write code all day; the hard part is knowing what to build.
3. **Low-resource languages are the frontier** -- Gurmukhi has no good pre-trained models. The solution was exact matching + human curation, not throwing a transformer at it.
4. **Reproducibility is a design choice** -- deterministic pipeline, version-controlled lexicon, artifact hashes. AI helped write it but the principle had to be imposed by the human.
5. **Bias control requires human discipline** -- 10 iterations of checking. The pipeline doesn't have opinions; the lexicon does. The human had to police their own assumptions.
6. **AI democratizes serious analysis** -- this project would have required a team (computational linguist, Gurmukhi expert, data engineer) a decade ago. One person did it in a weekend with AI tools.
7. **The interesting question is "what to build"** -- not "how to build it." AI collapses the how. The what -- the lexicon, the dimensions, the questions to ask -- that's still entirely human.

---

## Tone

- First-person, personal
- AI-practitioner audience (newsletter.harpreet.io readers)
- Not academic, not promotional
- Honest about limitations
- The story: "I had a question about a sacred text I couldn't read. AI let me answer it."

---

## ChatGPT/Harpreet Design Iterations (raw context)

The following captures the iterative design process between Harpreet and ChatGPT that shaped the project architecture. This is the "how the sausage was made" -- the PRD didn't spring forth fully formed. It evolved through dialogue.

---

### Iteration 1: Initial Vision & Three Phases

The first pass established the top-line vision:

> Build a **verifiable, line-level corpus of the Guru Granth Sahib (Ang 1-1430)** rooted in **canonical Gurmukhi text**, then layer **high-precision entity detection** and produce **auditable, methodologically defensible analyses**. Everything must be **reproducible**, **traceable to Ang+line**, and **minimize interpretive bias** (no English translation in the analysis path).

Three phases were defined:
- **Phase 1 -- Corpus build + strict counting** (high precision, low interpretation): Create canonical dataset, answer "How many times are entities referenced?" with strict auditable counting.
- **Phase 2 -- Expanded detection + structured analyses** (grouped, still defensible): Go beyond raw counts to structured quantitative insights -- tradition-reference analytics, pedagogy signals, linguistic register signals.
- **Phase 3 -- Higher-recall interpretation layers** (disambiguation + classification): Handle hard problems like "ਰਾਮ" meaning Rama vs formless divine. Hybrid approach: rules + context windows + optional LLM classification.

Key architecture decisions made in this first pass:
- Data source: srigranth.org servlet (store raw HTML snapshots for reproducibility)
- Unit of analysis: line as presented by source
- File formats: JSONL for data, YAML for lexicons, CSV for reports
- Text integrity: every line record includes source_url, retrieved_at, sha256, parser_version
- Matching: exact match first, regex only where needed, always store surface_form + span + rule_id
- Normalization: no destructive normalization in Phase 1; derived normalized field if needed later
- Testing: unit tests + audit mode (random sample 50 matches for manual verification)

Entity lexicon design from this iteration:
- Each entity: entity_id, aliases_gurmukhi, precision (high/medium/low), notes, enabled_phase
- RAM was explicitly flagged as `precision: low, enabled_phase: 3` with note "Ambiguous: Rama vs nirgun divine"
- KRISHNA was `precision: high, enabled_phase: 1`
- This precision/phase gating was a key design choice: start with what's unambiguous, defer the hard stuff

---

### Iteration 2: The RAM Disambiguation Debate

A critical dialogue about whether contextual disambiguation was needed:

**The question:** "If the word used is Rama, that itself is the signal. Why disambiguate?"

**ChatGPT's response (paraphrased):** There are two different research questions:
- A) "How many times does the word ਰਾਮ appear?" -- lexical, no disambiguation needed, defensible
- B) "How many times is the Hindu deity Rama referenced?" -- theological, requires disambiguation, very different claim

**The resolution:** Constrain the claim. Label metrics precisely. Phase 1 answers question A. Phase 3 can attempt question B.

This debate shaped a core principle: **never collapse layers in reporting**. Instead of "Rama is referenced 2,000 times," report: "The token ਰਾਮ appears 2,019 times. Co-occurrence analysis shows it behaves statistically as a nirgun name (27 nirgun co-occurrences vs 7 sagun at ang level)."

**The "Aval Allah Noor Upaya" example** crystallized this:
- Lexical layer: Allah = 1 occurrence
- Interpretive layer: universalist metaphysics, anti-hierarchy, non-sectarian unity -- NOT Islamic doctrinal endorsement
- The line uses Islamic language to dissolve religious hierarchy
- Naive counting ("Allah is referenced, therefore Islamic influence") would be misleading
- The layered architecture allows nuance to survive quantification

---

### Iteration 3: Evolution to the Three-Layer Architecture

The conversation evolved from "counting words" to a **multi-layer textual analysis framework**:

**Layer 1 -- Lexical (zero interpretation):**
- Token frequency, entity frequency, language cluster frequency
- "How many times does token X appear? Where? By which author? In which Raga?"
- No theology, no intent, no semantic judgment
- Must be 100% reproducible

**Layer 2 -- Structural (manuscript metadata):**
- Authorship distribution (Mahalla headers), Raga distribution, Ang progression
- "Does Guru Arjan use Perso-Arabic vocabulary differently than Guru Nanak?" -- structural, not interpretive
- Powerful and underestimated

**Layer 3 -- Interpretive (context classification):**
- Semantic classification with explicit labels: mythological_specific, nirgun_generic_divine, ritual_reference, polemic/critique, uncertain
- Structured tags per line, not prose commentary
- Requires gold standard annotation, rule-based heuristics, optional LLM classification

**The interpretive taxonomy (proposed and refined):**
- Religious Language Usage Type: mythological_reference, ritual_reference, scriptural_reference, office_holder_reference, universalizing_language, polemic_critique, nirgun_generic_divine
- Epistemic Mode: critique, endorsement, transcendence, didactic_instruction, experiential_claim
- Theological Axis: sagun_specific, nirgun_abstract, collapsing_duality, anti_formalism

**Critical guardrail:** Never collapse layers in reporting. Report each layer separately.

**ChatGPT's framing:** "Most debates on the Guru Granth Sahib fall into anecdotal quoting, ideological framing, cherry-picked examples. Your architecture allows raw lexical truth, structural metadata truth, explicit interpretive modeling. This moves the discussion from opinion to model."

---

### What this design process reveals (newsletter-relevant)

1. **The PRD was a dialogue, not a document** -- It evolved through back-and-forth between human domain knowledge and AI analytical thinking. The human brought the questions; the AI brought the methodology.

2. **AI pushed back productively** -- ChatGPT challenged the "just count words" instinct and forced precision about what claims the data could and couldn't support. The disambiguation debate made the project better.

3. **Architecture before code** -- The three-layer separation (Lexical/Structural/Interpretive) was designed in conversation BEFORE any code was written. This is the most important output of the ChatGPT collaboration.

4. **The guardrails came from the dialogue** -- "Never collapse layers in reporting," "label metrics precisely," "constrain the claim" -- these principles emerged from the iterative design, not from a textbook.

5. **ChatGPT as product manager, not coder** -- The ChatGPT sessions were about WHAT to build and HOW to think about the problem. The coding was delegated entirely to Claude Code. Different AI tools for different cognitive tasks.

6. **The evolution: counting → structure → interpretation** -- The project matured from "count deity names" to a multi-layer analytical framework through iterative refinement. Each iteration added rigor without adding complexity for the end user.

---

## Refined Framing (AGREED)

**Thesis: "Domain expert + AI = research team of one"**

AI doesn't replace domain expertise -- it collapses the *support staff* around it. The bottleneck moves from "how to build" to "what to build and what questions to ask."

The emotional hook is the GGS story (sacred text, personal journey, decades-old desire). The intellectual payload is the workflow architecture. The audience walks away with a reusable framework for their own domain-expert projects.

---

## The Decades-Old Desire (emotional core)

- Harpreet had wanted to analyze this text since his early 20s
- Didn't know how to build it, wasn't a data scientist, couldn't fluently read the 6 languages in Gurmukhi
- The weekend project finally happened because AI collapsed every barrier EXCEPT the domain expertise
- "I did most thinking on the right questions to ask" -- THIS is the thesis in one sentence
- The hard part was never the code. It was: What entities matter? What dimensions capture the theology? How do you avoid your own biases? What claims can the data actually support?

---

## Claude Agent Teams -- Actual Usage

### The GGS project
- Asked Claude to spawn agents for the analysis pipeline
- Claude recommended 6 agents, noted that 8 might be a stretch
- Ended up using 4 agents in practice
- This is parallel execution of independent workstreams -- not one agent doing everything sequentially

### The pattern (from joystream project screenshots -- same workflow)
- Claude analyzes the ticket/task graph and produces a **dependency graph with execution waves**
- Identifies which tasks can run in parallel, which are blocked
- Recommends optimal number of agents based on the dependency structure (not just "more is better")
- Each agent gets:
  - Its own track (e.g., backend, cli, frontend)
  - Its own ticket queue ordered by dependency
  - Its own agent prompt file (.claude/agents/{name}-agent.md)
  - Quality gates: run checks after each ticket, commit and push after each
- Agents run in separate tmux panes, each launched with `claude --print-cost -p "You are the [X] agent..."`
- Key coordination details:
  - Some agents can start immediately (no shared dependencies)
  - Some agents are BLOCKED until upstream work finishes
  - Blocked agents can "study the codebase" while waiting
  - All agents commit to the same branch -- git pull/push handles merges
  - Agent prompts reference AGENTS.md for project-wide rules

### What this means for the blog
- This is NOT "I asked an AI to write code" -- this is **orchestrating a team of AI agents** with dependency graphs, parallel execution, and coordination protocols
- The human role: define the work, structure the dependencies, decide how many agents, review the output
- Claude's role: analyze the dependency graph, recommend team size, execute the tickets, handle merges
- This is project management, not programming

### Concrete detail for the blog
- "Claude analyzed my 30 tickets, mapped the dependency graph into 6 execution waves, and recommended 3 agents. The backend agent was busy the entire time. The CLI agent finished early and picked up test tickets. The frontend agent was blocked for waves 1-5 and then ran its serial chain."
- The human didn't write the dependency graph. The human didn't decide which agent gets which ticket. Claude did the project management. The human decided what to build and how many agents to run.
