import pytest

from app.database.repositories.settings_repository import AUTO_POSTING_KEY, SettingsRepository


@pytest.mark.asyncio
async def test_auto_posting_enabled_by_default(session):
    repo = SettingsRepository(session)
    assert await repo.is_auto_posting_enabled() is True


@pytest.mark.asyncio
async def test_disable_auto_posting(session):
    repo = SettingsRepository(session)
    await repo.set_auto_posting_enabled(False)
    assert await repo.is_auto_posting_enabled() is False


@pytest.mark.asyncio
async def test_enable_after_disable(session):
    repo = SettingsRepository(session)
    await repo.set_auto_posting_enabled(False)
    await repo.set_auto_posting_enabled(True)
    assert await repo.is_auto_posting_enabled() is True


@pytest.mark.asyncio
async def test_set_is_idempotent_upsert(session):
    repo = SettingsRepository(session)
    await repo.set_auto_posting_enabled(False)
    await repo.set_auto_posting_enabled(False)
    assert await repo.get(AUTO_POSTING_KEY) == "false"
