from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.base import GeneratedPost
from app.bot.middleware.auth import AdminAuthMiddleware
from app.content.duplicate_detector import DuplicateDetector
from app.content.generator import ContentGenerator
from app.content.strategy import ContentStrategy
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from app.services.draft_service import DraftService
from app.services.improvement_service import ImprovementService
from tests.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_discard_marks_discarded_and_creates_new_draft(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    original = await draft_repo.create(
        scheduled_for="2026-09-27_20:00",
        category="daily_phrases",
        cefr_level="Mixed",
        title="Original",
        content="A" * 100,
    )

    llm = FakeLLMProvider(posts=[GeneratedPost(title="New", content="B" * 100)])
    generator = ContentGenerator(
        llm=llm,
        strategy=ContentStrategy(),
        duplicate_detector=DuplicateDetector(),
        draft_repo=draft_repo,
        history_repo=history_repo,
    )
    draft_service = DraftService(generator=generator, draft_repo=draft_repo)

    new_draft = await draft_service.discard_and_regenerate(original.id)

    refreshed_original = await draft_repo.get(original.id)
    assert refreshed_original.status == "DISCARDED"
    assert refreshed_original.discard_reason == "owner_discarded"
    assert new_draft.id != original.id
    assert new_draft.status == "WAITING_APPROVAL"


@pytest.mark.asyncio
async def test_improve_creates_revision_and_updates_content(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    draft = await draft_repo.create(
        scheduled_for="2026-09-27_20:00",
        category="grammar",
        cefr_level="Mixed",
        title="Original",
        content="A" * 100,
    )

    llm = FakeLLMProvider()
    service = ImprovementService(
        llm=llm, draft_repo=draft_repo, history_repo=history_repo, timezone="Asia/Tashkent", marketing_ratio=0.1
    )

    updated = await service.improve(draft, "Make it shorter")

    assert len(llm.improve_calls) == 1
    assert llm.improve_calls[0][1] == "Make it shorter"
    assert updated.content != "A" * 100
    assert updated.status == "WAITING_APPROVAL"


@pytest.mark.asyncio
async def test_auth_middleware_blocks_unauthorized_user():
    middleware = AdminAuthMiddleware(admin_ids=[111])
    handler = AsyncMock()
    event = MagicMock()
    event.answer = AsyncMock()

    data = {"event_from_user": MagicMock(id=999)}
    result = await middleware(handler, event, data)

    handler.assert_not_awaited()
    assert result is None


@pytest.mark.asyncio
async def test_auth_middleware_allows_authorized_user():
    middleware = AdminAuthMiddleware(admin_ids=[111])
    handler = AsyncMock(return_value="ok")
    event = MagicMock()

    data = {"event_from_user": MagicMock(id=111)}
    result = await middleware(handler, event, data)

    handler.assert_awaited_once()
    assert result == "ok"
