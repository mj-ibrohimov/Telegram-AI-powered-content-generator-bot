from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot import texts

# (category key, Uzbek button label)
TOPIC_EXAMPLES = [
    ("daily_phrases", "🗣 Kundalik"),
    ("grammar", "📖 Grammatika"),
    ("workplace", "💼 Ish joyida"),
    ("travel", "✈️ Sayohat"),
]


def yarat_topic_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=texts.BTN_YARAT_RANDOM, callback_data="yarat_topic:")]]
    rows.extend(
        [InlineKeyboardButton(text=label, callback_data=f"yarat_topic:{category}")]
        for category, label in TOPIC_EXAMPLES
    )
    rows.append([InlineKeyboardButton(text=texts.BTN_YARAT_OTHER, callback_data="yarat_topic:other")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
