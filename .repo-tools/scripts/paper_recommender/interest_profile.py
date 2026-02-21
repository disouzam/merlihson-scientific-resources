"""Build Mike's interest profile from reviewed papers CSV."""

import csv
import hashlib
import json
from pathlib import Path
from typing import Optional

# Path relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "mike-paper-reviews-all" / "reviews_metadata" / "paper_with_links.csv"
CACHE_DIR = Path(__file__).resolve().parent
CACHE_FILE = CACHE_DIR / ".interest_profile_cache.json"


def _csv_hash() -> str:
    """Get hash of CSV file to detect changes."""
    return hashlib.md5(CSV_PATH.read_bytes()).hexdigest()


def _load_cached_profile() -> Optional[str]:
    """Load cached profile if CSV hasn't changed."""
    if not CACHE_FILE.exists():
        return None
    try:
        cache = json.loads(CACHE_FILE.read_text())
        if cache.get("csv_hash") == _csv_hash():
            return cache["profile"]
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _save_cached_profile(profile: str) -> None:
    """Save profile to cache."""
    CACHE_FILE.write_text(json.dumps({
        "csv_hash": _csv_hash(),
        "profile": profile,
    }))


def get_paper_titles() -> list[str]:
    """Read all reviewed paper titles from CSV."""
    titles = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "").strip()
            if title:
                titles.append(title)
    return titles


def build_interest_profile() -> str:
    """Build a concise interest profile string from Mike's reviewed papers.

    Returns a cached version if the CSV hasn't changed.
    """
    cached = _load_cached_profile()
    if cached:
        return cached

    titles = get_paper_titles()

    # Build a static profile summarizing known themes from 580+ papers
    # This is more reliable than LLM-based extraction and avoids extra API costs
    profile = f"""Mike has reviewed {len(titles)} AI/ML papers. His core research interests include:

**Deep Learning Foundations:** Transformers, attention mechanisms, neural architecture design, optimization, generalization theory, double descent, scaling laws, neural network training dynamics.

**Large Language Models (LLMs):** Pre-training, fine-tuning, prompting, in-context learning, chain-of-thought reasoning, instruction tuning, RLHF, alignment, safety, evaluation benchmarks.

**Model Efficiency:** Knowledge distillation, model compression, pruning, quantization, efficient inference, mixture of experts, sparse models.

**Representation Learning:** Contrastive learning, self-supervised learning, embeddings, feature learning, transfer learning, curriculum learning.

**Emerging Architectures:** State-space models (Mamba, S4), KANs (Kolmogorov-Arnold Networks), mixture of experts, retrieval-augmented generation.

**Computer Vision & Multimodal:** Vision transformers, diffusion models, image generation, vision-language models, multimodal learning.

**Interpretability & Analysis:** Mechanistic interpretability, probing, feature visualization, model analysis, loss landscape analysis.

**Reasoning & Planning:** Mathematical reasoning, code generation, tool use, agentic systems, reinforcement learning for reasoning.

Here are some of his recently reviewed paper titles for additional context:
{chr(10).join(f"- {t}" for t in titles[-50:])}"""

    _save_cached_profile(profile)
    return profile
