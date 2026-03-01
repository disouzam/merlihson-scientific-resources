#!/usr/bin/env python3
"""
Twitter Thread Builder

Builds Twitter threads from Hebrew reviews (400 chars per tweet).
Paper link appears only in first and last tweets.
Can post to Telegram for manual Twitter posting.

Usage:
  python3 twitter_thread_builder.py --review 577 --output thread.txt
  python3 twitter_thread_builder.py --review 577 --telegram
  python3 twitter_thread_builder.py --review 577 --print
"""

import sys
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Repository paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HEBREW_MD_DIR = REPO_ROOT / "mike-paper-reviews-all" / "split-hebrew-reviews-md"


def load_hebrew_review(review_num: int) -> Optional[str]:
    """Load Hebrew review markdown file."""
    review_file = HEBREW_MD_DIR / f"Review_{review_num:03d}.md"

    if not review_file.exists():
        print(f"❌ Error: Review file not found: {review_file}")
        return None

    try:
        with open(review_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"❌ Error reading review file: {e}")
        return None


def clean_markdown(content: str) -> str:
    """Remove markdown formatting, keep clean text."""
    # Remove markdown headers (###, ##, #)
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

    # Remove bold (**text**)
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)

    # Remove italic (*text*)
    content = re.sub(r'\*(.+?)\*', r'\1', content)

    # Remove links [text](url) - keep text only
    content = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', content)

    return content.strip()


def extract_title(content: str) -> str:
    """Extract review title (first non-empty line)."""
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            return line
    return "Paper Review"


def extract_paper_name(content: str) -> str:
    """Extract the English paper name from the review header line.

    Typical format: 'סקירת המאמר היומית של מייק: DD.MM.YY, סקירה NNN, NNN סקירות ל-1024 PAPER TITLE'
    The English paper name is the all-caps (or mixed-case) tail after the last number sequence.
    """
    lines = content.strip().split('\n')
    for line in lines:
        if 'סקירה' not in line or 'סקירת' not in line:
            continue
        # Match: after 'ל-1024' or similar, grab the English paper name at the end
        match = re.search(r'ל-\d+\s+(.+)', line)
        if match:
            name = match.group(1).strip()
            if name and any(c.isascii() and c.isalpha() for c in name):
                return name
        # Fallback: grab the last uppercase English segment
        match = re.search(r'([A-Z][A-Z\s\-\(\):,]+[A-Z\)])\s*$', line)
        if match:
            return match.group(1).strip()
    return ""


def extract_key_concepts(content: str, max_concepts: int = 3) -> List[str]:
    """Extract key technical concepts from the review body for the intro tweet.

    Looks for meaningful English technical terms: CamelCase words, terms in
    parentheses that look like definitions, and capitalized noun phrases.
    Skips the title/header lines to avoid picking up fragments.
    """
    # Work on review body only (skip first 2 lines which are title + header)
    lines = content.strip().split('\n')
    body = '\n'.join(lines[2:]) if len(lines) > 2 else content

    concepts = []
    seen = set()

    # 1. CamelCase terms (TokenRank, PageRank, etc.)
    camel_terms = re.findall(r'\b([A-Z][a-z]+[A-Z][a-zA-Z]*)\b', body)
    for term in camel_terms:
        if term.lower() not in seen:
            seen.add(term.lower())
            concepts.append(term)
            if len(concepts) >= max_concepts:
                return concepts

    # 2. English terms in parentheses that look like definitions
    paren_terms = re.findall(r'\(([A-Za-z][A-Za-z\s\-]{4,}?)\)', body)
    for term in paren_terms:
        term = term.strip()
        if re.match(r'^(as|the|a|an|or|and|i\.e|e\.g|aka|כמו|כלומר)\b', term, re.IGNORECASE):
            continue
        if term.lower() not in seen and len(term.split()) <= 5:
            seen.add(term.lower())
            concepts.append(term)
            if len(concepts) >= max_concepts:
                return concepts

    # 3. Standalone capitalized English phrases in the body (2-4 words)
    cap_phrases = re.findall(r'(?<!\()\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b(?!\))', body)
    for term in cap_phrases:
        term = term.strip()
        if term.lower() not in seen:
            seen.add(term.lower())
            concepts.append(term)
            if len(concepts) >= max_concepts:
                return concepts

    return concepts


