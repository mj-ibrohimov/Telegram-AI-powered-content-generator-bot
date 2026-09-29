from datetime import datetime

import structlog
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from zoneinfo import ZoneInfo

from app.bot import texts
from app.bot.formatting import format_draft_message
from app.bot.keyboards.approval import approval_keyboard
from app.bot.states.improvement import FreeformStates, ImageStates, ImprovementStates
from app.config import Settings
from app.content.duplicate_detector import DuplicateDetector
from app.content.generator import ContentGenerator, GenerationFailedError
from app.content.strategy import ContentStrategy
from app.database.database import get_session
from app.database.models import DraftStatus
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from app.errors import describe_exception
from app.services.improvement_service import ImprovementFailedError, ImprovementService

logger = structlog.get_logger()
router = Router(name="drafts")


@router.message(ImprovementStates.WAITING_FOR_IMPROVEMENT_INSTRUCTION)
async def on_improvement_instruction(message: Message, state: FSMContext, settings: Settings, llm_provider) -> None:
    data = await state.get_data()
    draft_id = data.get("draft_id")
    instruction = (message.text or "").strip()

    if not draft_id:
        await state.clear()
        await message.answer(texts.IMPROVE_STATE_LOST)
        return

    if not instruction:
        await message.answer(texts.IMPROVE_EMPTY_INSTRUCTION)
        return

    await message.answer(texts.IMPROVE_REVISING)

    async with get_session() as session:
        draft_repo = DraftRepository(session)
        draft = await draft_repo.get(draft_id)
        if draft is None:
            await state.clear()
            await message.answer(texts.IMPROVE_DRAFT_GONE)
            return
        if draft.status == DraftStatus.PUBLISHED.value:
            await state.clear()
            await message.answer(texts.IMPROVE_ALREADY_PUBLISHED)
            return

        history_repo = ContentHistoryRepository(session)
        service = ImprovementService(
            llm=llm_provider,
            draft_repo=draft_repo,
            history_repo=history_repo,
            timezone=settings.timezone,
            marketing_ratio=settings.promotional_post_ratio,
        )

        try:
            updated_draft = await service.improve(draft, instruction)
        except ImprovementFailedError as exc:
            logger.error("improvement_handler_failed", draft_id=draft_id, error=describe_exception(exc))
            await draft_repo.set_status(draft_id, DraftStatus.WAITING_APPROVAL)
            await message.answer(texts.IMPROVE_FAILED.format(reason=exc))
            return

    await state.clear()
    await message.answer(
        texts.IMPROVE_REVISED_HEADER + format_draft_message(updated_draft, settings.channel_link),
        reply_markup=approval_keyboard(updated_draft.id),
        parse_mode="HTML",
    )


@router.message(FreeformStates.WAITING_FOR_PROMPT)
async def on_freeform_prompt(message: Message, state: FSMContext, settings: Settings, llm_provider, news_provider) -> None:
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer(texts.FREEFORM_EMPTY)
        return

    await state.clear()
    await message.answer(texts.FREEFORM_GENERATING)

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
                scheduled_for=f"custom_{datetime.now(tz).strftime('%Y%m%d%H%M%S')}",
                scheduled_time=now_str,
                timezone=settings.timezone,
                cefr_level=settings.default_cefr_level,
                custom_instruction=prompt,
            )
        except GenerationFailedError as exc:
            logger.error("freeform_generation_failed", error=describe_exception(exc))
            await message.answer(texts.FREEFORM_FAILED.format(reason=exc))
            return

    await message.answer(
        format_draft_message(draft, settings.channel_link),
        reply_markup=approval_keyboard(draft.id),
        parse_mode="HTML",
    )


@router.message(ImageStates.WAITING_FOR_PROMPT)
async def on_image_prompt(message: Message, state: FSMContext, llm_provider) -> None:
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer(texts.IMAGE_EMPTY)
        return

    await state.clear()
    await message.answer(texts.IMAGE_GENERATING)

    try:
        image_bytes = await llm_provider.generate_image(prompt)
    except Exception as exc:  # noqa: BLE001
        detail = describe_exception(exc)
        logger.error("image_generation_failed", error=detail)
        await message.answer(texts.IMAGE_FAILED.format(reason=detail))
        return

    await message.answer_photo(
        BufferedInputFile(image_bytes, filename="rasm.png"),
        caption=prompt[:1024],
    )
