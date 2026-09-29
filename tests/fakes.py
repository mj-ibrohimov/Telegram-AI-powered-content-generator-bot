import httpx

from app.ai.base import GeneratedPost, GenerationContext, LLMProvider, QualityReview


class FakeLLMProvider(LLMProvider):
    def __init__(
        self,
        posts: list[GeneratedPost] | None = None,
        reviews: list[QualityReview] | None = None,
    ):
        self.posts = posts or []
        # Defaults to always-valid so existing tests that don't care about
        # the review step keep passing without having to specify one.
        self.reviews = reviews
        self.call_count = 0
        self.improve_calls: list[tuple[str, str]] = []
        self.review_calls: list[GeneratedPost] = []

    async def generate_post(self, context: GenerationContext) -> GeneratedPost:
        if self.call_count < len(self.posts):
            post = self.posts[self.call_count]
        else:
            post = GeneratedPost(
                title=f"Post {self.call_count}",
                content="A" * 100 + f" unique-{self.call_count}",
            )
        self.call_count += 1
        return post

    async def improve_post(self, current_content: str, instruction: str, context: GenerationContext) -> GeneratedPost:
        self.improve_calls.append((current_content, instruction))
        return GeneratedPost(title="Improved", content=current_content + " " + instruction)

    async def review_post(self, post: GeneratedPost, context: GenerationContext) -> QualityReview:
        self.review_calls.append(post)
        if self.reviews:
            index = min(len(self.review_calls) - 1, len(self.reviews) - 1)
            return self.reviews[index]
        return QualityReview(valid=True, issues=[])

    async def generate_image(self, prompt: str) -> bytes:
        return b"fake-image-bytes"


class FailingLLMProvider(LLMProvider):
    async def generate_post(self, context: GenerationContext) -> GeneratedPost:
        raise RuntimeError("LLM unavailable")

    async def improve_post(self, current_content: str, instruction: str, context: GenerationContext) -> GeneratedPost:
        raise RuntimeError("LLM unavailable")

    async def review_post(self, post: GeneratedPost, context: GenerationContext) -> QualityReview:
        raise RuntimeError("LLM unavailable")

    async def generate_image(self, prompt: str) -> bytes:
        raise RuntimeError("LLM unavailable")


class TimeoutLLMProvider(LLMProvider):
    """Simulates a network timeout, which httpx represents with an empty
    str() -- used to guard against 'error=' showing up blank in logs."""

    async def generate_post(self, context: GenerationContext) -> GeneratedPost:
        raise httpx.ReadTimeout("")

    async def improve_post(self, current_content: str, instruction: str, context: GenerationContext) -> GeneratedPost:
        raise httpx.ReadTimeout("")

    async def review_post(self, post: GeneratedPost, context: GenerationContext) -> QualityReview:
        raise httpx.ReadTimeout("")

    async def generate_image(self, prompt: str) -> bytes:
        raise httpx.ReadTimeout("")
