<div align="center">

<img src="./images/cosmic-neural-header.svg" alt="Scientific Resources Hub" width="100%">

<br>

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)
[![Last Updated](https://img.shields.io/badge/Updated-January_2026-success.svg)](#)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](METADATA_UPDATE_PROCESS.md)

**Your one-stop knowledge base for AI/ML research, learning, and reference**

[Explore Reviews](#-paper-reviews) • [Learning Materials](#-learning-materials) • [Presentations](#-presentations) • [Quick Start](#-quick-start)

</div>

---

## Highlights

<table>
<tr>
<td align="center" width="25%">
<h3>📄 569+</h3>
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

- [Overview](#-overview)
- [Quick Start](#-quick-start)
- [Paper Reviews](#-paper-reviews)
- [Learning Materials](#-learning-materials)
- [Presentations](#-presentations)
- [Metadata & Search](#-metadata--search)
- [Python Tools](#-python-tools)
- [Collection Statistics](#-collection-statistics)
- [Repository Structure](#-repository-structure)
- [For Researchers & Students](#-for-researchers--students)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

This repository is a **curated knowledge base** for AI/ML researchers, students, and practitioners. It contains:

- **569 comprehensive paper reviews** covering cutting-edge AI/ML research (2022-2026)
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
| Individual review files | `mike-paper-reviews-all/split-reviews-docx/Review_001.docx` - `Review_569.docx` |
| All paper titles | `mike-paper-reviews-all/reviews_metadata/all_paper_titles.txt` |
| Papers with ArXiv links | `mike-paper-reviews-all/reviews_metadata/paper_with_links.csv` |
| Merged PDF (447 pages) | `mike-paper-reviews-all/pdf/all_reviews_until_30_11_24.pdf` |

---

## Paper Reviews

### `mike-paper-reviews-all/`

The core collection containing **569 individual paper reviews** in multiple formats.

| Type | Count | Description |
|------|-------|-------------|
| **Individual Reviews** | 1-208 | Deep-dive analyses with enhanced ArXiv links |
| **Daily Reviews** | 209-569 | Chronological reviews (May 2024 - Jan 2026) |

#### Formats Available
- **`split-reviews-docx/`** - 569 individual DOCX files (`Review_001.docx` → `Review_569.docx`)
- **`pdf/`** - PDF collections including merged 447-page compilation
- **`docx/`** - Original batch source documents

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

## Python Tools

### `mike-paper-reviews-all/py_code/`

Automation tools for document processing:

#### `docx_splitter.py`
A CLI tool for splitting batch DOCX files into individual reviews.

```bash
# Split a single batch file
python docx_splitter.py Reviews_1-30.docx --output ./split-reviews-docx/

# Process all batch files
python docx_splitter.py --all --output ./split-reviews-docx/
```

**Features:**
- Detects review boundaries using regex patterns
- Handles duplicate review numbers with suffix naming
- Preserves formatting and styles
- 100% extraction success rate

**Dependencies:** `python-docx`, `lxml`, `Pillow`

```bash
pip install -r mike-paper-reviews-all/py_code/requirements.txt
```

---

## Collection Statistics

| Metric | Value |
|--------|-------|
| **Total Paper Reviews** | 569 |
| **Individual Reviews** | 208 (with ArXiv links) |
| **Daily Reviews** | 361 (May 2024 - Jan 2026) |
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
├── mike-paper-reviews-all/          # Main review collection (311 MB)
│   ├── split-reviews-docx/          # 569 individual DOCX reviews
│   │   ├── Review_001.docx
│   │   ├── Review_002.docx
│   │   └── ... → Review_569.docx
│   ├── pdf/                         # PDF format reviews
│   │   └── all_reviews_until_30_11_24.pdf  # Merged (447 pages)
│   ├── docx/                        # Original batch documents
│   ├── reviews_metadata/            # Searchable indices
│   │   ├── all_paper_titles.txt
│   │   ├── paper_with_links.csv
│   │   └── clean_titles_for_search.txt
│   └── py_code/                     # Python automation tools
│       ├── docx_splitter.py
│       └── requirements.txt
│
├── learning-materials/              # Educational resources (1.7 GB)
│   ├── machine learning/            # 15 ML subcategories
│   ├── math/                        # Mathematical foundations
│   ├── algorithms/                  # Data structures & algorithms
│   ├── programming/                 # Languages & practices
│   ├── interview preparation/       # Career resources
│   └── ... (22 categories total)
│
├── presentations/                   # Research presentations (32 MB)
│   └── 9 PDF presentations
│
├── archive-reviews/           # Legacy archive (31 MB)
│
├── METADATA_UPDATE_PROCESS.md       # Maintenance guide
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

See [`METADATA_UPDATE_PROCESS.md`](METADATA_UPDATE_PROCESS.md) for the comprehensive guide on:
- Adding new reviews
- Updating metadata indices
- Maintaining consistency
- Quality standards

### Quick Guidelines
- Follow the `Review_NNN.docx` naming convention
- Update `all_paper_titles.txt` when adding reviews
- Maintain searchable CSV mappings
- Preserve formatting standards

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
