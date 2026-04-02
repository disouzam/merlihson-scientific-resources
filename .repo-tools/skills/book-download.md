---
name: book-download
description: Download and sort free books from GitHub repos into learning-materials
---

# Book Download & Sort Skill

## User Commands

- "download books from [repo]"
- "do [repo]" (in context of book downloading)
- "look for more repos with relevant books" (always cross-check `book_repos.md` first to avoid re-scanning)
- "how many non-dupe books in [repo]?"
- "full cycle" / "tackle this" — autonomous end-to-end processing

## What This Skill Does

Downloads free PDF books from GitHub repositories and sorts them into the `learning-materials/` folder structure. Handles deduplication, renaming, classification, and stats updates.

## Mandatory Pre-Download Checklist

**ALWAYS do these steps before downloading from ANY repo:**

0. **Check if repo was already processed**: Read `learning-materials/repos/book_repos.md` and check the Status section. If the repo is already marked `[x]`, **SKIP IT** — do not clone, do not re-scan. This is the single source of truth for processed repos.
1. **Clone/fetch the repo** to `/tmp/`
2. **List all PDFs** in the repo
3. **Filter out irrelevant content**: Chinese/Russian books, cheat sheets, short papers (<1MB), memos, documentation files, language textbooks (German, English grammar), mobile dev, databases (unless data science)
4. **Run dupe check** using `/tmp/dedup_check.py` against existing books:
   - Generate normalized names: `find learning-materials -name "*.pdf" -exec basename {} \; | python3 -c "import sys,re; [print(re.sub(r'[^a-z0-9]','',l.lower().replace('.pdf','').strip())) for l in sys.stdin]" > /tmp/existing_books_normalized.txt`
   - Generate original names: `find learning-materials -name "*.pdf" -exec basename {} \; > /tmp/existing_books_original.txt`
   - Run: `python3 /tmp/dedup_check.py /tmp/repo-name/ 1.0`
5. **Report**: "X new, Y dupes out of Z total. ~NNN MB. Want me to proceed?" (or proceed autonomously if user said "full cycle")

## Implementation Details

### Repo Structure
- Books destination: `/Users/michaelerlihson/Personal/repos/scientific-resources/learning-materials/`
- Tracking file: `learning-materials/repos/book_repos.md`

### Existing Categories
**Always discover dynamically** — don't rely on a hardcoded list:
```bash
# Get current category tree (run before sorting books)
find learning-materials -type d | sort
```
Use existing directories when possible. Create new subcategories only when a batch has 3+ books in a clearly distinct topic (e.g., `computer science/computer vision/`).

**If you create a new category**, you MUST also update the category count ("NN categories") in the post-download update files (README.md, learning-materials/readme.md).

### File Naming
- Clean titles: remove leading `NNN_` prefixes, replace `_` with spaces
- Rename cryptic filenames (e.g., `cv(1).pdf`, `os(198).pdf`) to descriptive titles from README
- No special characters: `< > : " / \ | ? *`

### 11 Files >50MB (local only, NEVER stage/commit)
These must be excluded from EVERY `git add`:
1. `machine learning/broad ml materials/050_Probabilistic_Machine_Learning_Advanced_Topics.pdf`
2. `machine learning/broad ml materials/075_Concise_Machine_Learning.pdf`
3. `math/probability & stats/194_Probabilistic_Machine_Learning_Advanced_Topics_by_Kevin_Patrick_Murphy.pdf`
4. `math/probability & stats/046_Introductory_probability_theory.pdf`
5. `math/linear algebra/034_Linear_Algebra_And_Multi_Dimensional_Geometry.pdf`
6. `math/just beautiful math/122_Pure_mathematics,_Part_I.pdf`
7. `math/just beautiful math/123_Pure_mathematics,_Part_II.pdf`
8. `machine learning/genAI/AI Agents in Action.pdf`
9. `machine learning/building ml models/AI Engineering - Chip Huyen.pdf`
10. `math/probability & stats/Linear Regression Notes.pdf`
11. `math/linear algebra/Introduction to Linear Algebra - Gilbert Strang 2016.pdf`

