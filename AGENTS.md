# AGENTS.md - Guru Granth Sahib Textual Analysis

This document describes how AI agents should operate within this project — a reproducible, line-level, auditable analysis platform for the Guru Granth Sahib.

---

## Rules for AI Agents

### RULE 0 - THE FUNDAMENTAL OVERRIDE PREROGATIVE
If I tell you to do something, even if it goes against what follows below, YOU MUST LISTEN TO ME. I AM IN CHARGE, NOT YOU.

### RULE 1 – ABSOLUTE (DO NOT EVER VIOLATE THIS)
You may NOT delete any file or directory unless I explicitly give the exact command in this session.

- This includes files you just created (tests, tmp files, scripts, etc.).
- You do not get to decide that something is "safe" to remove.
- If you think something should be removed, stop and ask. You must receive clear written approval before any deletion command is even proposed.
- Treat "never delete files without permission" as a hard invariant.

### IRREVERSIBLE GIT & FILESYSTEM ACTIONS — DO NOT EVER BREAK GLASS
Absolutely forbidden unless I give the exact command and explicit approval in the same message:

- `git reset --hard`
- `git clean -fd`
- `rm -rf`
- Any command that can delete or overwrite code/data

**No guessing:** If there is any uncertainty about what a command might delete or overwrite, stop immediately and ask for specific approval. "I think it's safe" is never acceptable.

**Safer alternatives first:** When cleanup or rollbacks are needed, request permission to use non-destructive options (`git status`, `git diff`, `git stash`, copying to backups) before ever considering a destructive command.

**Mandatory explicit plan:** Even after explicit authorization, restate the command verbatim, list exactly what will be affected, and wait for confirmation that your understanding is correct. Only then may you execute it—if anything remains ambiguous, refuse and escalate.

**Document the confirmation:** When running any approved destructive command, record in your response:
- The exact user text that authorized it
- The command actually run
- The execution time

If that audit trail is missing, the operation did not happen.

### Code Editing Discipline
**NEVER run scripts that process/change code files in this repo, EVER!** That sort of brittle, regex-based stuff is always a huge disaster and creates far more problems than it solves. No codemods, no invented one-off scripts, no giant sed/regex refactors.

- **Many simple changes:** Use several subagents in parallel to make changes faster, but still make each change manually.
- **Subtle/complex changes:** Methodically do them all yourself manually, file-by-file, with careful reasoning.

### Backwards Compatibility & File Sprawl
We do not care about backwards compatibility—we are in early development with no users. We want to do things the RIGHT way in a clean, organized manner with NO TECH DEBT.

- **No compatibility shims** or any similar nonsense.
- **No file clones:** You may NEVER take an existing file like `match.py` and create `matchV2.py`, `match_improved.py`, `match_enhanced.py`, `match_unified.py`, or ANYTHING ELSE REMOTELY LIKE THAT.
- **Revise in place:** When changing behavior, migrate callers and remove old code inside the same file.
- **New files are rare:** Only for genuinely new functionality that makes zero sense to include in any existing file. The bar for creating new files is INCREDIBLY high.

### Third-Party Libraries
If you aren't 100% sure about how to use a third-party library, you MUST search online to find the latest documentation website for the library to understand how it is supposed to work and the latest suggested best practices and usage. Never guess at APIs.

