---
name: book-download
description: Download and sort free books from GitHub repos into learning-materials
---

# Book Download & Sort Skill

## User Commands

- "download books from [repo]"
- "do [repo]" (in context of book downloading)
- "look for more repos with relevant books"
- "how many non-dupe books in [repo]?"
- "full cycle" / "tackle this" — autonomous end-to-end processing

## What This Skill Does

Downloads free PDF books from GitHub repositories and sorts them into the `learning-materials/` folder structure. Handles deduplication, renaming, classification, and stats updates.

## Mandatory Pre-Download Checklist

**ALWAYS do these steps before downloading from ANY repo:**

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

### Existing Categories (use these, create new subcategories only when needed)
```
ai/
algorithms/
computer science/
computer science/computer vision/
data engineering/
data science applications/
economics/
excel/
finance/
general reading/
interview preparation/
kubernetes/
machine learning/
machine learning/broad ml materials/
machine learning/deep neural nets/
machine learning/nlp/
machine learning/reinforcement learning/
machine learning/ML concepts, algorithms and machinery/
math/
math/algebra/
math/analysis/
math/combinatorics/
math/information theory/
math/just beautiful math/
math/linear algebra/
math/logic and foundations/
math/optimization/
math/pdes/
math/physics/
math/probability & stats/
MLOps/
programming/
programming/general programming resources/
programming/general python resources/
programming/matlab/
programming/r & scala/
programming/software design/
python-ml-math/
quantum computing/
signal processing/
sql/
surveys/
visualisation/
```

### File Naming
- Clean titles: remove leading `NNN_` prefixes, replace `_` with spaces
- Rename cryptic filenames (e.g., `cv(1).pdf`, `os(198).pdf`) to descriptive titles from README
- No special characters: `< > : " / \ | ? *`

### 7 Files >100MB (local only, NEVER stage/commit)
These must be excluded from EVERY `git add`:
1. `machine learning/broad ml materials/050_Probabilistic_Machine_Learning_Advanced_Topics.pdf`
2. `machine learning/broad ml materials/075_Concise_Machine_Learning.pdf`
3. `math/probability & stats/194_Probabilistic_Machine_Learning_Advanced_Topics_by_Kevin_Patrick_Murphy.pdf`
4. `math/probability & stats/046_Introductory_probability_theory.pdf`
5. `math/linear algebra/034_Linear_Algebra_And_Multi_Dimensional_Geometry.pdf`
6. `math/just beautiful math/122_Pure_mathematics,_Part_I.pdf`
7. `math/just beautiful math/123_Pure_mathematics,_Part_II.pdf`

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

# 3. Find all places with old count in README.md
grep -n "OLD_COUNT" README.md

# 4. Update all occurrences
# Use Edit tool with replace_all for each file

# 5. Stage all updated files
git add README.md learning-materials/readme.md images/cosmic-neural-header.svg learning-materials/repos/book_repos.md

# 6. Commit together with the books (or as a separate commit)
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

**Summary**: 663+ books from 22+ repos processed. Collection: 1,280 PDFs.

## Error Scenarios

- **404 errors**: Check branch name (`main` vs `master`)
- **Yandex.Disk links**: Often dead (404), skip
- **2GB pack size limit**: Split commits into batches
- **100MB file limit**: Exclude from git, keep local only
- **Merge conflicts on push**: `git pull --rebase --autostash` then retry
- **Fuzzy dedup false positives**: Acceptable — better to skip potential dupes than re-add

---

**Last Updated:** 2026-03-11