def extract_arxiv_link(content: str) -> Optional[str]:
    """Extract ArXiv link from review."""
    # Look for arxiv.org URLs
    match = re.search(r'https?://arxiv\.org/[^\s]+', content)
    if match:
        return match.group(0)
    return None


def split_into_tweets(text: str, max_chars: int = 380) -> List[str]:
    """
    Split text into tweet-sized chunks intelligently.

    Args:
        text: Text to split
        max_chars: Max characters per tweet (default 380 to reserve ~20 for numbering/emoji)

    Returns:
        List of tweet texts
    """
    # First, collect all atomic pieces (sentences)
    paragraphs = text.split('\n\n')
    pieces = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        sentences = split_by_sentences(para)
        for sent in sentences:
            sent = sent.strip()
            if sent:
                pieces.append(sent)
        pieces.append('\n\n')  # paragraph break marker

    # Remove trailing paragraph break
    while pieces and pieces[-1] == '\n\n':
        pieces.pop()

    # Greedily pack sentences into tweets
    tweets = []
    current_tweet = ""

    for piece in pieces:
        if piece == '\n\n':
            # Paragraph break - try to keep as separator
            continue

        # Determine separator
        sep = " " if current_tweet else ""

        if len(current_tweet) + len(sep) + len(piece) <= max_chars:
            current_tweet += sep + piece
        else:
            # Save current tweet
            if current_tweet:
                tweets.append(current_tweet)

            # If single sentence is too long, split by words
            if len(piece) > max_chars:
                words = piece.split()
                current_tweet = ""
                for word in words:
                    wsep = " " if current_tweet else ""
                    if len(current_tweet) + len(wsep) + len(word) <= max_chars:
                        current_tweet += wsep + word
                    else:
                        if current_tweet:
                            tweets.append(current_tweet)
                        current_tweet = word
            else:
                current_tweet = piece

    if current_tweet:
        tweets.append(current_tweet)

    return tweets


def split_by_sentences(text: str) -> List[str]:
    """Split text by sentences (period, question mark, exclamation)."""
    # Split by sentence endings
    sentences = re.split(r'([.!?]+)', text)

    result = []
    current = ""

    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        punctuation = sentences[i+1] if i+1 < len(sentences) else ""

        full_sentence = (sentence + punctuation).strip()
        if full_sentence:
            result.append(full_sentence)

    return result


