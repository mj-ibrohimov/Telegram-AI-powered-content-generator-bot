from datetime import datetime

import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from zoneinfo import ZoneInfo

from app.bot import texts
from app.bot.formatting import format_draft_message
from app.bot.keyboards.approval import approval_keyboard
from app.bot.keyboards.daraja import cefr_level_keyboard
from app.bot.states.improvement import FreeformStates, ImageStates
from app.config import Settings
from app.content.duplicate_detector import DuplicateDetector
from app.content.generator import ContentGenerator, GenerationFailedError
from app.content.strategy import ContentStrategy
from app.database.database import get_session
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from app.errors import describe_exception

logger = structlog.get_logger()
router = Router(name="admin")

VALID_CATEGORIES = {
    "daily_phrases",
    "vocabulary",
    "travel",
    "workplace",
    "grammar",
    "mistakes",
    "comparison",
    "quiz",
    "culture",
    "news",
    "media",
    "challenge",
    "migration",
    "marketing",
}
VALID_CEFR = {"A1", "A2", "B1", "B2", "C1", "C2", "Mixed"}


async def _generate_and_send(
    message: Message,
    settings: Settings,
    llm_provider,
    news_provider,
    cefr_level: str,
    category_override: str | None,
) -> None:
    tz = ZoneInfo(settings.timezone)
    now_str = datetime.now(tz).strftime("%H:%M")

    async with get_session() as session:
        draft_repo = DraftRepository(session)
        history_repo = ContentHistoryRepository(session)
        strategy = ContentStrategy(marketing_ratio=settings.promotional_post_ratio, news_enabled=settings.news_enabled)
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

        try:
            draft = await generator.generate(
                scheduled_for=f"manual_{datetime.now(tz).strftime('%Y%m%d%H%M%S')}",
                scheduled_time=now_str,
                timezone=settings.timezone,
                cefr_level=cefr_level,
                category_override=category_override,
            )
        except GenerationFailedError as exc:
            logger.error("manual_generation_failed", error=describe_exception(exc))
            await message.answer(texts.GENERATION_FAILED_MANUAL.format(reason=exc))
            return

    await message.answer(
        format_draft_message(draft, settings.channel_link),
        reply_markup=approval_keyboard(draft.id),
        parse_mode="HTML",
    )


@router.message(Command("holat"))
async def cmd_status(message: Message, settings: Settings, scheduler) -> None:
    db_ok = True
    try:
        async with get_session() as session:
            await session.execute(select(1))
    except Exception:  # noqa: BLE001
        db_ok = False

    next_run = None
    jobs = scheduler.get_jobs() if scheduler else []
    upcoming = [j.next_run_time for j in jobs if j.next_run_time]
    if upcoming:
        next_run = min(upcoming).strftime("%Y-%m-%d %H:%M %Z")

    await message.answer(
        texts.STATUS_TEMPLATE.format(
            scheduler_state="Ishlayapti" if scheduler else "Ishlamayapti",
            next_run=next_run or "noma'lum",
            channel=settings.telegram_channel_id,
            db_state="Ulangan" if db_ok else "XATO",
        ),
        parse_mode="HTML",
    )


@router.message(Command("jadval"))
async def cmd_schedule(message: Message, settings: Settings) -> None:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    lines = "\n".join(f"• {t}" for t in settings.post_times_list)
    await message.answer(
        texts.SCHEDULE_TEMPLATE.format(date=now.strftime("%Y-%m-%d"), timezone=settings.timezone, lines=lines),
        parse_mode="HTML",
    )


@router.message(Command("sozlamalar"))
async def cmd_settings(message: Message, settings: Settings) -> None:
    await message.answer(
        texts.SETTINGS_TEMPLATE.format(
            timezone=settings.timezone,
            post_times=settings.post_times,
            cefr=settings.default_cefr_level,
            marketing_ratio=settings.promotional_post_ratio,
            dup_threshold=settings.duplicate_similarity_threshold,
            max_attempts=settings.max_generation_attempts,
            news_enabled=settings.news_enabled,
            llm_provider=settings.llm_provider,
            llm_model=settings.llm_model,
        ),
        parse_mode="HTML",
    )


@router.message(Command("tarix"))
async def cmd_history(message: Message) -> None:
    async with get_session() as session:
        draft_repo = DraftRepository(session)
        recent = await draft_repo.get_recent_published(limit=10)

    if not recent:
        await message.answer(texts.HISTORY_EMPTY)
        return

    lines = []
    for d in recent:
        published = d.published_at.strftime("%Y-%m-%d %H:%M") if d.published_at else "?"
        lines.append(f"• [{published}] ({texts.category_label(d.category)}) {d.title}")

    await message.answer(texts.HISTORY_HEADER + "\n".join(lines), parse_mode="HTML")


@router.message(Command("yarat"))
async def cmd_generate(message: Message, settings: Settings, llm_provider, news_provider) -> None:
    parts = (message.text or "").split()[1:]
    category_override = None
    cefr_level = settings.default_cefr_level

    for part in parts:
        if part in VALID_CATEGORIES:
            category_override = part
        elif part in VALID_CEFR:
            cefr_level = part

    await message.answer(texts.GENERATING)
    await _generate_and_send(message, settings, llm_provider, news_provider, cefr_level, category_override)


@router.message(Command("daraja"))
async def cmd_daraja(message: Message) -> None:
    await message.answer(texts.DARAJA_PICK_LEVEL, reply_markup=cefr_level_keyboard())


@router.message(Command("erkin"))
async def cmd_freeform(message: Message, state: FSMContext) -> None:
    await state.set_state(FreeformStates.WAITING_FOR_PROMPT)
    await message.answer(texts.FREEFORM_PROMPT_ASK)


@router.message(Command("rasm"))
async def cmd_image(message: Message, state: FSMContext) -> None:
    await state.set_state(ImageStates.WAITING_FOR_PROMPT)
    await message.answer(texts.IMAGE_PROMPT_ASK)
