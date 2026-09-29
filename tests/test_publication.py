from unittest.mock import AsyncMock

import pytest

from app.database.repositories.draft_repository import DraftRepository
from app.services.publication_service import AlreadyPublishedError, DraftNotFoundError, PublicationService


class FakeMessage:
    def __init__(self, message_id: int):
        self.message_id = message_id


@pytest.mark.asyncio
async def test_publish_success(session):
    draft_repo = DraftRepository(session)
    draft = await draft_repo.create(
        scheduled_for="2026-09-27_20:00",
        category="daily_phrases",
        cefr_level="Mixed",
        title="T",
        content="A" * 100,
    )

    bot = AsyncMock()
    bot.send_message.return_value = FakeMessage(message_id=555)

    service = PublicationService(bot=bot, channel_id="@testchannel", channel_link="https://t.me/testchannel", draft_repo=draft_repo)
    updated_draft, published_at = await service.publish(draft.id)

    assert updated_draft.status == "PUBLISHED"
    assert updated_draft.telegram_message_id == 555
    assert published_at is not None
    bot.send_message.assert_awaited_once()
    sent_text = bot.send_message.call_args.kwargs["text"]
    assert "https://t.me/testchannel" in sent_text


@pytest.mark.asyncio
async def test_publish_twice_raises(session):
    draft_repo = DraftRepository(session)
    draft = await draft_repo.create(
        scheduled_for="2026-09-27_20:00",
        category="daily_phrases",
        cefr_level="Mixed",
        title="T",
        content="A" * 100,
    )

    bot = AsyncMock()
    bot.send_message.return_value = FakeMessage(message_id=555)

    service = PublicationService(bot=bot, channel_id="@testchannel", channel_link="https://t.me/testchannel", draft_repo=draft_repo)
    await service.publish(draft.id)

    with pytest.raises(AlreadyPublishedError):
        await service.publish(draft.id)

    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_missing_draft_raises(session):
    draft_repo = DraftRepository(session)
    bot = AsyncMock()
    service = PublicationService(bot=bot, channel_id="@testchannel", channel_link="https://t.me/testchannel", draft_repo=draft_repo)

    with pytest.raises(DraftNotFoundError):
        await service.publish(9999)