def build_thread(content: str, review_num: int, clickbait: bool = True) -> List[str]:
    """
    Build complete Twitter thread from review content.

    Args:
        content: Review content
        review_num: Review number
        clickbait: If True, use engaging/clickbait style

    Returns:
        List of tweets with numbering
    """
    # Clean markdown
    clean_content = clean_markdown(content)

    # Extract components
    title = extract_title(content)
    arxiv_link = extract_arxiv_link(content)

    # Remove title from content (already in first tweet)
    lines = clean_content.split('\n')
    content_without_title = '\n'.join(lines[1:]).strip()

    # Strip URLs from content (paper link only in first/last tweet)
    content_without_title = re.sub(r'https?://\S+', '', content_without_title)
    content_without_title = re.sub(r'\n{3,}', '\n\n', content_without_title).strip()

    # Split content into tweets (380 chars to leave room for numbering/emoji prefix)
    content_tweets = split_into_tweets(content_without_title, max_chars=380)

    # Build thread
    thread = []

    if clickbait:
        # CLICKBAIT VERSION - Content-aware hooks
        paper_name = extract_paper_name(content)
        hook_emojis = ["🔥", "🧠", "⚡", "🎯", "💡", "🚀"]
        hook_emoji = hook_emojis[review_num % len(hook_emojis)]

        total = len(content_tweets) + 3

        # Build hook from actual paper title + paper link
        link_line = f"\n\n📄 {arxiv_link}" if arxiv_link else ""
        if paper_name:
            first_tweet = f"(1/{total}) {hook_emoji} {paper_name} 🧵\n\n📄 {title}\n\n🇮🇱 Full Hebrew review below ⬇️{link_line}\n\n#AI #MachineLearning"
        else:
            first_tweet = f"(1/{total}) {hook_emoji} {title} 🧵\n\n🇮🇱 Full Hebrew review below ⬇️{link_line}\n\n#AI #MachineLearning"
        thread.append(first_tweet)

        # Build intro from actual review concepts
        concepts = extract_key_concepts(content)
        intro_lines = [f"(2/{total}) סקירה {review_num} - למה הפוסט הזה חשוב? 🤔\n"]
        for concept in concepts:
            intro_lines.append(f"➡️ {concept}")
        if not concepts:
            intro_lines.append(f"➡️ {title}")
        intro_lines.append(f"\nבואו נצלול פנימה 🏊‍♂️")
        intro_tweet = "\n".join(intro_lines)
        thread.append(intro_tweet)

        # Content tweets with emojis
        emoji_map = {
            'הסטייה': '📊',
            'שגיאה': '⚠️',
            'מודל': '🤖',
            'אידיאלי': '✨',
            'אפקטיבי': '⚙️',
            'attention': '👁️',
            'טרנספורמר': '🔄',
            'רעש': '📉',
            'דיוק': '🎯',
            'סף': '🚧',
        }

        for i, tweet_text in enumerate(content_tweets, start=3):
            # Add contextual emoji based on content
            emoji = "📌"
            for keyword, emoji_char in emoji_map.items():
                if keyword in tweet_text:
                    emoji = emoji_char
                    break

            numbered_tweet = f"({i}/{total}) {emoji} {tweet_text}"
            thread.append(numbered_tweet)

        # Last tweet: Strong CTA + link
        last_tweet = f"({total}/{total}) 🎓 רוצים לקרוא את המחקר המלא?\n\n"
        if arxiv_link:
            last_tweet += f"📄 Paper: {arxiv_link}\n\n"
        last_tweet += f"💬 מה דעתכם? כתבו בתגובות!\n\n🔄 RT אם למדתם משהו חדש\n\n✅ סוף Thread\n\n#AI #MachineLearning #DeepLearning"
        thread.append(last_tweet)

    else:
        # ORIGINAL VERSION - Simple and clean
        total_tweets = len(content_tweets) + 2
        link_line = f"\n\n📄 {arxiv_link}" if arxiv_link else ""
        first_tweet = f"(1/{total_tweets}) {title}\n\n🧵 Full Hebrew review ⬇️{link_line}"
        thread.append(first_tweet)

        for i, tweet_text in enumerate(content_tweets, start=2):
            numbered_tweet = f"({i}/{total_tweets}) {tweet_text}"
            thread.append(numbered_tweet)

        last_tweet = f"({total_tweets}/{total_tweets}) "
        if arxiv_link:
            last_tweet += f"📄 Full paper: {arxiv_link}\n\n"
        last_tweet += f"✅ End of thread\n\n#MachineLearning #AI #Hebrew"
        thread.append(last_tweet)

    return thread


def validate_thread(thread: List[str], max_chars: int = 400) -> bool:
    """Validate all tweets are under max characters (400 limit)."""
    all_valid = True

    for i, tweet in enumerate(thread, start=1):
        if len(tweet) > max_chars:
            print(f"⚠️ Warning: Tweet {i} is {len(tweet)} chars (max {max_chars})")
            print(f"   Content: {tweet[:100]}...")
            all_valid = False

    return all_valid


def format_thread_for_display(thread: List[str]) -> str:
    """Format thread for display/output."""
    output = []
    output.append("=" * 60)
    output.append(f"TWITTER THREAD ({len(thread)} tweets)")
    output.append("=" * 60)
    output.append("")

    for i, tweet in enumerate(thread, start=1):
        output.append(f"─── Tweet {i}/{len(thread)} ───")
        output.append(tweet)
        output.append("")

    output.append("=" * 60)

    return "\n".join(output)


def format_thread_for_telegram(thread: List[str]) -> str:
    """
    Format thread for Telegram posting.
    Each tweet separated by horizontal line for easy copy/paste.
    """
    output = []
    output.append("🐦 TWITTER THREAD - READY TO POST 🐦")
    output.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    output.append("")
    output.append(f"📊 Total: {len(thread)} tweets")
    output.append("📋 Copy each tweet below and paste to Twitter")
    output.append("")
    output.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    output.append("")

    for i, tweet in enumerate(thread, start=1):
        output.append(f"✂️ TWEET {i}/{len(thread)} ✂️")
        output.append("─────────────────────")
        output.append(tweet)
        output.append("")
        if i < len(thread):
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append("")

    output.append("✅ END OF THREAD")

    return "\n".join(output)


