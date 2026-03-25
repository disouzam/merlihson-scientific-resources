"""Generate 6-sentence reviews for top-ranked papers using Claude Sonnet.

Fetches arXiv PDFs, extracts abstract + introduction, and uses Claude
to produce concise reviews suitable for a Telegram daily digest.
"""

import io
import re
import time
from typing import List, Optional

import anthropic
import fitz  # PyMuPDF
import requests

from .paper_ranker import RankedPaper

# Max chars to extract from PDF (abstract + intro ≈ 2 pages)
MAX_EXTRACT_CHARS = 6000
# Retry settings for arXiv PDF downloads
MAX_RETRIES = 2
RETRY_DELAY = 3


def _arxiv_pdf_url(entry_url: str) -> str:
    """Convert arXiv entry URL to PDF URL."""
    url = entry_url.replace("/abs/", "/pdf/")
    # Strip version suffix like v1, v2 (e.g., 2401.12345v2 -> 2401.12345)
    return re.sub(r"v\d+$", "", url)


def _download_pdf(url: str) -> Optional[bytes]:
    """Download PDF bytes from URL with retries."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/pdf"):
                return resp.content
            if resp.status_code == 429 and attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
        except requests.RequestException:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
        break
    return None


def _extract_abstract_and_intro(pdf_bytes: bytes) -> str:
    """Extract text from first ~2 pages of a PDF (abstract + introduction)."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        # Extract up to 3 pages to ensure we capture the full intro
        for page_num in range(min(3, len(doc))):
            text += doc[page_num].get_text()
            if len(text) >= MAX_EXTRACT_CHARS:
                break
        doc.close()
        # Trim to max chars at a sentence boundary
        if len(text) > MAX_EXTRACT_CHARS:
            cut = text[:MAX_EXTRACT_CHARS].rfind(". ")
            if cut > MAX_EXTRACT_CHARS // 2:
                text = text[: cut + 1]
            else:
                text = text[:MAX_EXTRACT_CHARS]
        return text.strip()
    except Exception:
        return ""


def _get_paper_text(ranked_paper: RankedPaper) -> str:
    """Get abstract+intro from PDF, falling back to abstract only."""
    pdf_url = _arxiv_pdf_url(ranked_paper.paper.link)
    pdf_bytes = _download_pdf(pdf_url)
    if pdf_bytes:
        extracted = _extract_abstract_and_intro(pdf_bytes)
        if extracted:
            return extracted
    # Fallback: use abstract from ArxivPaper
    return ranked_paper.paper.abstract


def generate_reviews(
    ranked_papers: List[RankedPaper],
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> List[RankedPaper]:
    """Add a 6-sentence review to each ranked paper.

    Downloads PDFs in sequence (respects arXiv rate limits),
    then batches all papers into a single Claude call for efficiency.
    """
    if not ranked_papers:
        return ranked_papers

    # Fetch paper texts (abstract + intro)
    paper_texts = []
    for rp in ranked_papers:
        text = _get_paper_text(rp)
        paper_texts.append(text)
        # Small delay between PDF downloads to be polite to arXiv
        time.sleep(0.5)

    # Build prompt for batch review generation
    client = anthropic.Anthropic(api_key=api_key)
    reviews = _generate_review_batch(client, model, ranked_papers, paper_texts)

    # Attach reviews to papers
    for rp, review in zip(ranked_papers, reviews):
        rp.review = review

    return ranked_papers


def _generate_review_batch(
    client: anthropic.Anthropic,
    model: str,
    ranked_papers: List[RankedPaper],
    paper_texts: List[str],
) -> List[str]:
    """Generate reviews for all papers in a single API call."""
    papers_block = ""
    for idx, (rp, text) in enumerate(zip(ranked_papers, paper_texts)):
        papers_block += (
            f"\n--- PAPER {idx} ---\n"
            f"Title: {rp.paper.title}\n"
            f"Authors: {', '.join(rp.paper.authors)}\n"
            f"Text (abstract + introduction):\n{text}\n"
        )

    prompt = f"""You are a senior AI/ML researcher writing concise paper reviews for a daily digest.

For each paper below, write exactly 6 sentences:
1. What problem the paper addresses and why it matters
2. The key idea or approach proposed
3. The main technical contribution or novelty
4. The most important experimental result or finding
5. A limitation, open question, or caveat
6. Who would benefit most from reading this paper

Rules:
- Be specific — reference actual methods, numbers, and findings from the text
- Be direct and opinionated — this is for a knowledgeable ML researcher
- Do NOT use filler phrases like "This paper presents" or "The authors propose"
- Each sentence should be self-contained and informative
- If the text only contains an abstract (no introduction), still write 6 sentences but note uncertainty where needed

{papers_block}

Output format — for each paper output:
PAPER <index>:
<6 sentences, one per line>

Output ONLY the reviews, no extra commentary."""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_reviews(response.content[0].text, len(ranked_papers))
    except Exception as e:
        print(f"Warning: Review generation failed ({e}). Proceeding without reviews.")
        return [""] * len(ranked_papers)


def _parse_reviews(response_text: str, expected_count: int) -> List[str]:
    """Parse the Claude response into individual review strings."""
    reviews = [""] * expected_count

    # Split by "PAPER N:" markers
    parts = re.split(r"PAPER\s+(\d+)\s*:", response_text)
    # parts[0] is text before first marker (empty/whitespace)
    # parts[1] = index, parts[2] = review text, parts[3] = index, ...
    for i in range(1, len(parts) - 1, 2):
        try:
            idx = int(parts[i])
            review_text = parts[i + 1].strip()
            if 0 <= idx < expected_count:
                reviews[idx] = review_text
        except (ValueError, IndexError):
            continue

    return reviews
