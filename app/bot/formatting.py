import re

from app.bot import texts
from app.database.models import Draft

ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "s", "code", "pre", "a", "br"}
TAG_PATTERN = re.compile(r"</?([a-zA-Z0-9]+)(\s+[^>]*)?/?>")


def sanitize_html(content: str) -> str:
    """Strips any HTML tags Telegram doesn't support / that aren't balanced,
    so malformed markup never reaches the Telegram API."""

    def _strip_disallowed(match: re.Match) -> str:
        tag = match.group(1).lower()
        return match.group(0) if tag in ALLOWED_TAGS else ""

    cleaned = TAG_PATTERN.sub(_strip_disallowed, content)

    # Second pass: drop any unbalanced closing/opening tags.
    tokens = list(TAG_PATTERN.finditer(cleaned))
    to_remove: set[int] = set()
    open_stack: list[tuple[str, int]] = []
    for match in tokens:
        tag = match.group(1).lower()
        if tag == "br":
            continue
        is_closing = match.group(0).startswith("</")
        if is_closing:
            if open_stack and open_stack[-1][0] == tag:
                open_stack.pop()
            else:
                to_remove.add(match.start())
        else:
            open_stack.append((tag, match.start()))
    for _, start in open_stack:
        to_remove.add(start)

    if not to_remove:
        return cleaned

    out = []
    last = 0
    for match in tokens:
        if match.start() in to_remove:
            out.append(cleaned[last:match.start()])
            last = match.end()
    out.append(cleaned[last:])
    return "".join(out)


def format_draft_message(draft: Draft, channel_link: str, status_label: str = texts.DRAFT_STATUS_WAITING) -> str:
    category_label = texts.category_label(draft.category)
    safe_content = sanitize_html(draft.content)
    footer = texts.CHANNEL_FOOTER.format(link=channel_link)
    return (
        f"{texts.DRAFT_HEADER}\n\n"
        f"<b>{texts.DRAFT_SCHEDULED_SLOT}:</b> {draft.scheduled_for}\n"
        f"<b>{texts.DRAFT_CATEGORY}:</b> {category_label}\n"
        f"<b>{texts.DRAFT_CEFR}:</b> {draft.cefr_level}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{safe_content}\n\n{footer}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{texts.DRAFT_STATUS}:</b> {status_label}"
    )


def format_published_message(draft: Draft, published_at_str: str) -> str:
    return f"{texts.PUBLISHED_HEADER}\n\n" + texts.PUBLISHED_BODY.format(time=published_at_str)


def format_channel_post(draft: Draft, channel_link: str) -> str:
    footer = texts.CHANNEL_FOOTER.format(link=channel_link)
    return f"{sanitize_html(draft.content)}\n\n{footer}"
