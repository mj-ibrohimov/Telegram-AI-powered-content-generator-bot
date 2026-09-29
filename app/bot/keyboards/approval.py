from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot import texts


def approval_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_APPROVE, callback_data=f"approve:{draft_id}")],
            [InlineKeyboardButton(text=texts.BTN_IMPROVE, callback_data=f"improve:{draft_id}")],
            [InlineKeyboardButton(text=texts.BTN_DISCARD, callback_data=f"discard:{draft_id}")],
        ]
    )
