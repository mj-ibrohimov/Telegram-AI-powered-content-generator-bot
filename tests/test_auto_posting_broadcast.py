from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.handlers.callbacks import on_auto_posting_toggle
from app.config import Settings
from app.database.repositories.settings_repository import SettingsRepository


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        telegram_bot_token="test-token",
        telegram_channel_id="@test",
        admin_telegram_ids="111,222,333",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_callback(data: str, actor_id: int):
    callback = MagicMock()
    callback.data = data
    callback.from_user.id = actor_id
    callback.from_user.full_name = "Admin One"
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_toggle_notifies_other_admins_not_the_actor(session):
    await SettingsRepository(session).set_auto_posting_enabled(True)

    @asynccontextmanager
    async def fake_get_session():
        yield session

    bot = AsyncMock()
    settings = _make_settings()
    callback = _make_callback("auto_posting:off", actor_id=111)

    with patch("app.bot.handlers.callbacks.get_session", fake_get_session):
        await on_auto_posting_toggle(callback, bot, settings)

    notified_ids = [call.kwargs["chat_id"] for call in bot.send_message.await_args_list]
    assert 111 not in notified_ids
    assert set(notified_ids) == {222, 333}
    assert await SettingsRepository(session).is_auto_posting_enabled() is False


@pytest.mark.asyncio
async def test_toggle_notification_failure_for_one_admin_does_not_block_others(session):
    @asynccontextmanager
    async def fake_get_session():
        yield session

    bot = AsyncMock()
    bot.send_message.side_effect = [RuntimeError("blocked by user"), None]
    settings = _make_settings()
    callback = _make_callback("auto_posting:on", actor_id=111)

    with patch("app.bot.handlers.callbacks.get_session", fake_get_session):
        await on_auto_posting_toggle(callback, bot, settings)

    assert bot.send_message.await_count == 2


@pytest.mark.asyncio
async def test_invalid_action_rejected_without_touching_db(session):
    @asynccontextmanager
    async def fake_get_session():
        yield session

    bot = AsyncMock()
    settings = _make_settings()
    callback = _make_callback("auto_posting:garbage", actor_id=111)

    with patch("app.bot.handlers.callbacks.get_session", fake_get_session):
        await on_auto_posting_toggle(callback, bot, settings)

    callback.answer.assert_awaited_once()
    bot.send_message.assert_not_awaited()
