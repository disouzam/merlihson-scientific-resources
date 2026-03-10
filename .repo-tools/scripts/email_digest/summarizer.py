"""Claude API summarization with token batching and merge."""

import logging
import time
from collections import defaultdict

import anthropic

from email_digest.config import Settings
from email_digest.email_parser import Category, Email, group_by_thread

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an email digest assistant. You receive a day's worth of emails organized \
by category and produce a detailed, visually appealing daily briefing.

OUTPUT FORMAT (use Telegram HTML tags: <b>, <i>, no markdown):

🔴 <b>Action Required</b>

For each actionable email:
⚡ <b>Sender</b> — <i>Subject</i>
  2-3 sentence summary: what the email is about, what action is needed from me, \
and any deadline or urgency. Include specific details (names, dates, amounts).
  🕐 Deadline: [date if mentioned]

━━━━━━━━━━━━━━━━━━━━

💬 <b>Personal</b>

For each personal email or thread:
👤 <b>Sender</b> — <i>Subject</i>
  2-3 sentence summary covering the key content. For threads, summarize the full \
conversation arc: who said what, what was decided, what's pending.

━━━━━━━━━━━━━━━━━━━━

📰 <b>Newsletters & Updates</b>

For each newsletter:
📌 <b>Source</b> — <i>Subject</i>
  2-3 sentence summary of the most interesting/useful points. Mention specific \
technologies, papers, tools, or insights that stand out.

━━━━━━━━━━━━━━━━━━━━

📊 <b>Quick Stats</b>
Total emails | By category breakdown

