"""Curated source lists for News Scout.

Picked for general-public framing (TV/print/online portal style), not
researcher/practitioner depth. Cuts: arXiv, HackerNews, TechCrunch,
VentureBeat, Ars Technica, The Information, Bloomberg (paywall).

Each English source has either a dedicated AI feed or a Tech feed that
will be filtered to AI-relevant items downstream.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EnglishSource:
    name: str
    feed_url: str
    is_ai_specific: bool  # True if feed is already AI-only; False if generic tech that needs filtering


# 10 English-language sources for general-public AI news
ENGLISH_SOURCES: List[EnglishSource] = [
    EnglishSource(
        name="Reuters Technology",
        # Reuters' own RSS endpoints break frequently; Google News site-search is stable.
        feed_url="https://news.google.com/rss/search?q=site%3Areuters.com+(AI+OR+%22artificial+intelligence%22)+when%3A2d&hl=en-US&gl=US&ceid=US:en",
        is_ai_specific=True,
    ),
    EnglishSource(
        name="AP Technology",
        # AP's own RSS is unreliable; Google News site-search gives us a stable AI-filtered feed.
        feed_url="https://news.google.com/rss/search?q=site%3Aapnews.com+(AI+OR+%22artificial+intelligence%22)+when%3A2d&hl=en-US&gl=US&ceid=US:en",
        is_ai_specific=True,
    ),
    EnglishSource(
        name="BBC Technology",
        feed_url="https://feeds.bbci.co.uk/news/technology/rss.xml",
        is_ai_specific=False,
    ),
    EnglishSource(
        name="NYT Technology",
        feed_url="https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        is_ai_specific=False,
    ),
    EnglishSource(
        name="The Guardian — AI",
        feed_url="https://www.theguardian.com/technology/artificialintelligenceai/rss",
        is_ai_specific=True,
    ),
    EnglishSource(
        name="The Verge",
        # AI-tag Atom feed has parser glitches; fall back to full feed + AI keyword filter.
        feed_url="https://www.theverge.com/rss/index.xml",
        is_ai_specific=False,
    ),
    EnglishSource(
        name="CNBC Technology",
        feed_url="https://www.cnbc.com/id/19854910/device/rss/rss.html",
        is_ai_specific=False,
    ),
    EnglishSource(
        name="Wired — AI",
        feed_url="https://www.wired.com/feed/tag/ai/latest/rss",
        is_ai_specific=True,
    ),
    EnglishSource(
        name="Axios — AI",
        # Axios has no clean AI-only RSS; Google News site-search keeps it stable.
        feed_url="https://news.google.com/rss/search?q=site%3Aaxios.com+(AI+OR+%22artificial+intelligence%22)+when%3A2d&hl=en-US&gl=US&ceid=US:en",
        is_ai_specific=True,
    ),
    EnglishSource(
        name="MIT Technology Review",
        feed_url="https://www.technologyreview.com/feed/",
        is_ai_specific=False,
    ),
    # --- Buzzier sources for sharper, more newsroom-friendly stories ---
    # Wires and legacy press skew toward measured/policy. These add drama,
    # founder fights, exposés, and "what tech people are actually arguing about".
    EnglishSource(
        name="TechCrunch — AI",
        feed_url="https://techcrunch.com/category/artificial-intelligence/feed/",
        is_ai_specific=True,
    ),
    EnglishSource(
        name="Platformer",
        feed_url="https://www.platformer.news/feed",
        is_ai_specific=False,
    ),
    EnglishSource(
        name="Hacker News front page",
        # front page items with at least 50 points (signal of community attention; AI filter trims to AI)
        feed_url="https://hnrss.org/frontpage?points=50",
        is_ai_specific=False,
    ),
    EnglishSource(
        name="Stratechery",
        feed_url="https://stratechery.com/feed/",
        is_ai_specific=False,
    ),
    EnglishSource(
        name="Ars Technica — AI",
        feed_url="https://arstechnica.com/tag/artificial-intelligence/feed/",
        is_ai_specific=True,
    ),
]


# 10 Israeli sites used for coverage check (Claude searches them in Hebrew via web_search).
# Order matters less than coverage breadth: portals + dailies + business + tech press.
ISRAELI_SITE_DOMAINS: List[str] = [
    "ynet.co.il",
    "n12.co.il",
    "mako.co.il",
    "walla.co.il",
    "israelhayom.co.il",
    "maariv.co.il",
    "haaretz.co.il",
    "themarker.com",
    "calcalist.co.il",
    "globes.co.il",
    "geektime.co.il",
]
# Note: 11 domains because N12 and Mako are the same outlet on two domains — counted as one slot.


# Pre-filter: any of these tokens in the title/summary marks an item as AI-related.
# Used to quickly drop non-AI tech stories from generic feeds (BBC, NYT, Reuters, CNBC).
# Conservative — Claude does a second-pass AI-relevance check after this.
AI_KEYWORDS: List[str] = [
    "AI",
    "A.I.",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network",
    "generative",
    "LLM",
    "large language model",
    "chatbot",
    "ChatGPT",
    "GPT-",
    "OpenAI",
    "Anthropic",
    "Claude",
    "Gemini",
    "Llama",
    "Mistral",
    "DeepSeek",
    "xAI",
    "Grok",
    "Copilot",
    "Sora",
    "Midjourney",
    "Stable Diffusion",
    "DALL-E",
    "Perplexity",
    "robotaxi",
    "self-driving",
    "autonomous vehicle",
    "humanoid robot",
    "deepfake",
    "AGI",
    "frontier model",
    "NVIDIA",
    "Hugging Face",
]
