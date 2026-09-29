from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenerationContext:
    scheduled_time: str
    timezone: str
    category: str
    cefr_level: str
    language: str = "German + Uzbek"
    recent_posts: list[str] = field(default_factory=list)
    discarded_posts: list[str] = field(default_factory=list)
    recent_categories: list[str] = field(default_factory=list)
    marketing_ratio: float = 0.10
    is_promotional_slot: bool = False
    news_items: list[dict] | None = None
    custom_instruction: str | None = None


@dataclass
class GeneratedPost:
    title: str
    content: str


@dataclass
class QualityIssue:
    field: str  # e.g. "grammar", "cefr_level", "category_adherence", "factual_accuracy"
    problem: str
    severity: str  # "minor" | "major"


@dataclass
class QualityReview:
    valid: bool
    issues: list[QualityIssue] = field(default_factory=list)
    fix_instruction: str | None = None

    @property
    def has_major_issues(self) -> bool:
        return any(i.severity == "major" for i in self.issues)


class LLMProvider(ABC):
    @abstractmethod
    async def generate_post(self, context: GenerationContext) -> GeneratedPost:
        ...

    @abstractmethod
    async def improve_post(self, current_content: str, instruction: str, context: GenerationContext) -> GeneratedPost:
        ...

    @abstractmethod
    async def review_post(self, post: GeneratedPost, context: GenerationContext) -> QualityReview:
        ...

    @abstractmethod
    async def generate_image(self, prompt: str) -> bytes:
        ...
