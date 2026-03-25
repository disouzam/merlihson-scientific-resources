"""Tests for paper_reviewer module."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from ..arxiv_fetcher import ArxivPaper
from ..paper_ranker import RankedPaper
from ..paper_reviewer import (
    _arxiv_pdf_url,
    _extract_abstract_and_intro,
    _parse_reviews,
    generate_reviews,
)


def _make_paper(idx: int = 0) -> RankedPaper:
    return RankedPaper(
        paper=ArxivPaper(
            title=f"Test Paper {idx}",
            abstract=f"This is the abstract for paper {idx}. It covers important topics.",
            authors=["Author A", "Author B"],
            link=f"http://arxiv.org/abs/2401.{idx:05d}",
            categories=["cs.LG"],
            published=datetime(2024, 1, 15),
        ),
        score=8.0 - idx,
        reason=f"Relevant because of reason {idx}",
    )


class TestArxivPdfUrl(unittest.TestCase):
    def test_converts_abs_to_pdf(self):
        url = "http://arxiv.org/abs/2401.12345"
        self.assertEqual(_arxiv_pdf_url(url), "http://arxiv.org/pdf/2401.12345")

    def test_strips_version(self):
        url = "http://arxiv.org/abs/2401.12345v2"
        self.assertEqual(_arxiv_pdf_url(url), "http://arxiv.org/pdf/2401.12345")


class TestParseReviews(unittest.TestCase):
    def test_parses_well_formatted_response(self):
        response = (
            "PAPER 0:\n"
            "Line one about the problem.\n"
            "Line two about the approach.\n"
            "Line three about novelty.\n"
            "Line four about results.\n"
            "Line five about limitations.\n"
            "Line six about audience.\n"
            "\n"
            "PAPER 1:\n"
            "Second paper line one.\n"
            "Second paper line two.\n"
            "Second paper line three.\n"
            "Second paper line four.\n"
            "Second paper line five.\n"
            "Second paper line six.\n"
        )
        reviews = _parse_reviews(response, 2)
        self.assertEqual(len(reviews), 2)
        self.assertIn("Line one about the problem", reviews[0])
        self.assertIn("Second paper line one", reviews[1])

    def test_handles_missing_paper(self):
        response = "PAPER 0:\nSome review.\n\nPAPER 2:\nAnother review.\n"
        reviews = _parse_reviews(response, 3)
        self.assertEqual(len(reviews), 3)
        self.assertIn("Some review", reviews[0])
        self.assertEqual(reviews[1], "")
        self.assertIn("Another review", reviews[2])

    def test_handles_empty_response(self):
        reviews = _parse_reviews("", 3)
        self.assertEqual(reviews, ["", "", ""])

    def test_handles_malformed_response(self):
        reviews = _parse_reviews("Just some random text without markers", 2)
        self.assertEqual(reviews, ["", ""])


class TestExtractAbstractAndIntro(unittest.TestCase):
    def test_returns_empty_on_invalid_pdf(self):
        result = _extract_abstract_and_intro(b"not a pdf")
        self.assertEqual(result, "")

    def test_returns_empty_on_empty_bytes(self):
        result = _extract_abstract_and_intro(b"")
        self.assertEqual(result, "")


class TestGenerateReviews(unittest.TestCase):
    @patch("paper_recommender.paper_reviewer._download_pdf")
    @patch("paper_recommender.paper_reviewer.anthropic.Anthropic")
    def test_falls_back_to_abstract_when_pdf_fails(self, mock_anthropic_cls, mock_download):
        mock_download.return_value = None  # PDF download fails
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="PAPER 0:\nReview based on abstract.\nLine 2.\nLine 3.\nLine 4.\nLine 5.\nLine 6.")]
        mock_client.messages.create.return_value = mock_response

        papers = [_make_paper(0)]
        result = generate_reviews(papers, "fake-key")

        self.assertEqual(len(result), 1)
        self.assertIn("Review based on abstract", result[0].review)
        # Verify the abstract was used in the prompt
        call_args = mock_client.messages.create.call_args
        prompt_text = call_args[1]["messages"][0]["content"]
        self.assertIn("This is the abstract for paper 0", prompt_text)

    @patch("paper_recommender.paper_reviewer._get_paper_text")
    @patch("paper_recommender.paper_reviewer.anthropic.Anthropic")
    def test_returns_empty_reviews_on_api_failure(self, mock_anthropic_cls, mock_get_text):
        mock_get_text.return_value = "Some text"
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        papers = [_make_paper(0), _make_paper(1)]
        result = generate_reviews(papers, "fake-key")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].review, "")
        self.assertEqual(result[1].review, "")

    def test_empty_list_returns_empty(self):
        result = generate_reviews([], "fake-key")
        self.assertEqual(result, [])

    @patch("paper_recommender.paper_reviewer._get_paper_text")
    @patch("paper_recommender.paper_reviewer.anthropic.Anthropic")
    def test_multiple_papers_batched(self, mock_anthropic_cls, mock_get_text):
        mock_get_text.return_value = "Some extracted text"
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text="PAPER 0:\nReview zero.\n\nPAPER 1:\nReview one.\n\nPAPER 2:\nReview two."
        )]
        mock_client.messages.create.return_value = mock_response

        papers = [_make_paper(i) for i in range(3)]
        result = generate_reviews(papers, "fake-key")

        # Single API call for all papers
        self.assertEqual(mock_client.messages.create.call_count, 1)
        self.assertEqual(len(result), 3)
        self.assertIn("Review zero", result[0].review)
        self.assertIn("Review one", result[1].review)
        self.assertIn("Review two", result[2].review)


class TestRankedPaperReviewField(unittest.TestCase):
    def test_default_review_is_empty(self):
        rp = _make_paper(0)
        self.assertEqual(rp.review, "")

    def test_review_can_be_set(self):
        rp = _make_paper(0)
        rp.review = "A great paper review."
        self.assertEqual(rp.review, "A great paper review.")


if __name__ == "__main__":
    unittest.main()
