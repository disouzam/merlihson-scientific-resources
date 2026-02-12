#!/usr/bin/env python3
"""
Twitter Thread Builder

Builds Twitter threads from Hebrew reviews (280 chars per tweet).
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


def extract_arxiv_link(content: str) -> Optional[str]:
    """Extract ArXiv link from review."""
    # Look for arxiv.org URLs
    match = re.search(r'https?://arxiv\.org/[^\s]+', content)
    if match:
        return match.group(0)
    return None


def split_into_tweets(text: str, max_chars: int = 500) -> List[str]:
    """
    Split text into tweet-sized chunks intelligently.

    Args:
        text: Text to split
        max_chars: Max characters per tweet (default 270 to reserve 10 for numbering)

    Returns:
        List of tweet texts
    """
    tweets = []

    # Split by double newline (paragraphs)
    paragraphs = text.split('\n\n')

    current_tweet = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph fits
        if len(current_tweet) + len(para) + 2 <= max_chars:  # +2 for \n\n
            if current_tweet:
                current_tweet += "\n\n" + para
            else:
                current_tweet = para
        else:
            # Save current tweet if not empty
            if current_tweet:
                tweets.append(current_tweet)

            # If paragraph itself is too long, split by sentences
            if len(para) > max_chars:
                sentences = split_by_sentences(para)

                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue

                    if len(current_tweet) + len(sent) + 1 <= max_chars:  # +1 for space
                        if current_tweet:
                            current_tweet += " " + sent
                        else:
                            current_tweet = sent
                    else:
                        if current_tweet:
                            tweets.append(current_tweet)

                        # If sentence still too long, split by words
                        if len(sent) > max_chars:
                            words = sent.split()
                            current_tweet = ""
                            for word in words:
                                if len(current_tweet) + len(word) + 1 <= max_chars:
                                    if current_tweet:
                                        current_tweet += " " + word
                                    else:
                                        current_tweet = word
                                else:
                                    if current_tweet:
                                        tweets.append(current_tweet)
                                    current_tweet = word
                        else:
                            current_tweet = sent
            else:
                current_tweet = para

    # Don't forget the last tweet
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

    # Split content into tweets
    content_tweets = split_into_tweets(content_without_title, max_chars=490)

    # Build thread
    thread = []

    if clickbait:
        # CLICKBAIT VERSION - More engaging hooks
        hooks = [
            "🔥 Thread about transformers you NEED to read",
            "🧠 Mind-blowing insights on LLM failures",
            "⚡ The physics behind transformer errors",
            "🎯 Why your LLM is actually failing",
            "💡 Revolutionary way to understand LLMs",
            "🚀 Game-changing paper alert"
        ]

        # Pick a hook based on review number (deterministic but varied)
        hook = hooks[review_num % len(hooks)]

        # First tweet: Engaging hook + title
        first_tweet = f"{hook} 🧵\n\n📄 {title}\n\n🇮🇱 Full Hebrew review below ⬇️\n\n#AI #MachineLearning"
        thread.append(first_tweet)

        # Add an engaging intro tweet
        intro_tweet = f"סקירה {review_num} - למה הפוסט הזה חשוב? 🤔\n\n➡️ תובנות מהפכניות על LLMs\n➡️ פיזיקה של שגיאות\n➡️ פתרונות מעשיים\n\nבואו נצלול פנימה 🏊‍♂️\n\n(2/{len(content_tweets) + 3})"
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

            numbered_tweet = f"{emoji} {tweet_text}\n\n({i}/{len(content_tweets) + 3})"
            thread.append(numbered_tweet)

        # Last tweet: Strong CTA + link
        last_tweet = f"🎓 רוצים לקרוא את המחקר המלא?\n\n"
        if arxiv_link:
            last_tweet += f"📄 Paper: {arxiv_link}\n\n"
        last_tweet += f"💬 מה דעתכם? כתבו בתגובות!\n\n🔄 RT אם למדתם משהו חדש\n\n✅ סוף Thread\n\n#AI #MachineLearning #DeepLearning\n\n({len(content_tweets) + 3}/{len(content_tweets) + 3})"
        thread.append(last_tweet)

    else:
        # ORIGINAL VERSION - Simple and clean
        first_tweet = f"{title}\n\n🧵 Full Hebrew review ⬇️"
        thread.append(first_tweet)

        total_tweets = len(content_tweets) + 2

        for i, tweet_text in enumerate(content_tweets, start=2):
            numbered_tweet = f"{tweet_text}\n\n({i}/{total_tweets})"
            thread.append(numbered_tweet)

        last_tweet = ""
        if arxiv_link:
            last_tweet = f"📄 Full paper: {arxiv_link}\n\n"
        last_tweet += f"✅ End of thread\n\n#MachineLearning #AI #Hebrew\n\n({total_tweets}/{total_tweets})"
        thread.append(last_tweet)

    return thread


def validate_thread(thread: List[str], max_chars: int = 500) -> bool:
    """Validate all tweets are under max characters (500 for Premium, 280 for free)."""
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
        output.append(f"[{len(tweet)} chars]")
        output.append("")

    output.append("=" * 60)
    output.append(f"Total tweets: {len(thread)}")
    output.append(f"Total characters: {sum(len(t) for t in thread)}")
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
        output.append(f"[{len(tweet)} chars]")
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
    if not validate_thread(thread, max_chars=500):
        print("\n⚠️ Warning: Some tweets exceed 500 characters!")
        print("   Thread may need adjustment\n")
    else:
        print("✓ All tweets under 500 characters (Twitter Premium)")
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
