from datetime import datetime

import structlog
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.bot import texts
from app.bot.formatting import format_draft_message
from app.errors import describe_exception
from app.bot.keyboards.approval import approval_keyboard
from app.config import Settings
from app.content.duplicate_detector import DuplicateDetector
from app.content.generator import ContentGenerator, GenerationFailedError
from app.content.strategy import ContentStrategy
from app.database.database import get_session
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from app.database.repositories.scheduler_repository import SchedulerRepository

logger = structlog.get_logger()


def get_slot_id(scheduled_time: str, now: datetime) -> str:
    return f"{now.strftime('%Y-%m-%d')}_{scheduled_time}"


async def run_scheduled_generation(
    bot: Bot,
    settings: Settings,
    llm_provider,
    news_provider,
    scheduled_time: str,
) -> None:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    slot_id = get_slot_id(scheduled_time, now)

    async with get_session() as session:
        scheduler_repo = SchedulerRepository(session)

        if await scheduler_repo.already_processed(slot_id):
            logger.info("scheduler_slot_already_processed", slot_id=slot_id)
            return

        await scheduler_repo.start_run(slot_id)
        logger.info("generation_started", slot_id=slot_id, scheduled_time=scheduled_time)

        try:
            draft_repo = DraftRepository(session)
            history_repo = ContentHistoryRepository(session)
            strategy = ContentStrategy(
                marketing_ratio=settings.promotional_post_ratio,
                news_enabled=settings.news_enabled,
            )
            duplicate_detector = DuplicateDetector(settings.duplicate_similarity_threshold)
            generator = ContentGenerator(
                llm=llm_provider,
                strategy=strategy,
                duplicate_detector=duplicate_detector,
                draft_repo=draft_repo,
                history_repo=history_repo,
                news_provider=news_provider,
                max_attempts=settings.max_generation_attempts,
            )

            draft = await generator.generate(
                scheduled_for=slot_id,
                scheduled_time=scheduled_time,
                timezone=settings.timezone,
                cefr_level=settings.default_cefr_level,
            )

            for admin_id in settings.admin_ids:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=format_draft_message(draft, settings.channel_link),
                        reply_markup=approval_keyboard(draft.id),
                        parse_mode="HTML",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error("send_draft_to_admin_failed", admin_id=admin_id, error=describe_exception(exc))

            await scheduler_repo.complete_run(slot_id, draft_id=draft.id)
            logger.info("generation_completed", slot_id=slot_id, draft_id=draft.id)

        except GenerationFailedError as exc:
            await scheduler_repo.fail_run(slot_id, str(exc))
            logger.error("scheduler_failed", slot_id=slot_id, error=describe_exception(exc))
            for admin_id in settings.admin_ids:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=texts.GENERATION_FAILED_SCHEDULED.format(slot=scheduled_time),
                    )
                except Exception:  # noqa: BLE001
                    pass
        except Exception as exc:  # noqa: BLE001
            await scheduler_repo.fail_run(slot_id, str(exc))
            logger.error("scheduler_failed_unexpected", slot_id=slot_id, error=describe_exception(exc))


def build_scheduler(
    bot: Bot,
    settings: Settings,
    llm_provider,
    news_provider,
) -> AsyncIOScheduler:
    tz = ZoneInfo(settings.timezone)
    scheduler = AsyncIOScheduler(timezone=tz)

    for time_str in settings.post_times_list:
        hour, minute = time_str.split(":")
        scheduler.add_job(
            run_scheduled_generation,
            trigger=CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
            args=[bot, settings, llm_provider, news_provider, time_str],
            id=f"generate_{time_str}",
            replace_existing=True,
            misfire_grace_time=300,
        )

    logger.info("scheduler_configured", post_times=settings.post_times_list, timezone=settings.timezone)
    return scheduler
