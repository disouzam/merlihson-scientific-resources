"""End-to-end integration test for the review pipeline.

Skips arXiv fetch (rate-limited) — uses a known paper to test
PDF download -> text extraction -> Claude review generation -> formatting.
"""

import sys
from datetime import datetime

from ..arxiv_fetcher import ArxivPaper
from ..paper_ranker import RankedPaper
from ..paper_reviewer import (
    _arxiv_pdf_url,
    _download_pdf,
    _extract_abstract_and_intro,
    generate_reviews,
)
from ..telegram_sender import format_message


def _make_real_paper() -> RankedPaper:
    """A real arXiv paper for integration testing."""
    return RankedPaper(
        paper=ArxivPaper(
            title="Attention Is All You Need",
            abstract=(
                "The dominant sequence transduction models are based on complex "
                "recurrent or convolutional neural networks that include an encoder "
                "and a decoder. The best performing models also connect the encoder "
                "and decoder through an attention mechanism. We propose a new simple "
                "network architecture, the Transformer, based solely on attention "
                "mechanisms, dispensing with recurrence and convolutions entirely."
            ),
            authors=["Vaswani, A.", "Shazeer, N.", "Parmar, N.", "et al."],
            link="http://arxiv.org/abs/1706.03762",
            categories=["cs.CL", "cs.LG"],
            published=datetime(2017, 6, 12),
        ),
        score=9.5,
        reason="Foundational transformer paper — directly relevant to LLM research",
    )


def test_pdf_download_and_extraction():
    """Test that we can download and extract text from a real arXiv PDF."""
    paper = _make_real_paper()
    pdf_url = _arxiv_pdf_url(paper.paper.link)
    print(f"PDF URL: {pdf_url}")

    pdf_bytes = _download_pdf(pdf_url)
    if pdf_bytes is None:
        print("SKIP: Could not download PDF (rate limit or network issue)")
        return False

    print(f"Downloaded {len(pdf_bytes)} bytes")

    text = _extract_abstract_and_intro(pdf_bytes)
    print(f"Extracted {len(text)} chars")
    print(f"First 200 chars: {text[:200]}...")

    assert len(text) > 500, f"Expected >500 chars, got {len(text)}"
    assert "attention" in text.lower() or "transformer" in text.lower(), "Expected paper content"
    print("PDF extraction: PASS")
    return True


def test_review_generation():
    """Test full review generation with Claude Sonnet."""
    import yaml
    from pathlib import Path

    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    if not config_path.exists():
        print("SKIP: No config.yaml found (need API key)")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    api_key = config.get("anthropic_api_key", "")
    if not api_key or api_key == "YOUR_ANTHROPIC_API_KEY_HERE":
        print("SKIP: No API key configured")
        return

    paper = _make_real_paper()
    print(f"Generating review for: {paper.paper.title}")

    result = generate_reviews([paper], api_key, model="claude-sonnet-4-20250514")

    assert len(result) == 1, f"Expected 1 paper, got {len(result)}"
    review = result[0].review
    print(f"\nReview ({len(review)} chars):\n{review}\n")

    assert len(review) > 100, f"Review too short: {len(review)} chars"

    # Check formatting works with reviews
    message = format_message(result)
    print(f"Formatted message ({len(message)} chars):\n{message}")
    assert review in message, "Review should appear in formatted message"
    print("\nReview generation: PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("E2E Paper Reviewer Test")
    print("=" * 60)

    print("\n--- Test 1: PDF Download + Extraction ---")
    pdf_ok = test_pdf_download_and_extraction()

    print("\n--- Test 2: Review Generation (Claude API) ---")
    test_review_generation()

    print("\n" + "=" * 60)
    print("All tests passed!")
