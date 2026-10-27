from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.database.repositories.settings_repository import SettingsRepository
from app.scheduler.scheduler import run_scheduled_generation
from tests.fakes import FakeLLMProvider


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        telegram_bot_token="test-token",
        telegram_channel_id="@test",
        admin_telegram_ids="111",
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.asyncio
async def test_scheduled_generation_skipped_when_auto_posting_disabled(session):
    await SettingsRepository(session).set_auto_posting_enabled(False)

    @asynccontextmanager
    async def fake_get_session():
        yield session

    bot = AsyncMock()
    llm = FakeLLMProvider()
    settings = _make_settings()

    with patch("app.scheduler.scheduler.get_session", fake_get_session):
        await run_scheduled_generation(bot, settings, llm, None, "08:00")

    # No LLM call was made and no message was sent -- this is the actual
    # token-saving behavior: the function must return before constructing
    # a ContentGenerator at all.
    assert llm.call_count == 0
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduled_generation_runs_when_auto_posting_enabled(session):
    await SettingsRepository(session).set_auto_posting_enabled(True)

    @asynccontextmanager
    async def fake_get_session():
        yield session

    bot = AsyncMock()
    bot.send_message.return_value = AsyncMock(message_id=1)
    llm = FakeLLMProvider()
    settings = _make_settings()

    with patch("app.scheduler.scheduler.get_session", fake_get_session):
        await run_scheduled_generation(bot, settings, llm, None, "08:00")

    assert llm.call_count == 1
    bot.send_message.assert_awaited_once()
