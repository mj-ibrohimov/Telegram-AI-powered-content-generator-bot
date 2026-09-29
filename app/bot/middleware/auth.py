from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = structlog.get_logger()


class AdminAuthMiddleware(BaseMiddleware):
    """Blocks any private-chat interaction from users not in the configured
    admin list. Applied to messages and callback queries in private chats only
    -- the bot never needs to process input from arbitrary users."""

    def __init__(self, admin_ids: list[int]):
        self.admin_ids = set(admin_ids)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if user.id not in self.admin_ids:
            logger.warning("unauthorized_access_attempt", telegram_user_id=user.id)
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ You are not authorized to use this bot.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⛔ You are not authorized to use this bot.")
            return None

        return await handler(event, data)
