"""Fetch recent papers from arXiv API."""

import arxiv
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List


@dataclass
class ArxivPaper:
    title: str
    abstract: str
    authors: List[str]
    link: str
    categories: List[str]
    published: datetime


def fetch_recent_papers(categories: List[str], days_back: int = 1) -> List[ArxivPaper]:
    """Fetch papers from arXiv published in the last `days_back` days.

    Uses the arXiv API to query multiple categories and deduplicates by paper ID.
    """
    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
    seen_ids = set()
    papers = []

    # Build OR query for all categories
    category_query = " OR ".join(f"cat:{cat}" for cat in categories)

    client = arxiv.Client()
    search = arxiv.Search(
        query=category_query,
        max_results=500,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    for result in client.results(search):
        # Stop if we've gone past our cutoff date
        published = result.published.astimezone()
        if published < cutoff:
            break

        paper_id = result.entry_id
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        # Get first 3 authors for display
        author_names = [a.name for a in result.authors[:3]]
        if len(result.authors) > 3:
            author_names.append("et al.")

        papers.append(ArxivPaper(
            title=result.title.replace("\n", " ").strip(),
            abstract=result.summary.replace("\n", " ").strip(),
            authors=author_names,
            link=result.entry_id,
            categories=[c for c in result.categories if c in categories],
            published=published,
        ))

    return papers
