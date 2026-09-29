from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import SchedulerRun


class SchedulerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, scheduled_for: str) -> SchedulerRun | None:
        result = await self.session.execute(select(SchedulerRun).where(SchedulerRun.scheduled_for == scheduled_for))
        return result.scalar_one_or_none()

    async def already_processed(self, scheduled_for: str) -> bool:
        run = await self.get(scheduled_for)
        return run is not None and run.status in ("SUCCESS", "RUNNING")

    async def start_run(self, scheduled_for: str) -> SchedulerRun:
        run = SchedulerRun(scheduled_for=scheduled_for, status="RUNNING")
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def complete_run(self, scheduled_for: str, draft_id: int | None = None) -> None:
        run = await self.get(scheduled_for)
        if run is None:
            return
        run.status = "SUCCESS"
        run.completed_at = datetime.now(timezone.utc)
        run.draft_id = draft_id
        await self.session.commit()

    async def fail_run(self, scheduled_for: str, error_message: str) -> None:
        run = await self.get(scheduled_for)
        if run is None:
            return
        run.status = "FAILED"
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = error_message[:2000]
        await self.session.commit()
