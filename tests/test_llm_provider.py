from unittest.mock import AsyncMock, patch

import pytest

from app.ai.base import GeneratedPost, GenerationContext
from app.ai.provider import LLMGenerationError, OpenAIProvider, get_llm_provider


def test_get_llm_provider_openai():
    provider = get_llm_provider("openai", api_key="k", model="gpt-4o-mini")
    assert provider.base_url == "https://api.openai.com/v1"


def test_get_llm_provider_unknown_raises():
    with pytest.raises(ValueError):
        get_llm_provider("nonexistent", api_key="k", model="m")


@pytest.mark.asyncio
async def test_openai_provider_review_post_parses_valid_response():
    provider = OpenAIProvider(api_key="k", model="gpt-4o-mini")
    post = GeneratedPost(title="T", content="content")
    context = GenerationContext(scheduled_time="08:00", timezone="Asia/Tashkent", category="daily_phrases", cefr_level="A2")

    with patch.object(
        provider,
        "_call_llm_json",
        AsyncMock(return_value={"valid": True, "issues": [], "fix_instruction": None}),
    ):
        review = await provider.review_post(post, context)

    assert review.valid is True
    assert review.issues == []
    assert review.fix_instruction is None


@pytest.mark.asyncio
async def test_openai_provider_review_post_parses_major_issue():
    provider = OpenAIProvider(api_key="k", model="gpt-4o-mini")
    post = GeneratedPost(title="T", content="content")
    context = GenerationContext(scheduled_time="08:00", timezone="Asia/Tashkent", category="grammar", cefr_level="A2")

    raw_response = {
        "valid": False,
        "issues": [
            {"field": "grammar", "problem": "wrong article used", "severity": "major"},
            {"field": "naturalness", "problem": "a bit stiff", "severity": "minor"},
        ],
        "fix_instruction": "Fix the article in sentence 1.",
    }

    with patch.object(provider, "_call_llm_json", AsyncMock(return_value=raw_response)):
        review = await provider.review_post(post, context)

    assert review.valid is False
    assert review.has_major_issues is True
    assert len(review.issues) == 2
    assert review.fix_instruction == "Fix the article in sentence 1."


@pytest.mark.asyncio
async def test_openai_provider_review_post_raises_on_missing_valid_field():
    provider = OpenAIProvider(api_key="k", model="gpt-4o-mini")
    post = GeneratedPost(title="T", content="content")
    context = GenerationContext(scheduled_time="08:00", timezone="Asia/Tashkent", category="daily_phrases", cefr_level="A2")

    with patch.object(provider, "_call_llm_json", AsyncMock(return_value={"issues": []})):
        with pytest.raises(LLMGenerationError):
            await provider.review_post(post, context)


@pytest.mark.asyncio
async def test_openai_provider_review_post_raises_on_malformed_issues_field():
    provider = OpenAIProvider(api_key="k", model="gpt-4o-mini")
    post = GeneratedPost(title="T", content="content")
    context = GenerationContext(scheduled_time="08:00", timezone="Asia/Tashkent", category="daily_phrases", cefr_level="A2")

    with patch.object(
        provider, "_call_llm_json", AsyncMock(return_value={"valid": False, "issues": "not-a-list"})
    ):
        with pytest.raises(LLMGenerationError):
            await provider.review_post(post, context)
