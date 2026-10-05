from app.bot.formatting import sanitize_html


def test_br_tag_converted_to_newline():
    """Real bug: Telegram's HTML parse mode does not support <br> (unlike a
    browser) and rejects the entire message with "Unsupported start tag br"
    if it's sent through unescaped. This caused /yarat to silently produce
    no reply -- the draft was generated successfully but Telegram rejected
    the message containing it."""
    content = "Line one.<br>Line two.<br/>Line three.<br />Line four."
    result = sanitize_html(content)
    assert "<br" not in result.lower()
    assert result == "Line one.\nLine two.\nLine three.\nLine four."


def test_br_removed_from_allowed_tags_does_not_break_balance_check():
    content = "<b>Bold</b><br>Normal text"
    result = sanitize_html(content)
    assert result == "<b>Bold</b>\nNormal text"


def test_other_unsupported_tags_still_stripped():
    content = "<p>Paragraph</p><div>Div</div><b>Bold</b>"
    result = sanitize_html(content)
    assert "<p>" not in result
    assert "<div>" not in result
    assert "<b>Bold</b>" in result


def test_supported_tags_pass_through_balanced():
    content = "<b>Bold</b> <i>Italic</i> <code>code</code>"
    result = sanitize_html(content)
    assert result == content


def test_unbalanced_supported_tag_is_stripped():
    content = "<b>unclosed bold"
    result = sanitize_html(content)
    assert "<b>" not in result
