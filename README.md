<div align="center">

<img src="./images/cosmic-neural-header.svg" alt="Scientific Resources Hub" width="100%">

<br>

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)
[![Last Updated](https://img.shields.io/badge/Updated-February_2026-success.svg)](#)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](METADATA_UPDATE_PROCESS.md)

**Your one-stop knowledge base for AI/ML research, learning, and reference**

[Explore Reviews](#-paper-reviews) • [Learning Materials](#-learning-materials) • [Presentations](#-presentations) • [Quick Start](#-quick-start)

</div>

---

## Highlights

<table>
<tr>
<td align="center" width="25%">
<h3>📄 573+</h3>
<b>Paper Reviews</b><br>
<sub>Deep analysis of cutting-edge<br>AI/ML research papers</sub>
</td>
<td align="center" width="25%">
<h3>📚 21</h3>
<b>Learning Categories</b><br>
<sub>From ML basics to<br>quantum computing</sub>
</td>
<td align="center" width="25%">
<h3>🎯 2.0 GB</h3>
<b>Resources</b><br>
<sub>PDFs, presentations,<br>cheat sheets & more</sub>
</td>
<td align="center" width="25%">
<h3>📅 2022-26</h3>
<b>Coverage Period</b><br>
<sub>Continuously updated<br>with latest research</sub>
</td>
</tr>
</table>

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Paper Reviews](#paper-reviews)
- [Learning Materials](#learning-materials)
- [Presentations](#presentations)
- [Metadata & Search](#metadata--search)
- [Automated Metadata Updates](#automated-metadata-updates)
- [Daily Review Automation](#daily-review-automation)
- [Collection Statistics](#collection-statistics)
- [Repository Structure](#repository-structure)
- [For Researchers & Students](#for-researchers--students)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This repository is a **curated knowledge base** for AI/ML researchers, students, and practitioners. It contains:

- **573 comprehensive paper reviews** covering cutting-edge AI/ML research (2022-2026)
- **21 learning categories** spanning machine learning, mathematics, algorithms, and more
- **9 research presentations** on deep learning architectures
- **Searchable metadata indices** for quick paper discovery
- **Python tooling** for document processing and automation

---

## Quick Start

### Find a Specific Paper
```bash
# Search by title in the metadata index
grep -i "transformer" mike-paper-reviews-all/reviews_metadata/all_paper_titles.txt

# Or browse the CSV with paper links
cat mike-paper-reviews-all/reviews_metadata/paper_with_links.csv
```

### Access Reviews
| What you want | Where to find it |
|---------------|------------------|
| Individual review files (DOCX) | `mike-paper-reviews-all/split-reviews-docx/Review_001.docx` - `Review_572.docx` |
| Individual reviews (Markdown) | `mike-paper-reviews-all/split-hebrew-reviews-md/Review_001.md` - `Review_572.md` |
| All paper titles | `mike-paper-reviews-all/reviews_metadata/all_paper_titles.txt` |
| Papers with links (100% coverage) | `mike-paper-reviews-all/reviews_metadata/paper_with_links.csv` |
| Archived PDFs and old formats | `mike-paper-reviews-all/archive/` |

---

## Paper Reviews

### `mike-paper-reviews-all/`

The core collection containing **572 individual paper reviews** in multiple formats.

| Type | Count | Description |
|------|-------|-------------|
| **Individual Reviews** | 1-208 | Deep-dive analyses with paper links |
| **Daily Reviews** | 365-572 | Chronological reviews (May 2024 - Feb 2026) |

#### Formats Available
- **`split-hebrew-reviews-md/`** - 572 Hebrew review markdown files (primary format)
- **`split-english-reviews-md/`** - 205 English review markdown files
- **`split-reviews-docx/`** - 572 DOCX source files (`Review_001.docx` → `Review_572.docx`)
- **`reviews_metadata/`** - Auto-updated metadata (100% link coverage)
- **`archive/`** - Historical PDFs and old batch documents

#### Research Domains Covered
| Domain | Topics |
|--------|--------|
| **Deep Learning** | CNNs, RNNs, Transformers, Novel Architectures |
| **NLP** | LLMs, Text Generation, Language Understanding |
| **Computer Vision** | Image Recognition, Object Detection, Segmentation |
| **Generative Models** | GANs, VAEs, Diffusion Models, Autoregressive |
| **Multimodal** | Vision-Language Models, Cross-Modal Learning |
| **Reinforcement Learning** | Policy Learning, Decision Making |
| **Optimization** | Training Algorithms, Regularization, Efficiency |

---

## Learning Materials

### `learning-materials/`

**22 specialized categories** with 1.7 GB of educational resources:

<table>
<tr>
<td width="50%">

#### Core AI/ML
- `machine learning/` - 15 subcategories
  - Deep neural nets
  - NLP & GenAI
  - Reinforcement learning
  - Conformal prediction
  - Time series
  - Fairness in ML
- `ai/` - General AI concepts
- `deep learning/` - Architecture deep-dives

</td>
<td width="50%">

#### Mathematics & CS
- `math/` - Mathematical foundations
- `algorithms/` - Data structures & methods
- `computer science/` - CS fundamentals
- `signal processing/` - Signal analysis
- `quantum computing/` - Quantum ML

</td>
</tr>
<tr>
<td>

#### Programming & Tools
- `programming/` - Languages & practices
- `python-ml-math/` - Integrated tutorials
- `data engineering/` - Pipelines & processing
- `MLOps/` - ML operations
- `kubernetes/` - Container orchestration
- `sql/` - Database queries
- `excel/` - Spreadsheet techniques
- `visualisation/` - Data visualization

</td>
<td>

#### Applied & Career
- `data science applications/` - Real-world DS
- `finance/` - Financial modeling
- `economics/` - Economic analysis
- `interview preparation/` - 32+ resources
- `surveys/` - Academic surveys
- `selected papers/` - Curated readings

</td>
</tr>
</table>

---

## Presentations

### `presentations/`

**9 research presentations** covering major deep learning topics:

| Presentation | Topic |
|--------------|-------|
| `CNN_Intro_INT_12_2020.pptx.pdf` | Convolutional Neural Networks |
| `Intro_to_RNNs_Transformers.pdf` | RNNs and Transformer basics |
| `Intro to Transformers_ NLP 3rd Meetup.pdf` | Transformers for NLP |
| `Survey of Transformers_ NLP Meetup.pdf` | Comprehensive Transformer survey |
| `Generative Adversarial Networks (GAN).pdf` | GAN architectures |
| `Diffusion Models for Data Generation.pdf` | Diffusion model introduction |
| `Text2Any Generative DDPMs_ 2022-2023.pdf` | Text-to-X generation |
| `Unsupervised Learning of Visual Features.pdf` | Contrastive learning (SwAV) |

---

## Metadata & Search

### `mike-paper-reviews-all/reviews_metadata/`

Searchable indices for quick paper discovery:

| File | Purpose |
|------|---------|
| `all_paper_titles.txt` | 546+ indexed paper titles (numbered list) |
| `clean_titles_for_search.txt` | Sanitized titles for programmatic search |
| `paper_with_links.csv` | Review number → ArXiv URL mappings |
| `reviews_1_207_titles.txt` | Index for individual reviews |
| `reviews_from_208_titles.txt` | Index for daily reviews |

### Example: Find Papers on Attention Mechanisms
```bash
grep -in "attention" mike-paper-reviews-all/reviews_metadata/all_paper_titles.txt
# Output: 42. FlashAttention: Fast and Memory-Efficient Exact Attention
#         156. Attention Is All You Need (Revisited)
#         ...
```

---

## 🤖 Automated Metadata Updates

### Git Pre-Commit Hook

This repository includes **automated metadata synchronization** via a git pre-commit hook. When you commit review files, all metadata indices are automatically updated and included in your commit.

#### What Gets Auto-Updated

Every time you commit a `Review_*.md` file, the hook automatically:

1. ✅ Extracts paper title and link from the review
2. ✅ Updates `paper_with_links.csv` with the new entry
3. ✅ Updates `all_paper_titles.txt` with numbered title
4. ✅ Updates `clean_titles_for_search.txt` for search indexing
5. ✅ Updates `reviews_from_208_titles.txt` (for reviews 208+)
6. ✅ Stages all updated metadata files
7. ✅ Includes them in your commit automatically

#### How It Works

```bash
# 1. Add a new review file
git add mike-paper-reviews-all/split-hebrew-reviews-md/Review_574.md

# 2. Commit (hook runs automatically!)
git commit -m "Add Review_574: Paper Title"

# Output you'll see:
# 📝 Detected review markdown changes, updating metadata...
# Extracting metadata from Hebrew review files...
# Extracted 573 reviews
# ✓ Metadata updated successfully
# ✓ Metadata files staged for commit

# 3. Push to remote
git push
```

#### Supported Paper Sources

The hook extracts links from multiple sources:
- **ArXiv** - Primary source for ML/AI papers
- **Nature** - High-impact journal articles
- **ACM Digital Library** - Computer science publications
- **OpenAI** - Direct paper releases and blog posts
- **Google Research** - Research blog publications
- **OpenReview** - Conference submissions
- **HuggingFace Papers** - Community papers
- **DOI Links** - Universal paper identifiers
- And more...

#### Coverage Statistics

| Metric | Value |
|--------|-------|
| **Total Reviews** | 572 |
| **With Paper Links** | 572 (100% coverage!) |
| **Auto-Extracted** | 571 |
| **Manually Added** | 1 |

No manual CSV editing needed! 🎉

---

## 🤖 Daily Review Automation

This repository includes **automated daily processing** of paper reviews. Every day at 5:00 AM, the system automatically checks for new review files and processes them end-to-end.

### What It Does

The daily automation:

1. ✅ **Scans** `~/Downloads/` for new `Review_XXX.docx` files
2. ✅ **Checks for duplicates** - skips reviews already in repo
3. ✅ **Copies** Hebrew DOCX to `split-reviews-docx/`
4. ✅ **Converts** Hebrew DOCX to markdown with title formatting
5. ✅ **Converts** English DOCX if present
6. ✅ **Commits** changes with descriptive message
7. ✅ **Updates metadata** automatically via pre-commit hook
8. ✅ **Pushes** to GitHub
9. ✅ **Logs** all actions for monitoring

### Setup

The automation is set up via launchd (macOS native scheduler):

```bash
# Install daily job (runs at 5:00 AM)
cd .repo-tools/scripts
./schedule_daily_job.sh
```

### Manual Processing

You can also run the processor manually:

```bash
# Test without making changes
python3 .repo-tools/scripts/daily_review_processor.py --dry-run

# Process new reviews now
python3 .repo-tools/scripts/daily_review_processor.py
```

### Monitoring

View automation logs:

```bash
# View recent activity
tail -f .repo-tools/logs/daily_processor.log

# View errors
cat .repo-tools/logs/daily_processor_error.log
```

### Management

```bash
# Check if job is running
launchctl list | grep daily-review

# Run immediately (don't wait for 5 AM)
launchctl start com.user.daily-review-processor

# Uninstall
launchctl unload ~/Library/LaunchAgents/com.user.daily-review-processor.plist
```

For detailed documentation, see [.repo-tools/scripts/README.md](.repo-tools/scripts/README.md)

---

## Collection Statistics

| Metric | Value |
|--------|-------|
| **Total Paper Reviews** | 573 |
| **Hebrew Reviews (Markdown)** | 573 files |
| **English Reviews (Markdown)** | 205 files |
| **Reviews with Paper Links** | 572 (100% coverage!) |
| **Daily Reviews** | 365 (May 2024 - Feb 2026) |
| **Learning Categories** | 21 |
| **Presentations** | 9 |
| **Total Repository Size** | 2.0 GB |
| **Coverage Period** | 2022-2026 |
| **Languages** | English + Hebrew |
| **License** | CC0-1.0 (Public Domain) |

---

## Repository Structure

```
scientific-resources/
├── mike-paper-reviews-all/          # Main review collection
│   ├── split-hebrew-reviews-md/     # 572 Hebrew review markdown files ⭐
│   │   ├── Review_001.md
│   │   ├── Review_002.md
│   │   └── ... → Review_572.md
│   ├── split-english-reviews-md/    # 205 English review markdown files
│   ├── split-reviews-docx/          # 572 DOCX source files
│   │   ├── Review_001.docx
│   │   └── ... → Review_572.docx
│   ├── reviews_metadata/            # Auto-updated metadata (100% coverage) 🤖
│   │   ├── paper_with_links.csv     # 572 reviews with links
│   │   ├── all_paper_titles.txt     # Numbered title list
│   │   ├── clean_titles_for_search.txt
│   │   └── reviews_from_208_titles.txt
│   └── archive/                     # Historical files
│       ├── old-pdf/                 # Old PDF compilations
│       ├── old-docx/                # Old batch DOCX files
│       └── archive-reviews/         # Legacy individual PDFs
│
├── learning-materials/              # Educational resources (1.7 GB)
│   ├── machine learning/            # 15 ML subcategories
│   ├── math/                        # Mathematical foundations
│   ├── algorithms/                  # Data structures & algorithms
│   ├── programming/                 # Languages & practices
│   ├── interview preparation/       # Career resources
│   └── ... (21 categories total)
│
├── presentations/                   # Research presentations (32 MB)
│   └── 9 PDF presentations
│
├── .repo-tools/                     # Automation framework
│   └── repo_automator/              # Metadata updater
│
├── .git/hooks/pre-commit            # Auto-update git hook 🤖
├── .gitignore                       # Ignore system files
├── METADATA_UPDATE_PROCESS.md       # Automation guide
└── README.md                        # This file
```

---

## For Researchers & Students

### Researchers
- **Literature Reviews**: 569 analyzed papers with critical insights
- **Trend Analysis**: Track AI/ML research evolution (2022-2026)
- **Methodology Examples**: Models for academic analysis
- **Quick Reference**: Searchable metadata for rapid paper discovery

### Students
- **Structured Learning**: 22 categories of educational materials
- **Academic Writing**: Examples of comprehensive paper reviews
- **Interview Prep**: 32+ resources for ML/DS interviews
- **Practical Skills**: Programming, SQL, data engineering tutorials

### Practitioners
- **Implementation Insights**: Practical guidance from research
- **Technology Assessment**: Evaluation of emerging techniques
- **Professional Development**: Presentations and tutorials
- **Quick Lookup**: Find relevant papers by topic instantly

---

## Contributing

### Adding New Reviews

Thanks to the **automated git hook**, adding reviews is simple:

1. Create your review file: `mike-paper-reviews-all/split-hebrew-reviews-md/Review_XXX.md`
2. Include the paper link in the review (ArXiv, DOI, or other sources)
3. Commit the file: `git commit -m "Add Review_XXX: Paper Title"`
4. **Metadata updates automatically!** No manual CSV editing needed.

### Guidelines
- Follow the `Review_NNN.md` naming convention
- Include paper link (ArXiv, DOI, etc.) in the review text
- The git hook will extract title and link automatically
- All metadata files are auto-updated on commit

See [`METADATA_UPDATE_PROCESS.md`](METADATA_UPDATE_PROCESS.md) for detailed documentation on:
- Review formatting standards
- Manual metadata updates (if needed)
- Quality standards
- Repository maintenance

---

## License

<p align="center">
<a href="http://creativecommons.org/publicdomain/zero/1.0/">
<img src="https://licensebuttons.net/p/zero/1.0/88x31.png" alt="CC0">
</a>
</p>

This work is dedicated to the **public domain** under the [CC0 1.0 Universal](http://creativecommons.org/publicdomain/zero/1.0/) license. You are free to use, modify, and distribute this content for any purpose without attribution.

---

<div align="center">

**Built with curiosity and dedication to open science**

[Back to Top](#scientific-resources-hub)

</div>
