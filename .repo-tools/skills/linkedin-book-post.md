---
name: linkedin-book-post
description: Write a LinkedIn post about a book (from PDF or URL) in Michael's signature style — personal reflection on one or two key ideas, not a generic summary. Use when user asks to "write a linkedin post for [book]" or references their LinkedIn book post style.
---

# LinkedIn Book Post Skill

Write LinkedIn posts about technical/academic books in Michael Erlihson's voice. Posts go to `/Users/mike_erlihson/personal/linkedin_posts/post_N_<short_name>.txt` (next available N).

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

1. **Always ensure the book is in the repo (`learning-materials/`)** — do this every time, not optionally:
   - Check first: `find /Users/mike_erlihson/personal/repos/scientific-resources/learning-materials -iname "*<keywords>*"`
   - If found, tell the user it's already in the repo and skip the add.
   - If not found, copy it into the **most specific existing** subject folder
     (e.g. `learning-materials/math/analysis/`, `learning-materials/machine learning/`).
     Reuse an existing folder whenever one reasonably fits — **only create a new
     subfolder if no existing folder is an appropriate home**.
   - Then `git add` the file, commit, and push (authored as the repo's configured git user).
2. Save post as `/Users/mike_erlihson/personal/linkedin_posts/post_<N>_<short_name>.txt`
   - N = next available number (check existing files)
   - short_name = lowercase, underscores, ~3-4 words derived from book title
3. **Always copy the source book to the linkedin posts folder** so user has post + book together:
   - For PDF input: `cp <source.pdf> /Users/mike_erlihson/personal/linkedin_posts/`
   - Skip if file already exists there
   - For URL input: skip (no local file)
4. **Always render the title page (title + authors) as an image** into the same folder,
   as `post_<N>_<short_name>_title.png` — a visual to attach to the LinkedIn post.
   - Use PyMuPDF/`fitz` (poppler/pdftoppm is NOT installed; `pip install pymupdf` if missing).
   - Pick the right page: scan pages 1–6 and render the **first one whose text contains
     both the title and the author name(s)** — for many books that's page 1, for some
     (e.g. MIT Press) the half-title is p.1 and the full title+authors page is p.3.
   - `doc[i].get_pixmap(dpi=150).save(".../post_<N>_<short_name>_title.png")`
   - For URL input: skip, or grab the cover image from the page if one is available.
5. Briefly tell the user the filenames (post + title image) — do not paste the full post back unless asked