RULES:
1. Provide substantive summaries — I want to understand each email's content without opening it.
2. For actionable items, extract WHO needs to do WHAT by WHEN.
3. Include specific details: names, dates, numbers, amounts, URLs mentioned.
4. If an email is in Hebrew, summarize it in Hebrew.
5. If a category has zero emails, omit that section entirely (including its separator).
6. For threads, summarize the progression and final outcome, not each reply separately.
7. Never fabricate information not present in the emails.
8. Use blank lines between emails for readability.
9. Omit the deadline line if no deadline is mentioned.
"""

TOKEN_THRESHOLD = 80_000  # Split into batches if estimated tokens exceed this


def summarize(emails: list[Email], settings: Settings, target_date: str) -> str:
    """
    Summarize categorized emails using Claude API.

    Uses single-call if under token threshold, otherwise batches by category
    and merges with a final call.
    """
    if not emails:
        return f"<b>Daily Email Digest -- {target_date}</b>\n0 emails processed\n\nNo emails received yesterday."

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Group by category
    by_category = defaultdict(list)
    for email in emails:
        by_category[email.category].append(email)

    prompt = _build_prompt(emails, by_category, target_date)
    estimated_tokens = len(prompt) // 4

    if estimated_tokens < TOKEN_THRESHOLD:
        logger.info(f"Single-call summarization (~{estimated_tokens} tokens)")
        summary = _call_claude(client, settings, prompt)
    else:
        logger.info(f"Batched summarization (~{estimated_tokens} tokens)")
        summary = _batched_summarize(client, settings, emails, by_category, target_date)

    # Prepend header
    header = f"📬 <b>Daily Email Digest — {target_date}</b>\n📨 {len(emails)} emails processed"

    return f"{header}\n\n{summary}"


def summarize_fallback(emails: list[Email], target_date: str) -> str:
    """Fallback: return subjects-only list when Claude API fails."""
    lines = [f"<b>Daily Email Digest -- {target_date}</b>"]
    lines.append(f"{len(emails)} emails (summarization unavailable)\n")
    lines.append("<b>Subjects:</b>")

    for email in emails[:50]:
        sender = email.sender.split("<")[0].strip()
        lines.append(f"• {sender} -- {email.subject}")

    if len(emails) > 50:
        lines.append(f"... and {len(emails) - 50} more")

    return "\n".join(lines)


def _build_prompt(
    emails: list[Email],
    by_category: dict[Category, list[Email]],
    target_date: str,
) -> str:
    """Build the user prompt from categorized emails."""
    parts = [f"Here are the emails from {target_date}. Summarize them according to your instructions.\n"]

    category_order = [
        Category.ACTIONABLE,
        Category.PERSONAL,
        Category.NEWSLETTER,
        Category.SOCIAL,
        Category.MARKETING,
    ]

    for cat in category_order:
        cat_emails = by_category.get(cat, [])
        if not cat_emails:
            continue

        parts.append(f"\n=== {cat.value.upper()} ({len(cat_emails)} emails) ===\n")

        threads = group_by_thread(cat_emails)
        for thread_id, thread_emails in threads.items():
            if len(thread_emails) > 1:
                parts.append(f"[Thread: {len(thread_emails)} messages]")
                for j, email in enumerate(thread_emails):
                    body = email.body[:300] if len(thread_emails) > 2 else email.body[:500]
                    parts.append(
                        f"  Message {j + 1}: From: {email.sender}\n"
                        f"  Subject: {email.subject}\n"
                        f"  Body: {body}\n"
                    )
            else:
                email = thread_emails[0]
                body = email.body[:500]
                parts.append(
                    f"From: {email.sender}\n"
                    f"Subject: {email.subject}\n"
                    f"Date: {email.date}\n"
                    f"Body: {body}\n"
                )

    return "\n".join(parts)


def _batched_summarize(
    client: anthropic.Anthropic,
    settings: Settings,
    emails: list[Email],
    by_category: dict[Category, list[Email]],
    target_date: str,
) -> str:
    """Split into category batches, summarize each, then merge."""
    partial_summaries = []

    # Batch 1: Actionable + Personal
    batch1_cats = [Category.ACTIONABLE, Category.PERSONAL]
    batch1_emails = []
    for cat in batch1_cats:
        batch1_emails.extend(by_category.get(cat, []))

    if batch1_emails:
        batch1_by_cat = defaultdict(list)
        for e in batch1_emails:
            batch1_by_cat[e.category].append(e)
        prompt = _build_prompt(batch1_emails, batch1_by_cat, target_date)
        partial_summaries.append(_call_claude(client, settings, prompt))

    # Batch 2: Newsletter
    batch2_emails = by_category.get(Category.NEWSLETTER, [])
    if batch2_emails:
        batch2_by_cat = {Category.NEWSLETTER: batch2_emails}
        prompt = _build_prompt(batch2_emails, batch2_by_cat, target_date)
        partial_summaries.append(_call_claude(client, settings, prompt))

    # Batch 3: Social + Marketing
    batch3_cats = [Category.SOCIAL, Category.MARKETING]
    batch3_emails = []
    for cat in batch3_cats:
        batch3_emails.extend(by_category.get(cat, []))

    if batch3_emails:
        batch3_by_cat = defaultdict(list)
        for e in batch3_emails:
            batch3_by_cat[e.category].append(e)
        prompt = _build_prompt(batch3_emails, batch3_by_cat, target_date)
        partial_summaries.append(_call_claude(client, settings, prompt))

    # Merge
    if len(partial_summaries) == 1:
        return partial_summaries[0]

    merge_prompt = (
        "Merge these partial email summaries into a single cohesive daily digest. "
        "Maintain the section structure (Action Required, Personal, Newsletters, Social, Marketing). "
        "Remove any duplicate information.\n\n"
        + "\n---\n".join(partial_summaries)
    )
    return _call_claude(client, settings, merge_prompt)


def _call_claude(
    client: anthropic.Anthropic, settings: Settings, user_prompt: str, max_retries: int = 3
) -> str:
    """Call Claude API with retries."""
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Claude API error (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def _build_stats(by_category: dict[Category, list[Email]]) -> str:
    """Build stats line."""
    parts = []
    for cat in [Category.ACTIONABLE, Category.PERSONAL, Category.NEWSLETTER, Category.SOCIAL, Category.MARKETING]:
        count = len(by_category.get(cat, []))
        if count:
            parts.append(f"{count} {cat.value}")
    return f"Stats: {', '.join(parts)}"