### Python Environment
- **Only use `uv`**, NEVER `pip`
- Use a venv
- **Only target Python 3.14** (we don't care about compatibility with earlier versions)
- **Only use `pyproject.toml`** (not requirements.txt) for managing the project

### Console Output
All console output should be informative, detailed, stylish, and colorful by fully leveraging the `rich` library wherever possible.

### Type Checking & Linting
**CRITICAL:** Whenever you make any substantive changes or additions to Python code, you MUST check that you didn't introduce any type errors or lint errors.

```bash
# Check for linter errors/warnings and automatically fix any found
ruff check --fix --unsafe-fixes

# Check for type errors
uvx ty check
```

If you see errors, carefully and thoughtfully understand and resolve each issue, reading sufficient context to truly understand the RIGHT way to fix them.

### Landing the Plane (Session Completion)
When ending a work session, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   br sync --flush-only    # Export beads to JSONL (no git ops)
   git add .beads/         # Stage beads changes
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Verify** - All changes committed AND pushed
6. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

---

## Project Overview

### What This Project Is

A reproducible, auditable, line-level analysis platform for the Guru Granth Sahib. All analysis is grounded in preserved Unicode Gurmukhi — no English translation drives analytical logic.

### Architecture

| Phase | Focus |
|-------|-------|
| **Phase 0** | Canonical Extraction (scraping + corpus creation) |
| **Phase 1** | Lexical Analysis (strict entity counting) |
| **Phase 2** | Structural Analysis (register density, co-occurrence) |
| **Phase 3** | Interpretive Tagging (rule-based, evidence-first) |
| **Phase 4** | Web Application (read-only, data-driven) |

Each phase is independent and reproducible.

### Repository Structure

```
config/        Configuration files (config.yaml)
lexicon/       Entity & marker definitions (YAML)
src/           Core pipeline code (Python)
scripts/       Phase runner scripts (shell)
data/          Raw + derived artifacts
tests/         Regression + matching tests
docs/          PLAN.md, PLAN_WEBAPP.md
```

### Design Principles

- Evidence-first
- No silent data loss
- All claims link to Gurmukhi lines
- Statistical claims include uncertainty
- Interpretive claims include rule trace
- This project is descriptive, not doctrinal

### Testing

```bash
pytest
```

Includes parser regression tests, lexicon lint tests, matching fixtures, and smoke pipeline tests (Ang 1–5 fixtures). CI does **not** scrape the live site.

---

## Issue Tracking with br (Beads)

All issue tracking goes through **Beads**. No other TODO systems.

**Key Invariants:**
- `.beads/` is authoritative state and **must always be committed** with code changes
- Do not edit `.beads/*.jsonl` directly; only via `br`

```bash
# Check ready work
br ready --json

# Create issues
br create "Issue title" -t bug|feature|task -p 0-4 --json
br create "Issue title" -p 1 --deps discovered-from:br-123 --json

# Update
br update br-42 --status in_progress --json
br update br-42 --priority 1 --json

# Complete
br close br-42 --reason "Completed" --json
```

**Types:** `bug`, `feature`, `task`, `epic`, `chore`

**Priorities:** `0` critical | `1` high | `2` medium (default) | `3` low | `4` backlog

**Agent Workflow:**
1. `br ready` to find unblocked work
2. Claim: `br update <id> --status in_progress`
3. Implement + test
4. If you discover new work, create a new bead with `discovered-from:<parent-id>`
5. Close when done
6. Commit `.beads/` in the same commit as code changes

### Beads CLI Reference

```bash
br list                        # List all issues/epics
br show <issue-id>             # Show issue details
br graph <epic-id>             # View epic dependency graph
br graph --all                 # Visualize all dependencies
br update <id> --status in_progress
br update <id> --status closed
br comments add <id> "description"
br sync --flush-only           # Export DB changes to JSONL
```

### Using bv as an AI Sidecar

bv is a graph-aware triage engine for Beads projects. Instead of parsing JSONL or hallucinating graph traversal, use robot flags for deterministic, dependency-aware outputs with precomputed metrics (PageRank, betweenness, critical path, cycles, HITS, eigenvector, k-core).

**CRITICAL: Use ONLY `--robot-*` flags. Bare `bv` launches an interactive TUI that blocks your session.**

**The Workflow — Start With Triage:**

```bash
bv --robot-triage        # THE MEGA-COMMAND: start here
bv --robot-next          # Minimal: just the single top pick + claim command
```

**Planning:**
| Command | Returns |
|---------|---------|
| `--robot-plan` | Parallel execution tracks with `unblocks` lists |
| `--robot-priority` | Priority misalignment detection with confidence |

**Graph Analysis:**
| Command | Returns |
|---------|---------|
| `--robot-insights` | Full metrics: PageRank, betweenness, HITS, eigenvector, critical path, cycles, k-core, articulation points, slack |
| `--robot-label-health` | Per-label health: `health_level` (healthy\|warning\|critical), `velocity_score`, `staleness`, `blocked_count` |
| `--robot-label-flow` | Cross-label dependency: `flow_matrix`, `dependencies`, `bottleneck_labels` |
| `--robot-label-attention [--attention-limit=N]` | Attention-ranked labels by: (pagerank x staleness x block_impact) / velocity |

**History & Change Tracking:**
| Command | Returns |
|---------|---------|
| `--robot-history` | Bead-to-commit correlations: `stats`, `histories` (per-bead events/commits/milestones), `commit_index` |
| `--robot-diff --diff-since <ref>` | Changes since ref: new/closed/modified issues, cycles introduced/resolved |

**Other Commands:**
| Command | Returns |
|---------|---------|
| `--robot-burndown <sprint>` | Sprint burndown, scope changes, at-risk items |
| `--robot-forecast <id\|all>` | ETA predictions with dependency-aware scheduling |
| `--robot-alerts` | Stale issues, blocking cascades, priority mismatches |
| `--robot-suggest` | Hygiene: duplicates, missing deps, label suggestions, cycle breaks |
| `--robot-graph [--graph-format=json\|dot\|mermaid]` | Dependency graph export |
| `--export-graph <file.html>` | Self-contained interactive HTML visualization |

**Scoping & Filtering:**
```bash
bv --robot-plan --label backend              # Scope to label's subgraph
bv --robot-insights --as-of HEAD~30          # Historical point-in-time
bv --recipe actionable --robot-plan          # Pre-filter: ready to work (no blockers)
bv --recipe high-impact --robot-triage       # Pre-filter: top PageRank scores
bv --robot-triage --robot-triage-by-track    # Group by parallel work streams
bv --robot-triage --robot-triage-by-label    # Group by domain
```

**Understanding Robot Output:**
- All robot JSON includes `data_hash` (fingerprint), `status` (per-metric state), `as_of` / `as_of_commit`
- Phase 1 (instant): degree, topo sort, density
- Phase 2 (async, 500ms timeout): PageRank, betweenness, HITS, eigenvector, cycles — check `status` flags
- For large graphs (>500 nodes): Some metrics may be approximated or skipped

**jq Quick Reference:**
```bash
bv --robot-triage | jq '.quick_ref'                        # At-a-glance summary
bv --robot-triage | jq '.recommendations[0]'               # Top recommendation
bv --robot-plan | jq '.plan.summary.highest_impact'        # Best unblock target
bv --robot-insights | jq '.status'                         # Check metric readiness
bv --robot-insights | jq '.Cycles'                         # Circular deps (must fix!)
bv --robot-label-health | jq '.results.labels[] | select(.health_level == "critical")'
```
