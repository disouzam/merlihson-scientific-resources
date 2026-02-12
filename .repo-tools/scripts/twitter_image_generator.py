#!/usr/bin/env python3
"""
Twitter Image Generator

Generates engaging images for Twitter threads:
- Title cards (first tweet)
- Key insight cards
- Quote cards
- Paper summary cards

Uses PIL (Pillow) for image generation.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Optional, Tuple
import textwrap


class TwitterImageGenerator:
    """Generate images for Twitter threads."""

    # Twitter image specs
    WIDTH = 1200
    HEIGHT = 675  # 16:9 ratio (recommended for Twitter)

    # Colors (modern tech style)
    BG_COLOR = (15, 23, 42)  # Dark blue
    TEXT_COLOR = (248, 250, 252)  # Off-white
    ACCENT_COLOR = (96, 165, 250)  # Light blue
    SECONDARY_COLOR = (156, 163, 175)  # Gray

    def __init__(self, output_dir: Path):
        """Initialize generator with output directory."""
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Try to load fonts, fallback to default
        self.title_font = self._load_font(size=80, bold=True)
        self.subtitle_font = self._load_font(size=50, bold=False)
        self.body_font = self._load_font(size=40, bold=False)
        self.small_font = self._load_font(size=30, bold=False)

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Load font, fallback to default if not found."""
        try:
            # Try to use system fonts
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFNSDisplay.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]

            for font_path in font_paths:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)

            # Fallback to default
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()

    def create_title_card(self, title: str, subtitle: str, review_num: int) -> Path:
        """
        Create title card for first tweet.

        Args:
            title: Paper title (English)
            subtitle: Hebrew title
            review_num: Review number

        Returns:
            Path to generated image
        """
        # Create image
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Add decorative top bar
        draw.rectangle([(0, 0), (self.WIDTH, 20)], fill=self.ACCENT_COLOR)

        # Add review number badge
        badge_text = f"Review #{review_num}"
        draw.rectangle([(40, 60), (300, 140)], fill=self.ACCENT_COLOR, outline=self.ACCENT_COLOR)
        draw.text((170, 100), badge_text, fill=self.BG_COLOR, font=self.small_font, anchor="mm")

        # Wrap and draw title
        y_offset = 200
        wrapped_title = textwrap.wrap(title, width=40)
        for line in wrapped_title[:3]:  # Max 3 lines
            draw.text((self.WIDTH // 2, y_offset), line, fill=self.TEXT_COLOR,
                     font=self.title_font, anchor="mm")
            y_offset += 90

        # Draw subtitle (Hebrew)
        y_offset += 50
        wrapped_subtitle = textwrap.wrap(subtitle, width=50)
        for line in wrapped_subtitle[:2]:  # Max 2 lines
            draw.text((self.WIDTH // 2, y_offset), line, fill=self.SECONDARY_COLOR,
                     font=self.subtitle_font, anchor="mm")
            y_offset += 60

        # Add bottom badge
        draw.text((self.WIDTH // 2, self.HEIGHT - 60), "🧵 Hebrew Review Thread",
                 fill=self.ACCENT_COLOR, font=self.body_font, anchor="mm")

        # Save image
        output_path = self.output_dir / f"review_{review_num}_title.png"
        img.save(output_path)

        return output_path

    def create_insight_card(self, insight: str, review_num: int, card_num: int) -> Path:
        """
        Create key insight card.

        Args:
            insight: Key insight text
            review_num: Review number
            card_num: Card number (for unique filename)

        Returns:
            Path to generated image
        """
        # Create image
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Add decorative elements
        draw.rectangle([(40, 40), (self.WIDTH - 40, 80)], fill=self.ACCENT_COLOR)

        # Add "Key Insight" label
        draw.text((self.WIDTH // 2, 110), "💡 תובנה מרכזית",
                 fill=self.ACCENT_COLOR, font=self.subtitle_font, anchor="mm")

        # Wrap and draw insight
        y_offset = 220
        wrapped_insight = textwrap.wrap(insight, width=35)
        for line in wrapped_insight[:8]:  # Max 8 lines
            draw.text((self.WIDTH // 2, y_offset), line, fill=self.TEXT_COLOR,
                     font=self.body_font, anchor="mm")
            y_offset += 55

        # Add review number at bottom
        draw.text((self.WIDTH // 2, self.HEIGHT - 60), f"Review #{review_num}",
                 fill=self.SECONDARY_COLOR, font=self.small_font, anchor="mm")

        # Save image
        output_path = self.output_dir / f"review_{review_num}_insight_{card_num}.png"
        img.save(output_path)

        return output_path

    def create_paper_link_card(self, arxiv_link: str, review_num: int) -> Path:
        """
        Create paper link card for last tweet.

        Args:
            arxiv_link: ArXiv URL
            review_num: Review number

        Returns:
            Path to generated image
        """
        # Create image
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Add decorative background pattern
        for i in range(0, self.WIDTH, 100):
            draw.line([(i, 0), (i + 200, self.HEIGHT)], fill=(30, 41, 59), width=2)

        # Main message
        draw.text((self.WIDTH // 2, 200), "📄 קרא את המאמר המלא",
                 fill=self.ACCENT_COLOR, font=self.title_font, anchor="mm")

        # ArXiv link
        draw.text((self.WIDTH // 2, 320), arxiv_link,
                 fill=self.TEXT_COLOR, font=self.body_font, anchor="mm")

        # QR code placeholder (we can add actual QR later)
        draw.rectangle([(self.WIDTH // 2 - 100, 400), (self.WIDTH // 2 + 100, 600)],
                      fill=self.TEXT_COLOR, outline=self.ACCENT_COLOR, width=5)
        draw.text((self.WIDTH // 2, 500), "QR", fill=self.BG_COLOR,
                 font=self.title_font, anchor="mm")

        # Save image
        output_path = self.output_dir / f"review_{review_num}_paper_link.png"
        img.save(output_path)

        return output_path


def test_generator():
    """Test image generation."""
    from pathlib import Path

    output_dir = Path("/tmp/twitter_images")
    generator = TwitterImageGenerator(output_dir)

    # Test title card
    title = "A MODEL OF ERRORS IN TRANSFORMERS"
    subtitle = "התרמודינמיקה של שגיאות טרנספורמר"
    title_path = generator.create_title_card(title, subtitle, 577)
    print(f"✓ Title card: {title_path}")

    # Test insight card
    insight = "המחברים מציעים תורת שדות אפקטיבית שבה מרחב הפרמטרים העצום מצטמצם לשני משתנים בלבד"
    insight_path = generator.create_insight_card(insight, 577, 1)
    print(f"✓ Insight card: {insight_path}")

    # Test paper link card
    arxiv_link = "https://arxiv.org/abs/2601.14175"
    link_path = generator.create_paper_link_card(arxiv_link, 577)
    print(f"✓ Paper link card: {link_path}")


if __name__ == "__main__":
    test_generator()
