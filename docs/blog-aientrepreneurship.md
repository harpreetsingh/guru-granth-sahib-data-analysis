# I Gave ChatGPT and Claude Code a 500-Year-Old Sacred Text and a Weekend. I Just Brought the Questions.

*A field report on running a real NLP pipeline with ChatGPT as product manager, Claude as engineer, and four AI agents in parallel.*

---

Over this long weekend, I did three things I'd never done before: built my first data science analysis project, published my first self-incepted open source project, and orchestrated a team of AI agents to do it.

I'm not a data scientist -- though I'm not a stranger to the work. As founder and co-CEO of Launchable, an AI company, I watched my team build data pipelines from 2019 onward. I understood the architecture. I could review the output. But I'd never taken an entire project end-to-end myself -- from the questions to the pipeline to the results. There was always a team to explain my vision to, and then wait for them to implement it. This weekend, for the first time, I didn't need that team. That was genuinely empowering.

The project: computationally analyzing the Guru Granth Sahib -- the central scripture of the Sikhs, 1,430 pages, 60,629 lines, six languages woven into Gurmukhi script. I'd wanted to do this since my early 20s. I don't read Punjabi fluently, and the interpretation of this text had always been outsourced to clerics. That felt like being illiterate.

The open source piece is personal. I've lived in OSS for most of my career -- five to six years in GlassFish, twelve years in Jenkins, building an enterprise business on top of it. But every one of those projects was someone else's vision that I contributed to. This is the first piece of work I conceived, built, and shipped myself. The entire GGS is now available as structured JSONL -- every line tagged, every entity traced to its source page. Anyone can query it.

And the agent orchestration connects to something I've written about before -- the Agent Flywheel System. This week I tried Claude's new agent teams harness (which, honestly, feels like they were heavily inspired by Agent Flywheel System). Four agents, dependency graphs, execution waves. The analysis I'd dreamed about for two decades became a weekend project because the AI stack finally caught up.

---

## The AI Architecture: Three Roles

The project used three distinct AI roles, each doing a different kind of cognitive work.

ChatGPT was the product manager. I spent hours in dialogue designing the analytical framework -- not "write me code," but "what are the right layers of analysis for a sacred text?" That conversation evolved through multiple iterations: from naive word counting, to the critical insight that lexical frequency and theological reference are different questions ("the token ਰਾਮ appears 2,019 times" is not the same claim as "the Hindu deity Rama is referenced 2,019 times"), to a three-layer architecture -- Lexical, Structural, Interpretive -- with explicit guardrails like "never collapse layers in reporting." The PRD that came out of this dialogue was 1,169 lines of serious engineering: data contracts, schema validation, normalization pipelines, error models.

Claude Code was the engineer. It built the entire pipeline: Aho-Corasick multi-pattern matching against 346 Gurmukhi spelling variants, 11-dimensional feature vectors per line, PMI co-occurrence analysis, author profiling. 733 tests passing. The methodology itself -- density scoring over boolean presence, PMI over raw co-occurrence, exact string matching over embeddings -- was recommended by Claude. It chose Aho-Corasick because with 346 patterns against 60,000 lines, regex would be O(patterns x text) while Aho-Corasick scans once. The full pipeline runs in under four seconds.

I was the domain expert. I built the 124-entity lexicon with 346 spelling variants across 11 theological dimensions. I decided what "nirgun" means, which entities matter, how to classify registers. I ran 10 iterations of planning with ChatGPT and Claude, ensuring my biases were weeded out -- kudos to ChatGPT, it flagged biased questions. The pipeline has no opinions. The lexicon does. And the lexicon is entirely human.

---

## The Agent Team

When it came time to execute, I didn't want one agent doing everything sequentially. I asked Claude to spawn agents. It analyzed the task graph and recommended 6 agents, noting that 8 would be a stretch. I ended up running 4 -- I could clearly see that a couple of agents would write to the same files, and unlike the Agent Flywheel System which has filesystem locking, here I needed to worry about that myself.

