from datetime import datetime

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.bot.formatting import format_channel_post
from app.database.models import DraftStatus
from app.database.repositories.draft_repository import DraftRepository
from app.errors import describe_exception

logger = structlog.get_logger()


class AlreadyPublishedError(Exception):
    pass


class DraftNotFoundError(Exception):
    pass


class PublicationService:
    def __init__(self, bot: Bot, channel_id: str, channel_link: str, draft_repo: DraftRepository):
        self.bot = bot
        self.channel_id = channel_id
        self.channel_link = channel_link
        self.draft_repo = draft_repo

    async def publish(self, draft_id: int) -> tuple[object, datetime]:
        draft = await self.draft_repo.get(draft_id)
        if draft is None:
            raise DraftNotFoundError(f"draft {draft_id} not found")

        if draft.status == DraftStatus.PUBLISHED.value:
            raise AlreadyPublishedError(f"draft {draft_id} already published")

        if draft.status not in (DraftStatus.WAITING_APPROVAL.value, DraftStatus.GENERATED.value):
            raise AlreadyPublishedError(f"draft {draft_id} is in status {draft.status}, cannot publish")

        logger.info("publication_attempted", draft_id=draft_id)
        try:
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=format_channel_post(draft, self.channel_link),
                parse_mode="HTML",
            )
        except TelegramAPIError as exc:
            logger.error("publication_failed", draft_id=draft_id, error=describe_exception(exc))
            raise

        updated_draft = await self.draft_repo.mark_published(
            draft_id=draft_id, telegram_message_id=message.message_id, channel_id=self.channel_id
        )
        logger.info("publication_successful", draft_id=draft_id, telegram_message_id=message.message_id)
        return updated_draft, updated_draft.published_at
