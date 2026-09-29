from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CategoryUsage, ContentHistory


class ContentHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_recent(self, limit: int = 20) -> list[ContentHistory]:
        result = await self.session.execute(select(ContentHistory).order_by(desc(ContentHistory.created_at)).limit(limit))
        return list(result.scalars().all())

    async def get_recent_by_category(self, category: str, limit: int = 10) -> list[ContentHistory]:
        result = await self.session.execute(
            select(ContentHistory)
            .where(ContentHistory.category == category)
            .order_by(desc(ContentHistory.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def record_category_usage(self, category: str) -> None:
        self.session.add(CategoryUsage(category=category))
        await self.session.commit()

    async def get_category_usage_counts(self, since_hours: int = 48) -> dict[str, int]:
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        result = await self.session.execute(select(CategoryUsage).where(CategoryUsage.used_at >= since))
        rows = result.scalars().all()
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.category] = counts.get(row.category, 0) + 1
        return counts

    async def get_recent_category_sequence(self, limit: int = 5) -> list[str]:
        result = await self.session.execute(select(CategoryUsage).order_by(desc(CategoryUsage.used_at)).limit(limit))
        return [row.category for row in result.scalars().all()]