The tickets themselves were generated using beads_rust, a project tracker that gives me a dependency graph (I've written about this before -- LINK). At this point, this workflow works so well for me that handing it to opaque task management inside Claude doesn't feel right. I want to see the graph. I want to own the structure. Claude reviewed these tickets and built the dependency waves: which tasks can run in parallel, which are blocked, which agent gets which track.

[SCREENSHOT: dependency graph with execution waves]

Each agent got its own track, its own ticket queue ordered by dependency, its own prompt file. The backend agent was busy the entire time on the critical path. The CLI agent started immediately -- zero shared dependencies -- finished early, and picked up test tickets. The frontend agent was blocked until upstream work finished, so it studied the codebase while waiting, then ran its serial chain. All agents committed to the same branch. Git pull/push handled merges. Quality gates after every ticket.

This is the Agent Flywheel System in practice -- natively supported by Claude Agent Teams. The human defines the work and the structure. The AI analyzes the dependency graph, recommends team size, and executes. The coordination protocol -- who's blocked, who picks up slack, when to start the downstream agent -- came from Claude, not from me. I was the architect. Claude was the general contractor running the crew.

---

## The Irreducible Human

Here's what AI couldn't do: decide what questions to ask.

The entire project hangs on a 124-entity lexicon -- 346 spelling variants in Gurmukhi, organized across 11 theological dimensions: nirgun, sanskritic, devotional, ethical, oneness, ritual, cleric, sagun narrative, scriptural, Perso-Arabic, identity. Every entity, every dimension, every classification is domain knowledge. No model has that. I had to know that SAHIB (ਸਾਹਿਬ) isn't Perso-Arabic in the GGS context, even though it's etymologically Persian. That single reclassification dropped the Perso-Arabic register from 0.73% to 0.29%. The lexicon is the most valuable artifact in the project, not the pipeline.

The bias control was the hardest work. I came in with hypotheses -- everyone does when they care about a text. I ran 10 iterations of planning with ChatGPT and Claude, ensuring my biases were weeded out. Kudos to ChatGPT -- it flagged biased questions. But ultimately, the discipline of checking and rechecking was mine to maintain. The pipeline has no opinions. The lexicon does. And if your lexicon is biased, your results are biased. No amount of engineering rigor fixes a loaded question.

This is the punchline for anyone thinking about using AI for serious analytical work: AI collapses everything *around* the domain expertise. The engineering, the project management, the parallelization, the testing -- all compressed into a weekend. But the questions you ask, the categories you choose, the biases you catch -- that's still entirely you. And that's the part that matters most.

---

## What the Data Showed

The pipeline worked. 60,012 entity matches across 60,629 lines -- 57.3% of the text lit up. The headline: 42.25% of all lines contain nirgun (formless divine) vocabulary. Nearly half the text is about a nameless, formless reality. Add the oneness markers and it's 44.25% Advaita-adjacent. The Gurus were talking about non-dual philosophy -- the field, the formless -- before it became an Instagram trend.

The surprises were real. HARI -- a name for Lord Vishnu/Krishna -- appears 55 times for every 1 occurrence of WAHEGURU. Modern Sikh practice centers on Waheguru, but the text itself speaks a different lexical language. RAM, which appears 2,019 times, behaves statistically as a synonym for the formless divine, not as a reference to the Ramayana hero -- its co-occurrence neighborhood is indistinguishable from HARI's. And HINDU and TURK (Muslim) have the highest statistical association in the entire corpus. The central message of Sikhism is that all humans are equal -- and whenever the text references Hindu and Turk, it names them together to make the point that they are not different.

I wrote the full findings in a separate post (LINK) -- 13 findings, per-author profiles, the Stoic-Bhakti-Advaita triangle, the civilizational vocabulary ratio (99.9:1 Sanatan to Islamic). But the point for this audience isn't the theology. It's that a domain expert with an AI stack produced findings that are reproducible, auditable, and traceable to specific Gurmukhi lines. Every number links to a source. The repo is open. File a bug.

---

## The Takeaway

Here's the reusable framework. Step one: use ChatGPT to design the *what* -- the questions, the methodology, the architecture. Push back on yourself. Let the AI challenge your framing. Step two: use Claude Code to build the *how* -- the pipeline, the tests, the engineering. Let it recommend the methodology. Step three: when the task graph gets big enough, spawn Claude Agent Teams -- define the dependency waves, let agents run parallel tracks. And throughout: you are the domain expert. You own the lexicon. You own the bias control. You own the interpretation.

The ratio that matters isn't AI-to-human. It's thinking-to-building. This project was maybe 70% thinking -- what questions to ask, what entities to track, what dimensions capture the theology, what claims the data can support -- and 30% building. AI inverted that ratio from what it would have been five years ago. The building used to be the bottleneck. Now the thinking is. And it should be.

I had a question about a sacred text I couldn't read. I'd carried it for two decades. Over this long weekend, with ChatGPT, Claude Code, and four agents, I answered it. The entire Guru Granth Sahib is now structured data, open source, queryable by anyone. That's what AI does for a domain expert with a question and a weekend.
