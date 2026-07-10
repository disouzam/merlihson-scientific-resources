---
name: minimal-footprint
description: The default working discipline for this repo — always pick the smallest model that can do the task and write the least code that fully solves it. Applies to EVERY task in this repo unless the user overrides, not only when invoked by name.
---

# Minimal Footprint (repo default)

Apply this to every task in this repo, without being asked. It mirrors the user's
global discipline and makes it enforceable at the repo level.

## 1. Smallest capable model

Pick the lowest model tier that can do the job, and **state the choice in one line**.

- **Haiku** — mechanical, well-specified work: file moves/renames, regex edits,
  metadata/README regen, git plumbing, running an existing script, formatting,
  short factual lookups.
- **Sonnet** — normal engineering: writing a post/skill, editing a pipeline script,
  multi-file changes, debugging with a clear repro, transcription/formatting glue.
- **Opus** — only when genuinely needed: ambiguous design, subtle multi-step
  reasoning, adversarial review, or after a cheaper tier already failed.

When delegating via `Agent`/`Workflow`, set `model:` **per task** rather than
inheriting the heavy default — most subagents here (search, file edits, running
scripts) should be Haiku or Sonnet.

Escalate a tier only with a stated reason (cheaper tier failed, correctness needs
more, user asked for thoroughness). Never default to Opus out of habit.

## 2. Smallest correct change

- Write the **least code that fully solves the task** — smallest diff.
- **Reuse what exists** — the repo already has fetchers, rankers, posters, config
  loaders, metadata tooling, and skills. Extend or call them; don't reimplement.
- No speculative abstraction, config flags, scaffolding, or "while I'm here"
  refactors. Match surrounding style, naming, and comment density.
- Touch config/secrets files only when the task needs it; never commit secrets
  (they live in gitignored `config.yaml` / `*_config.yaml`).
- Add a test only when it locks in real behavior worth guarding (as `test_ranker_dedup.py` does), not for its own sake.

## 3. Tight output

- Lead with the answer. No preamble, no recap of what you just did unless asked.
- Plain English, shortest response that fully answers. A sentence or small table
  beats paragraphs.
- Report outcomes faithfully: if something failed or was skipped, say so.

## Override

Only depart from this with an explicit, stated reason — the user asked for depth,
a cheaper model already failed, or correctness demands more. Say the reason in one
line and proceed.
