import random

DEFAULT_CATEGORY_WEIGHTS: dict[str, int] = {
    "daily_phrases": 20,
    "vocabulary": 15,
    "grammar": 15,
    "workplace": 10,
    "quiz": 10,
    "culture": 10,
    "news": 5,
    "media": 5,
    "mistakes": 10,
    "challenge": 5,
    "marketing": 5,
}

# Suggested typical category per slot, used as a soft bias rather than a hard rule.
SLOT_BIAS: dict[str, str] = {
    "08:00": "daily_phrases",
    "12:00": "grammar",
    "16:00": "workplace",
    "20:00": "quiz",
    "22:00": "culture",
}


class ContentStrategy:
    def __init__(
        self,
        weights: dict[str, int] | None = None,
        marketing_ratio: float = 0.10,
        news_enabled: bool = False,
    ):
        self.weights = dict(weights or DEFAULT_CATEGORY_WEIGHTS)
        self.marketing_ratio = marketing_ratio
        if not news_enabled:
            self.weights.pop("news", None)

    def select_category(
        self,
        scheduled_time: str | None = None,
        recent_categories: list[str] | None = None,
        category_override: str | None = None,
    ) -> str:
        if category_override:
            return category_override

        recent_categories = recent_categories or []
        candidates = dict(self.weights)

        # Marketing is capped strictly by ratio, not just weight.
        if "marketing" in candidates and random.random() > self.marketing_ratio:
            candidates.pop("marketing")

        # Softly discourage repeating the same category as the last 2 slots.
        for cat in recent_categories[-2:]:
            if cat in candidates and len(candidates) > 1:
                candidates[cat] = max(1, candidates[cat] // 3)

        # Bias toward the slot's typical category if it's still a candidate.
        bias_category = SLOT_BIAS.get(scheduled_time or "")
        if bias_category and bias_category in candidates:
            candidates[bias_category] = int(candidates[bias_category] * 1.5)

        categories = list(candidates.keys())
        weights = [candidates[c] for c in categories]
        return random.choices(categories, weights=weights, k=1)[0]
