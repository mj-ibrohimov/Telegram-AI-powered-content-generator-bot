import base64
import json

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.base import GeneratedPost, GenerationContext, LLMProvider, QualityIssue, QualityReview
from app.ai.prompts import (
    CATEGORY_GUIDANCE,
    IMPROVE_INSTRUCTION_TEMPLATE,
    REVIEW_SYSTEM_PROMPT,
    REVIEW_USER_TEMPLATE,
    SYSTEM_PROMPT,
)
from app.errors import describe_exception

logger = structlog.get_logger()


class LLMGenerationError(Exception):
    pass


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible chat completions provider. Works with OpenAI and any
    OpenAI-compatible endpoint (set llm_base_url to point elsewhere)."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def _build_user_message(self, context: GenerationContext) -> str:
        guidance = CATEGORY_GUIDANCE.get(context.category, "Create a useful German-learning post.")
        payload = {
            "scheduled_time": context.scheduled_time,
            "timezone": context.timezone,
            "category": context.category,
            "cefr_level": context.cefr_level,
            "language": context.language,
            "recent_posts": context.recent_posts,
            "discarded_posts": context.discarded_posts,
            "recent_categories": context.recent_categories,
            "marketing_ratio": context.marketing_ratio,
            "news_items": context.news_items or [],
            "custom_instruction": context.custom_instruction or "",
        }
        message = (
            f"Category guidance: {guidance}\n\n"
            f"Context (JSON): {json.dumps(payload, ensure_ascii=False)}\n\n"
            "Avoid repeating any topic, vocabulary, or example listed in recent_posts or discarded_posts."
        )
        if context.custom_instruction:
            message += (
                f"\n\nThe channel owner's exact custom request (follow this closely, it takes priority "
                f"over the category guidance above): \"{context.custom_instruction}\""
            )
        return message

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, LLMGenerationError)),
    )
    async def _call_llm_json(self, messages: list[dict], temperature: float = 0.8) -> dict:
        """Calls chat completions with JSON-object mode and returns the parsed
        JSON body. Callers validate/interpret the shape themselves since
        generate/improve and review use different JSON schemas."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()

        try:
            raw = data["choices"][0]["message"]["content"]
            return json.loads(raw)
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("llm_malformed_output", error=describe_exception(exc))
            raise LLMGenerationError("LLM returned malformed output") from exc

    async def _call_llm(self, messages: list[dict]) -> GeneratedPost:
        parsed = await self._call_llm_json(messages)

        try:
            title = str(parsed["title"]).strip()
            content = str(parsed["content"]).strip()
        except (KeyError, TypeError) as exc:
            logger.warning("llm_malformed_output", error=describe_exception(exc))
            raise LLMGenerationError("LLM returned malformed output") from exc

        if not title or not content:
            raise LLMGenerationError("LLM returned empty title/content")

        return GeneratedPost(title=title, content=content)

    async def generate_post(self, context: GenerationContext) -> GeneratedPost:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_message(context)},
        ]
        return await self._call_llm(messages)

    async def improve_post(self, current_content: str, instruction: str, context: GenerationContext) -> GeneratedPost:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_message(context)},
            {
                "role": "user",
                "content": IMPROVE_INSTRUCTION_TEMPLATE.format(
                    current_content=current_content, instruction=instruction
                ),
            },
        ]
        return await self._call_llm(messages)

    async def review_post(self, post: GeneratedPost, context: GenerationContext) -> QualityReview:
        guidance = CATEGORY_GUIDANCE.get(context.category, "Create a useful German-learning post.")
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": REVIEW_USER_TEMPLATE.format(
                    category=context.category,
                    cefr_level=context.cefr_level,
                    guidance=guidance,
                    title=post.title,
                    content=post.content,
                ),
            },
        ]
        parsed = await self._call_llm_json(messages, temperature=0.2)

        try:
            valid = bool(parsed["valid"])
            raw_issues = parsed.get("issues", [])
            if not isinstance(raw_issues, list):
                raise TypeError("issues must be a list")

            issues = []
            for raw_issue in raw_issues:
                issues.append(
                    QualityIssue(
                        field=str(raw_issue.get("field", "unknown")),
                        problem=str(raw_issue.get("problem", "")).strip(),
                        severity=str(raw_issue.get("severity", "minor")).strip().lower(),
                    )
                )

            fix_instruction = parsed.get("fix_instruction")
            fix_instruction = str(fix_instruction).strip() if fix_instruction else None
        except (KeyError, TypeError, AttributeError) as exc:
            logger.warning("review_malformed_output", error=describe_exception(exc))
            raise LLMGenerationError("Review LLM returned malformed output") from exc

        return QualityReview(valid=valid, issues=issues, fix_instruction=fix_instruction)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, LLMGenerationError)),
    )
    async def generate_image(self, prompt: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json",
                },
            )
            response.raise_for_status()
            data = response.json()

        try:
            b64_data = data["data"][0]["b64_json"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("image_generation_malformed_output", error=describe_exception(exc))
            raise LLMGenerationError("Image provider returned malformed output") from exc

        return base64.b64decode(b64_data)


def get_llm_provider(provider_name: str, api_key: str, model: str, base_url: str | None = None) -> LLMProvider:
    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
    raise ValueError(f"Unknown LLM provider: {provider_name}")
