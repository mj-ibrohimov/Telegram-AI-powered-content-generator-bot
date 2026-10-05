import asyncio
import logging
import sys

import structlog
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from fastapi import FastAPI
from sqlalchemy import select

from app.ai.provider import get_llm_provider
from app.bot import texts
from app.bot.handlers import admin, callbacks, drafts, start
from app.bot.middleware.auth import AdminAuthMiddleware
from app.config import Settings, get_settings
from app.database.database import get_session, init_db
from app.news.provider import NullNewsProvider, WebNewsProvider
from app.scheduler.scheduler import build_scheduler

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = structlog.get_logger()


def create_health_app(scheduler) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict:
        db_status = "ok"
        try:
            async with get_session() as session:
                await session.execute(select(1))
        except Exception:  # noqa: BLE001
            db_status = "error"

        return {
            "status": "ok",
            "database": db_status,
            "scheduler": "running" if scheduler.running else "stopped",
        }

    return app


async def main() -> None:
    settings: Settings = get_settings()

    await init_db()
    logger.info("database_initialized")

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())

    auth_middleware = AdminAuthMiddleware(admin_ids=settings.admin_ids)
    dispatcher.message.middleware(auth_middleware)
    dispatcher.callback_query.middleware(auth_middleware)

    dispatcher.include_router(start.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(callbacks.router)
    dispatcher.include_router(drafts.router)

    await bot.set_my_commands(
        [BotCommand(command=cmd, description=desc) for cmd, desc in texts.BOT_COMMANDS]
    )
    logger.info("bot_commands_registered")

    llm_provider = get_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
    )

    news_provider = WebNewsProvider(settings.news_api_key) if settings.news_enabled else NullNewsProvider()

    scheduler = build_scheduler(bot=bot, settings=settings, llm_provider=llm_provider, news_provider=news_provider)
    scheduler.start()
    logger.info("scheduler_started")

    dispatcher["settings"] = settings
    dispatcher["scheduler"] = scheduler
    dispatcher["llm_provider"] = llm_provider
    dispatcher["news_provider"] = news_provider

    health_app = create_health_app(scheduler)
    config = uvicorn.Config(
        health_app,
        host=settings.health_check_host,
        port=settings.health_check_port,
        log_level="warning",
    )
    health_server = uvicorn.Server(config)

    logger.info("bot_starting")
    await asyncio.gather(
        dispatcher.start_polling(bot),
        health_server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
