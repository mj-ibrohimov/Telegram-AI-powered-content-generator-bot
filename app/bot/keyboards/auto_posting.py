from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot import texts


def auto_posting_keyboard(currently_enabled: bool) -> InlineKeyboardMarkup:
    if currently_enabled:
        button = InlineKeyboardButton(text=texts.BTN_AUTO_POSTING_TURN_OFF, callback_data="auto_posting:off")
    else:
        button = InlineKeyboardButton(text=texts.BTN_AUTO_POSTING_TURN_ON, callback_data="auto_posting:on")
    return InlineKeyboardMarkup(inline_keyboard=[[button]])
