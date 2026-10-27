from app.bot.keyboards.yarat_topic import yarat_topic_keyboard


def test_yarat_topic_keyboard_has_random_button_first():
    keyboard = yarat_topic_keyboard()
    first_button = keyboard.inline_keyboard[0][0]
    assert first_button.callback_data == "yarat_topic:"


def test_yarat_topic_keyboard_has_four_topic_examples():
    keyboard = yarat_topic_keyboard()
    callback_data = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "yarat_topic:daily_phrases" in callback_data
    assert "yarat_topic:grammar" in callback_data
    assert "yarat_topic:workplace" in callback_data
    assert "yarat_topic:travel" in callback_data


def test_yarat_topic_keyboard_has_other_button_last():
    keyboard = yarat_topic_keyboard()
    last_button = keyboard.inline_keyboard[-1][0]
    assert last_button.callback_data == "yarat_topic:other"


def test_yarat_topic_callback_parsing_random():
    callback_data = "yarat_topic:"
    topic = callback_data.split(":", 1)[1]
    assert topic == ""
    assert (topic or None) is None


def test_yarat_topic_callback_parsing_category():
    callback_data = "yarat_topic:grammar"
    topic = callback_data.split(":", 1)[1]
    assert topic == "grammar"


def test_yarat_topic_callback_parsing_other():
    callback_data = "yarat_topic:other"
    topic = callback_data.split(":", 1)[1]
    assert topic == "other"
