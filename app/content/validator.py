import re
from dataclasses import dataclass, field

MIN_LENGTH = 50
MAX_LENGTH = 3000  # hard ceiling; content should normally target 500-1500

ALLOWED_HTML_TAGS = {"b", "strong", "i", "em", "u", "s", "code", "pre", "a"}


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def _has_balanced_html_tags(content: str) -> bool:
    tag_pattern = re.compile(r"</?([a-zA-Z0-9]+)[^>]*>")
    stack = []
    for match in tag_pattern.finditer(content):
        tag = match.group(1).lower()
        if tag not in ALLOWED_HTML_TAGS:
            continue
        is_closing = match.group(0).startswith("</")
        if is_closing:
            if not stack or stack[-1] != tag:
                return False
            stack.pop()
        else:
            stack.append(tag)
    return not stack


def validate(title: str, content: str) -> ValidationResult:
    errors = []

    if not title or not title.strip():
        errors.append("title is empty")

    if not content or not content.strip():
        errors.append("content is empty")
        return ValidationResult(valid=False, errors=errors)

    length = len(content)
    if length < MIN_LENGTH:
        errors.append(f"content too short ({length} chars, min {MIN_LENGTH})")
    if length > MAX_LENGTH:
        errors.append(f"content too long ({length} chars, max {MAX_LENGTH})")

    if not _has_balanced_html_tags(content):
        errors.append("unbalanced or unsupported HTML tags")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