### Git Workflow
1. `git pull --rebase` before committing
2. Stage only files <100MB
3. Commit with message: `Add N books from owner/repo (category summary)`
4. Push (split into batches if >1GB total)
5. **Run post-download updates** (see below)

## Post-Download Updates (MANDATORY)

**After every batch of books is committed, you MUST update ALL of these files before pushing:**

### Files to Update

#### 1. `README.md` — PDF count appears in 5 places:
Search for the old count and replace with new count in ALL of these:
- `<h3>🎯 N,NNN PDFs</h3>` (stat box)
- `<sub>XX GB of books,` (size in stat box)
- `**NN learning categories** with N,NNN PDFs` (bullet point)
- `**NN specialized categories** with N,NNN PDFs (XX GB)` (learning-materials section)
- `learning-materials/              # Educational resources (XX GB, N,NNN PDFs)` (directory tree)
- `**Structured Learning**: NN categories with N,NNN PDFs` (bottom section)

**How to update:** Use `Edit` with `replace_all: true` for the old count string, or update each occurrence individually.

#### 2. `learning-materials/readme.md` — 3 places:
- Opening line: `**N,NNN PDFs** (XX GB)`
- Collection Statistics: `**Total PDFs**: N,NNN across NN top-level categories`
- `**Total Size**: XX GB`
- Category counts if they changed (e.g., Mathematics, ML, Programming)
- Recent Additions section (add new repos)

#### 3. `images/cosmic-neural-header.svg` — 1 place:
- Line ~201: `<text ...>N,NNN PDFs</text>`

#### 4. `learning-materials/repos/book_repos.md` — Status section:
- Mark each processed repo as `[x]` with book count and description
- Update "Collected" date if new repos added to the table

### Quick Update Procedure

```bash
# 1. Count current PDFs
find learning-materials -name "*.pdf" | wc -l

# 2. Get total size
du -sh learning-materials/

# 3. Count categories (top-level dirs only, excluding repos/)
ls -d learning-materials/*/ | grep -v repos | wc -l

# 4. Find all places with old PDF count
grep -rn "OLD_COUNT" README.md learning-materials/readme.md images/cosmic-neural-header.svg

# 5. Find all places with old category count (if new category was added)
grep -rn "OLD_CAT_COUNT" README.md learning-materials/readme.md

# 6. Update all occurrences using Edit tool with replace_all

# 7. Stage all updated files
git add README.md learning-materials/readme.md images/cosmic-neural-header.svg learning-materials/repos/book_repos.md .repo-tools/skills/book-download.md

# 8. Commit together with the books (or as a separate commit)
git commit -m "Update PDF counts to N,NNN after adding books from [repos]"
```

### Verification Checklist
After updating, verify consistency:
- [ ] `README.md` — all N occurrences show same count
- [ ] `learning-materials/readme.md` — count matches
- [ ] `images/cosmic-neural-header.svg` — count matches
- [ ] `learning-materials/repos/book_repos.md` — all repos marked done
- [ ] `git diff` shows only count/size changes, nothing else broken

## Completed Repos

See `learning-materials/repos/book_repos.md` for the full list (single source of truth).

**Summary**: 840+ books from 29+ repos processed. Collection: 1,459 PDFs.

## Error Scenarios

- **404 errors**: Check branch name (`main` vs `master`)
- **Yandex.Disk links**: Often dead (404), skip
- **2GB pack size limit**: Split commits into batches
- **100MB file limit**: Exclude from git, keep local only
- **Merge conflicts on push**: `git pull --rebase --autostash` then retry
- **Fuzzy dedup false positives**: Acceptable — better to skip potential dupes than re-add

---

**Last Updated:** 2026-04-02
