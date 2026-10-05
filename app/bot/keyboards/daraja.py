from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# (category key, Uzbek button label)
QUICK_CATEGORIES = [
    ("daily_phrases", "🗣 Kundalik"),
    ("workplace", "💼 Korporativ"),
    ("travel", "✈️ Sayohat"),
]


def cefr_level_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=level, callback_data=f"daraja_level:{level}") for level in CEFR_LEVELS[:3]],
        [InlineKeyboardButton(text=level, callback_data=f"daraja_level:{level}") for level in CEFR_LEVELS[3:]],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def daraja_category_keyboard(level: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"daraja_cat:{level}:{category}")]
        for category, label in QUICK_CATEGORIES
    ]
    rows.append([InlineKeyboardButton(text="🎲 Istalgan mavzu", callback_data=f"daraja_cat:{level}:")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
