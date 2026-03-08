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

## What This Skill Does

Downloads free PDF books from GitHub repositories and sorts them into the `learning-materials/` folder structure. Handles deduplication, renaming, classification, and stats updates.

## Mandatory Pre-Download Checklist

**ALWAYS do these steps before downloading from ANY repo:**

1. **Clone/fetch the repo** to `/tmp/`
2. **List all PDFs** in the repo
3. **Filter out irrelevant content**: Chinese/Russian books, cheat sheets, short papers (<1MB), memos, documentation files
4. **Run dupe check** against existing books in `learning-materials/`:
   - Exact normalized match (strip spaces, hyphens, underscores, lowercase)
   - Fuzzy match (60%+ keyword overlap on significant words)
5. **Report to user**: "X new, Y dupes out of Z total. ~NNN MB. Want me to proceed?"
6. **Wait for user approval** before downloading

## Implementation Details

### Repo Structure
- Books destination: `/Users/michaelerlihson/Personal/repos/scientific_repo/learning-materials/`
- Tracking file: `learning-materials/repos/book_repos.md`
- Master tracking: `/Users/michaelerlihson/Personal/awesome-list-downloader/book_repos.md`

### Existing Categories (use these, don't create new ones)
```
algorithms/
computer science/
data engineering/analytics/
machine learning/broad ml materials/
machine learning/deep neural nets/
machine learning/nlp/
machine learning/reinforcement learning/
math/algebra/
math/analysis/
math/information theory/
math/just beautiful math/
math/linear algebra/
math/logic and foundations/
math/pdes/
math/physics/
math/probability & stats/
programming/general programming resources/
programming/general python resources/
programming/matlab/
programming/r & scala/
programming/software design/
python-ml-math/
```

### File Naming
- Clean titles: remove leading `NNN_` prefixes, replace `_` with spaces
- Rename cryptic filenames (e.g., `os(198).pdf`) to descriptive titles
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
1. `git stash && git pull --rebase && git stash pop` before committing
2. Stage only files <100MB
3. Commit with message: `add N books from owner/repo (source description)`
4. Push (split into batches if >1GB total)
5. Update stats in ALL locations (see Post-Download Updates)

## Post-Download Updates (MANDATORY)

After every batch, update ALL of these:

1. **`README.md`** — PDF count in 4 places:
   - `<h3>` stat box
   - `<sub>` size line
   - Bullet point "23 learning categories with NNN PDFs"
   - "23 specialized categories with NNN PDFs (X.X GB)"
   - Stats table `| **Learning Material PDFs** | NNN |`
   - Directory tree comment `# Educational resources (X.X GB, NNN PDFs)`
   - Bottom section "23 categories with NNN PDFs"

2. **`learning-materials/readme.md`** — PDF count in 2 places:
   - Opening line "**NNN PDFs** (X.X GB)"
   - Collection Statistics "**Total PDFs**: NNN across 23 top-level categories"
   - Size "**Total Size**: X.X GB"

3. **`images/cosmic-neural-header.svg`** — Box 3 text

4. **`learning-materials/repos/book_repos.md`** — Mark repo as done

5. **`~/Personal/awesome-list-downloader/book_repos.md`** — Master tracking

6. **Regenerate HTML links**: `cd /Users/michaelerlihson/Personal/repos/scientific_repo && python3 /tmp/gen_html.py`

## Completed Repos

| Repo | Books | Status |
|------|------:|--------|
| valeman/Awesome_Math_Books | 197 | Done |
| Carl-McBride-Ellis/Compendium | 128 | Done |
| aridiosilva/AI_Books | 31 | Done |
| cakaki68/Machine-Learning-Books | 52 | Done |
| camoverride/lit | 23 | Done |
| fadcrep/the-best-artificial-intelligence-books | 13 | Done |
| rohanmistry231/Mathematics-for-Machine-Learning-Books | 7 | Done |
| chaconnewu/free-data-science-books | 10 | Done |
| manjunath5496/Open-Access-Books | 69 | Done |
| AzatAI/cs_books | 40 | Done |
| Rafiquzzaman420/Math-Books | 13 | Done |
| md-sawrab/Statistics-Book-Collections | 29 | Done |
| mdnuruzzamanKALLOL/Machine-Learning-Book-Collections | 59 | Done |
| MinhNguyenDS/AI-pdf-books | 26 | Done |
| manjunath5496/AI-Books | 41 | Done |
| zslucky/awesome-AI-books | 0 | Dead links |
| rossant/awesome-math | 0 | Web links only |
| khuyentran1401/awesome-Python-data-science-books | 0 | Amazon links only |
| MasoudKaviani/freemachinelearninigbooks | 0 | Links only |
| joeldg/Deep-learning-books | 0 | Links only |
| demorenoc/springer-books | 0 | Markdown only |
| GauravWalia19/Free-Algorithms-Books | 18 | Done |
| GunterMueller/Books-3 | 59 | Done |
| gowtamkumar/DSA-Books | 0 | All <1MB |
| 0bprashanthc/algorithm-books | 0 | All dupes |
| ahkarami/Great-Deep-Learning-Books | 0 | Links only |

## Error Scenarios

- **404 errors**: Check branch name (`main` vs `master`)
- **Yandex.Disk links**: Use API `cloud-api.yandex.net/v1/disk/public/resources/download` — but links often dead
- **2GB pack size limit**: Split commits into batches
- **100MB file limit**: Exclude from git, keep local only
- **Merge conflicts on push**: `git stash && git pull --rebase && git stash pop`

---

**Last Updated:** 2026-02-27
