from app.bot.keyboards.auto_posting import auto_posting_keyboard


def test_keyboard_shows_turn_off_when_enabled():
    keyboard = auto_posting_keyboard(currently_enabled=True)
    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "auto_posting:off"


def test_keyboard_shows_turn_on_when_disabled():
    keyboard = auto_posting_keyboard(currently_enabled=False)
    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "auto_posting:on"
