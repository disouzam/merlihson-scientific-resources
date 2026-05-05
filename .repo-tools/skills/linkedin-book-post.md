---
name: linkedin-book-post
description: Write a LinkedIn post about a book (from PDF or URL) in Michael's signature style — personal reflection on one or two key ideas, not a generic summary. Use when user asks to "write a linkedin post for [book]" or references their LinkedIn book post style.
---

# LinkedIn Book Post Skill

Write LinkedIn posts about technical/academic books in Michael Erlihson's voice. Posts go to `~/Downloads/linkedin_posts_materials/post_N_<short_name>.txt` (next available N).

## Inputs

- **PDF**: Read pages 1-8 to capture cover, preface, TOC, and a sample of content
- **URL**: Use WebFetch to extract title, author, TOC, approach, and key topics

## Style template

Reference the canonical example (Michael's "Dynamic Programming" post):

```
Most technical discussions quietly assume that the objective is linear. This book keeps showing what breaks when that assumption is relaxed. 📐

One idea that stays with me is how much of dynamic programming depends on recursion, not on the specific objective. The moment you move to mean-variance or value-at-risk, the recursion disappears and the problem becomes almost unmanageable. It is not just harder. It is structurally different.

Another idea is the shift from thinking about values to thinking about operators. A policy is no longer just a rule. It becomes something that generates a fixed point. That reframes optimization as a question about stability and convergence rather than search.

What changes is the intuition. You stop asking what is optimal and start asking what survives iteration.

That feels closer to how real systems behave. 🤔

#DynamicProgramming #ReinforcementLearning #Optimization #DecisionTheory #AI
```

## Structure rules

1. **Hook (1-2 sentences)** — Set up tension: a common assumption the book challenges, or a gap it fills. End with a 📐 emoji.
2. **First idea ("One idea that stays with me...")** — Pick a specific, non-obvious insight. Be concrete. Show why it matters structurally, not just procedurally.
3. **Second idea ("Another idea is...")** — Different angle. Connect it to broader engineering or scientific intuition. Use "It is not X. It is Y."-style reframing where natural.
4. **Closing reframe ("What changes is..." or similar)** — One short sentence that distills how reading this book shifts the reader's thinking. End with 🤔 or similar.
5. **Hashtags** — 4-5 relevant tags. First two are usually field-level (`#Mathematics`, `#AI`, `#ComputerScience`); next 2-3 are specific (`#GraphTheory`, `#Optimization`).

## Voice rules

- First-person but understated — "stays with me", "I appreciated", never "I think this is amazing"
- No bullet points or numbered lists in the post itself
- No phrases like "must-read", "game-changer", "highly recommended"
- No "must-have" book endorsements — observation, not promotion
- Avoid LinkedIn cliches: "blown away", "thrilled to share", "humbled to announce"
- Prefer concrete claims over praise: "9 editions in" beats "an excellent textbook"
- Length: ~150-220 words, fits comfortably in one LinkedIn post without "see more" cutoff
- Sentences vary in length; short punchy ones land the reframes

## Output

1. Save post as `~/Downloads/linkedin_posts_materials/post_<N>_<short_name>.txt`
   - N = next available number (check existing files)
   - short_name = lowercase, underscores, ~3-4 words derived from book title
2. **Always copy the source book to the same folder** so user has post + book together:
   - For PDF input: `cp <source.pdf> ~/Downloads/linkedin_posts_materials/`
   - Skip if file already exists there
   - For URL input: skip (no local file)
3. Briefly tell the user the filename — do not paste the full post back unless asked