def save_thread_to_file(thread: List[str], output_file: Path):
    """Save thread to text file."""
    content = format_thread_for_display(thread)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Thread saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error saving thread: {e}")


def post_to_telegram(thread: List[str], review_num: int):
    """Post thread to Telegram test channel."""
    try:
        # Import Telegram uploader
        sys.path.insert(0, str(REPO_ROOT / ".repo-tools" / "scripts"))
        from telegram_uploader import send_telegram_message, TelegramConfig, load_config

        # Load Telegram config
        config_file = REPO_ROOT / ".repo-tools" / "scripts" / "telegram_config.yaml"
        config = load_config(config_file)

        # Format for Telegram
        message = format_thread_for_telegram(thread)

        # Send to Hebrew test channel
        print(f"\nPosting thread to Telegram (Hebrew channel)...")
        print(f"Review {review_num}, {len(thread)} tweets")

        response = send_telegram_message(
            message,
            config.hebrew_channel.bot_token,
            config.hebrew_channel.chat_id,
            parse_mode='HTML'
        )

        if response:
            print(f"✓ Thread posted to Telegram!")
            print(f"  Channel: {config.hebrew_channel.username}")
            print(f"  Message ID: {response.get('message_id')}")
            return True
        else:
            print(f"❌ Failed to post to Telegram")
            return False

    except Exception as e:
        print(f"❌ Error posting to Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Build Twitter threads from Hebrew reviews")
    parser.add_argument('--review', type=int, required=True, help='Review number (e.g., 577)')
    parser.add_argument('--output', type=str, help='Output file path (e.g., thread.txt)')
    parser.add_argument('--print', action='store_true', help='Print thread to console')
    parser.add_argument('--telegram', action='store_true', help='Post thread to Telegram test channel')
    parser.add_argument('--clickbait', action='store_true', default=True, help='Use engaging/clickbait style (default: True)')
    parser.add_argument('--simple', action='store_true', help='Use simple style (no clickbait)')
    parser.add_argument('--images', action='store_true', help='Generate images for thread')
    parser.add_argument('--image-dir', type=str, default='/tmp/twitter_images', help='Directory for generated images')

    args = parser.parse_args()

    # Determine style
    use_clickbait = args.clickbait and not args.simple

    print(f"\n🔨 Building Twitter thread for Review {args.review}...")
    if use_clickbait:
        print("   🔥 Using clickbait/engaging style")
    else:
        print("   📝 Using simple style")
    print("")

    # Load review
    content = load_hebrew_review(args.review)
    if not content:
        return 1

    # Build thread
    thread = build_thread(content, args.review, clickbait=use_clickbait)

    print(f"✓ Thread built: {len(thread)} tweets")
    print("")

    # Generate images if requested
    if args.images:
        try:
            from twitter_image_generator import TwitterImageGenerator

            image_dir = Path(args.image_dir)
            generator = TwitterImageGenerator(image_dir)

            # Generate title card
            title = extract_title(content)
            # Extract Hebrew subtitle (second line)
            lines = content.split('\n')
            subtitle = lines[1] if len(lines) > 1 else ""

            title_img = generator.create_title_card(title, subtitle, args.review)
            print(f"✓ Title card: {title_img}")

            # Generate paper link card
            arxiv_link = extract_arxiv_link(content)
            if arxiv_link:
                link_img = generator.create_paper_link_card(arxiv_link, args.review)
                print(f"✓ Paper link card: {link_img}")

            print(f"\n💡 Tip: Attach images to first and last tweets for max engagement!")
            print("")

        except Exception as e:
            print(f"⚠️ Could not generate images: {e}")
            print("")

    # Validate
    if not validate_thread(thread, max_chars=400):
        print("\n⚠️ Warning: Some tweets exceed 400 characters!")
        print("   Thread may need adjustment\n")
    else:
        print("✓ All tweets under 400 characters")
        print("")

    # Output options
    if args.print:
        print(format_thread_for_display(thread))

    if args.output:
        output_path = Path(args.output)
        save_thread_to_file(thread, output_path)

    if args.telegram:
        post_to_telegram(thread, args.review)

    # If no output specified, print to console
    if not args.print and not args.output and not args.telegram:
        print(format_thread_for_display(thread))

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
