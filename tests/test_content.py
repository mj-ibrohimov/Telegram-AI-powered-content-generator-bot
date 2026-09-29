import pytest

from app.ai.base import GeneratedPost
from app.content.duplicate_detector import DuplicateDetector
from app.content.generator import ContentGenerator, GenerationFailedError
from app.content.strategy import ContentStrategy
from app.content.validator import validate
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from tests.fakes import FailingLLMProvider, FakeLLMProvider, TimeoutLLMProvider


def test_validate_rejects_empty_content():
    result = validate("Title", "")
    assert not result.valid


def test_validate_rejects_too_short_content():
    result = validate("Title", "short")
    assert not result.valid
    assert any("short" in e for e in result.errors)


def test_validate_rejects_unbalanced_html():
    content = "A" * 100 + "<b>unclosed bold"
    result = validate("Title", content)
    assert not result.valid


def test_validate_accepts_valid_post():
    content = "<b>Hallo</b>\n" + "Ich lerne Deutsch. " * 10
    result = validate("Title", content)
    assert result.valid


def test_strategy_marketing_ratio_zero_excludes_marketing():
    strategy = ContentStrategy(marketing_ratio=0.0)
    selections = [strategy.select_category() for _ in range(50)]
    assert "marketing" not in selections


def test_strategy_news_disabled_removed_from_weights():
    strategy = ContentStrategy(news_enabled=False)
    assert "news" not in strategy.weights


def test_strategy_category_override_always_wins():
    strategy = ContentStrategy()
    assert strategy.select_category(category_override="grammar") == "grammar"


@pytest.mark.asyncio
async def test_generator_creates_draft(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    llm = FakeLLMProvider(posts=[GeneratedPost(title="T", content="A" * 100)])
    generator = ContentGenerator(
        llm=llm,
        strategy=ContentStrategy(),
        duplicate_detector=DuplicateDetector(),
        draft_repo=draft_repo,
        history_repo=history_repo,
        max_attempts=3,
    )

    draft = await generator.generate(
        scheduled_for="2026-09-27_08:00",
        scheduled_time="08:00",
        timezone="Asia/Tashkent",
        cefr_level="Mixed",
        category_override="daily_phrases",
    )

    assert draft.id is not None
    assert draft.status == "WAITING_APPROVAL"
    assert draft.category == "daily_phrases"


@pytest.mark.asyncio
async def test_generator_custom_instruction_uses_custom_category(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    llm = FakeLLMProvider(posts=[GeneratedPost(title="T", content="A" * 100)])
    generator = ContentGenerator(
        llm=llm,
        strategy=ContentStrategy(),
        duplicate_detector=DuplicateDetector(),
        draft_repo=draft_repo,
        history_repo=history_repo,
        max_attempts=3,
    )

    draft = await generator.generate(
        scheduled_for="2026-09-27_manual",
        scheduled_time="14:00",
        timezone="Asia/Tashkent",
        cefr_level="Mixed",
        custom_instruction="Berlin transporti haqida A2 darajasida post yoz",
    )

    assert draft.category == "custom"


@pytest.mark.asyncio
async def test_fake_provider_generates_image_bytes():
    llm = FakeLLMProvider()
    image_bytes = await llm.generate_image("Oktoberfest")
    assert isinstance(image_bytes, bytes)
    assert len(image_bytes) > 0


@pytest.mark.asyncio
async def test_generator_raises_after_max_attempts_on_llm_failure(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    generator = ContentGenerator(
        llm=FailingLLMProvider(),
        strategy=ContentStrategy(),
        duplicate_detector=DuplicateDetector(),
        draft_repo=draft_repo,
        history_repo=history_repo,
        max_attempts=2,
    )

    with pytest.raises(GenerationFailedError):
        await generator.generate(
            scheduled_for="2026-09-27_08:00",
            scheduled_time="08:00",
            timezone="Asia/Tashkent",
            cefr_level="Mixed",
            category_override="daily_phrases",
        )


@pytest.mark.asyncio
async def test_generator_failure_message_never_blank_on_timeout(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    generator = ContentGenerator(
        llm=TimeoutLLMProvider(),
        strategy=ContentStrategy(),
        duplicate_detector=DuplicateDetector(),
        draft_repo=draft_repo,
        history_repo=history_repo,
        max_attempts=1,
    )

    with pytest.raises(GenerationFailedError) as exc_info:
        await generator.generate(
            scheduled_for="2026-09-27_08:00",
            scheduled_time="08:00",
            timezone="Asia/Tashkent",
            cefr_level="Mixed",
            category_override="daily_phrases",
        )

    assert str(exc_info.value).strip() != ""
    assert "ReadTimeout" in str(exc_info.value)
