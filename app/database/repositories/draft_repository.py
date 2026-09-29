from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ContentHistory, Draft, DraftStatus, Publication, Revision


class DraftRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        scheduled_for: str,
        category: str,
        cefr_level: str,
        title: str,
        content: str,
        generation_attempt: int = 1,
    ) -> Draft:
        draft = Draft(
            scheduled_for=scheduled_for,
            category=category,
            cefr_level=cefr_level,
            title=title,
            content=content,
            status=DraftStatus.WAITING_APPROVAL.value,
            generation_attempt=generation_attempt,
        )
        self.session.add(draft)
        await self.session.commit()
        await self.session.refresh(draft)
        return draft

    async def get(self, draft_id: int) -> Draft | None:
        result = await self.session.execute(select(Draft).where(Draft.id == draft_id))
        return result.scalar_one_or_none()

    async def mark_published(self, draft_id: int, telegram_message_id: int, channel_id: str) -> Draft | None:
        draft = await self.get(draft_id)
        if draft is None:
            return None
        draft.status = DraftStatus.PUBLISHED.value
        draft.published_at = datetime.now(timezone.utc)
        draft.telegram_message_id = telegram_message_id
        self.session.add(
            Publication(draft_id=draft.id, channel_id=channel_id, telegram_message_id=telegram_message_id)
        )
        self.session.add(
            ContentHistory(
                draft_id=draft.id,
                category=draft.category,
                topic=draft.title,
                summary=draft.content[:500],
                status="PUBLISHED",
            )
        )
        await self.session.commit()
        await self.session.refresh(draft)
        return draft

    async def mark_discarded(self, draft_id: int, reason: str = "owner_discarded") -> Draft | None:
        draft = await self.get(draft_id)
        if draft is None:
            return None
        draft.status = DraftStatus.DISCARDED.value
        draft.discard_reason = reason
        self.session.add(
            ContentHistory(
                draft_id=draft.id,
                category=draft.category,
                topic=draft.title,
                summary=draft.content[:500],
                status="DISCARDED",
            )
        )
        await self.session.commit()
        await self.session.refresh(draft)
        return draft

    async def mark_failed(self, draft_id: int) -> Draft | None:
        draft = await self.get(draft_id)
        if draft is None:
            return None
        draft.status = DraftStatus.FAILED.value
        await self.session.commit()
        await self.session.refresh(draft)
        return draft

    async def set_status(self, draft_id: int, status: DraftStatus) -> Draft | None:
        draft = await self.get(draft_id)
        if draft is None:
            return None
        draft.status = status.value
        await self.session.commit()
        await self.session.refresh(draft)
        return draft

    async def add_revision(self, draft_id: int, content: str, instruction: str | None) -> Draft | None:
        draft = await self.get(draft_id)
        if draft is None:
            return None
        result = await self.session.execute(
            select(Revision).where(Revision.draft_id == draft_id).order_by(desc(Revision.version))
        )
        last = result.scalars().first()
        next_version = (last.version + 1) if last else 1
        self.session.add(
            Revision(draft_id=draft_id, version=next_version, content=content, instruction=instruction)
        )
        draft.content = content
        draft.status = DraftStatus.WAITING_APPROVAL.value
        await self.session.commit()
        await self.session.refresh(draft)
        return draft

    async def get_recent_published(self, limit: int = 10) -> list[Draft]:
        result = await self.session.execute(
            select(Draft)
            .where(Draft.status == DraftStatus.PUBLISHED.value)
            .order_by(desc(Draft.published_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_by_category(self, category: str, limit: int = 5) -> list[Draft]:
        result = await self.session.execute(
            select(Draft)
            .where(Draft.category == category, Draft.status == DraftStatus.PUBLISHED.value)
            .order_by(desc(Draft.published_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_discarded(self, limit: int = 5) -> list[Draft]:
        result = await self.session.execute(
            select(Draft)
            .where(Draft.status == DraftStatus.DISCARDED.value)
            .order_by(desc(Draft.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_all(self, limit: int = 20) -> list[Draft]:
        result = await self.session.execute(select(Draft).order_by(desc(Draft.created_at)).limit(limit))
        return list(result.scalars().all())
