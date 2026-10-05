from app.bot.keyboards.daraja import cefr_level_keyboard, daraja_category_keyboard


def test_cefr_level_keyboard_has_all_six_levels():
    keyboard = cefr_level_keyboard()
    callback_data = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert callback_data == [
        "daraja_level:A1",
        "daraja_level:A2",
        "daraja_level:B1",
        "daraja_level:B2",
        "daraja_level:C1",
        "daraja_level:C2",
    ]


def test_daraja_category_keyboard_embeds_level_and_category():
    keyboard = daraja_category_keyboard("B1")
    callback_data = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "daraja_cat:B1:daily_phrases" in callback_data
    assert "daraja_cat:B1:workplace" in callback_data
    assert "daraja_cat:B1:travel" in callback_data


def test_daraja_category_keyboard_random_topic_has_empty_category():
    keyboard = daraja_category_keyboard("A2")
    callback_data = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "daraja_cat:A2:" in callback_data


def test_daraja_cat_callback_parsing_splits_into_three_parts():
    callback_data = "daraja_cat:B2:workplace"
    _, level, category = callback_data.split(":", 2)
    assert level == "B2"
    assert category == "workplace"


def test_daraja_cat_callback_parsing_random_topic_gives_empty_category():
    callback_data = "daraja_cat:C1:"
    _, level, category = callback_data.split(":", 2)
    assert level == "C1"
    assert category == ""
    assert (category or None) is None
