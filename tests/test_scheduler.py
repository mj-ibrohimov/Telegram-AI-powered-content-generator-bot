from datetime import datetime

import pytest
from zoneinfo import ZoneInfo

from app.database.repositories.scheduler_repository import SchedulerRepository
from app.scheduler.scheduler import get_slot_id


def test_get_slot_id_format():
    tz = ZoneInfo("Asia/Tashkent")
    now = datetime(2026, 9, 27, 20, 0, tzinfo=tz)
    assert get_slot_id("20:00", now) == "2026-09-27_20:00"


def test_get_slot_id_different_times_different_slots():
    tz = ZoneInfo("Asia/Tashkent")
    now = datetime(2026, 9, 27, 8, 0, tzinfo=tz)
    assert get_slot_id("08:00", now) != get_slot_id("20:00", now)


@pytest.mark.asyncio
async def test_scheduler_repository_idempotency(session):
    repo = SchedulerRepository(session)
    slot_id = "2026-09-27_20:00"

    assert not await repo.already_processed(slot_id)

    await repo.start_run(slot_id)
    assert await repo.already_processed(slot_id)

    await repo.complete_run(slot_id, draft_id=None)
    assert await repo.already_processed(slot_id)


@pytest.mark.asyncio
async def test_scheduler_repository_failed_run_not_processed(session):
    repo = SchedulerRepository(session)
    slot_id = "2026-09-27_20:00"

    await repo.start_run(slot_id)
    await repo.fail_run(slot_id, "boom")

    assert not await repo.already_processed(slot_id)
