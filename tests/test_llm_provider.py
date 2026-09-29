from unittest.mock import AsyncMock, patch

import pytest

from app.ai.base import GeneratedPost, GenerationContext, QualityReview
from app.ai.provider import CodeCraftProvider, FallbackLLMProvider, LLMGenerationError, OpenAIProvider, get_llm_provider
from tests.fakes import FailingLLMProvider, FakeLLMProvider


def test_get_llm_provider_openai():
    provider = get_llm_provider("openai", api_key="k", model="gpt-4o-mini")
    assert provider.base_url == "https://api.openai.com/v1"


def test_get_llm_provider_codecraft_defaults_base_url():
    provider = get_llm_provider("codecraft", api_key="k", model="gpt-4o-mini")
    assert isinstance(provider, CodeCraftProvider)
    assert provider.base_url == "https://codecraftapi.com/v1"


def test_get_llm_provider_codecraft_respects_explicit_base_url():
    provider = get_llm_provider("codecraft", api_key="k", model="gpt-4o-mini", base_url="https://custom.example/v1")
    assert provider.base_url == "https://custom.example/v1"


def test_get_llm_provider_unknown_raises():
    with pytest.raises(ValueError):
        get_llm_provider("nonexistent", api_key="k", model="m")


@pytest.mark.asyncio
async def test_codecraft_provider_generate_image_disabled():
    provider = CodeCraftProvider(api_key="k", model="gpt-4o-mini")
    with pytest.raises(LLMGenerationError):
        await provider.generate_image("a picture of Berlin")


@pytest.mark.asyncio
async def test_fallback_provider_uses_primary_when_it_succeeds():
    primary = FakeLLMProvider(posts=[GeneratedPost(title="Primary", content="A" * 100)])
    fallback = FakeLLMProvider(posts=[GeneratedPost(title="Fallback", content="B" * 100)])
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    context = GenerationContext(scheduled_time="08:00", timezone="Asia/Tashkent", category="daily_phrases", cefr_level="Mixed")
    post = await provider.generate_post(context)

    assert post.title == "Primary"
    assert fallback.call_count == 0


@pytest.mark.asyncio
async def test_fallback_provider_falls_back_when_primary_fails():
    primary = FailingLLMProvider()
    fallback = FakeLLMProvider(posts=[GeneratedPost(title="Fallback", content="B" * 100)])
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    context = GenerationContext(scheduled_time="08:00", timezone="Asia/Tashkent", category="daily_phrases", cefr_level="Mixed")
    post = await provider.generate_post(context)

    assert post.title == "Fallback"
    assert fallback.call_count == 1


@pytest.mark.asyncio
async def test_fallback_provider_image_falls_back():
    primary = CodeCraftProvider(api_key="k", model="gpt-4o-mini")
    fallback = FakeLLMProvider()
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    image_bytes = await provider.generate_image("Oktoberfest")
    assert image_bytes == b"fake-image-bytes"


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
