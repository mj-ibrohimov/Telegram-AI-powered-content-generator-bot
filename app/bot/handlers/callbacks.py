import structlog
from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from zoneinfo import ZoneInfo

from app.bot import texts
from app.bot.formatting import format_draft_message, format_published_message
from app.bot.handlers.admin import VALID_CEFR, VALID_CATEGORIES, _generate_and_send
from app.bot.keyboards.approval import approval_keyboard
from app.bot.keyboards.auto_posting import auto_posting_keyboard
from app.bot.keyboards.daraja import daraja_category_keyboard
from app.bot.states.improvement import FreeformStates, ImprovementStates
from app.config import Settings
from app.content.duplicate_detector import DuplicateDetector
from app.content.generator import ContentGenerator, GenerationFailedError
from app.content.strategy import ContentStrategy
from app.database.database import get_session
from app.database.models import DraftStatus
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from app.database.repositories.settings_repository import SettingsRepository
from app.errors import describe_exception
from app.services.draft_service import DraftService
from app.services.publication_service import AlreadyPublishedError, DraftNotFoundError, PublicationService

logger = structlog.get_logger()
router = Router(name="callbacks")


def _parse_draft_id(callback_data: str) -> int | None:
    try:
        return int(callback_data.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


@router.callback_query(lambda c: c.data and c.data.startswith("approve:"))
async def on_approve(callback: CallbackQuery, bot: Bot, settings: Settings) -> None:
    draft_id = _parse_draft_id(callback.data)
    if draft_id is None:
        await callback.answer(texts.INVALID_REQUEST, show_alert=True)
        return

    async with get_session() as session:
        draft_repo = DraftRepository(session)
        service = PublicationService(
            bot=bot,
            channel_id=settings.telegram_channel_id,
            channel_link=settings.channel_link,
            draft_repo=draft_repo,
        )
        try:
            draft, published_at = await service.publish(draft_id)
        except DraftNotFoundError:
            await callback.answer(texts.DRAFT_NOT_FOUND, show_alert=True)
            return
        except AlreadyPublishedError:
            await callback.answer(texts.ALREADY_PUBLISHED_ALERT, show_alert=True)
            return
        except TelegramAPIError as exc:
            logger.error("publish_telegram_error", draft_id=draft_id, error=describe_exception(exc))
            await callback.answer(texts.PUBLISH_TELEGRAM_ERROR, show_alert=True)
            return

    tz = ZoneInfo(settings.timezone)
    published_local = published_at.astimezone(tz).strftime("%H:%M")

    await callback.message.edit_text(
        format_published_message(draft, published_local),
        parse_mode="HTML",
    )
    await callback.answer(texts.PUBLISHED_ALERT)


@router.callback_query(lambda c: c.data and c.data.startswith("discard:"))
async def on_discard(callback: CallbackQuery, settings: Settings, llm_provider, news_provider) -> None:
    draft_id = _parse_draft_id(callback.data)
    if draft_id is None:
        await callback.answer(texts.INVALID_REQUEST, show_alert=True)
        return

    async with get_session() as session:
        draft_repo = DraftRepository(session)
        existing = await draft_repo.get(draft_id)
        if existing is None:
            await callback.answer(texts.DRAFT_NOT_FOUND, show_alert=True)
            return
        if existing.status == DraftStatus.PUBLISHED.value:
            await callback.answer(texts.DISCARD_ALREADY_PUBLISHED, show_alert=True)
            return

        await callback.message.edit_text(texts.DISCARDED_REGENERATING)

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
        draft_service = DraftService(generator=generator, draft_repo=draft_repo)

        try:
            new_draft = await draft_service.discard_and_regenerate(draft_id)
        except GenerationFailedError as exc:
            logger.error("discard_regeneration_failed", draft_id=draft_id, error=describe_exception(exc))
            await callback.message.answer(texts.DISCARD_REGEN_FAILED)
            await callback.answer()
            return

    await callback.message.answer(
        format_draft_message(new_draft, settings.channel_link),
        reply_markup=approval_keyboard(new_draft.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("improve:"))
async def on_improve(callback: CallbackQuery, state: FSMContext) -> None:
    draft_id = _parse_draft_id(callback.data)
    if draft_id is None:
        await callback.answer(texts.INVALID_REQUEST, show_alert=True)
        return

    async with get_session() as session:
        draft_repo = DraftRepository(session)
        draft = await draft_repo.get(draft_id)
        if draft is None:
            await callback.answer(texts.DRAFT_NOT_FOUND, show_alert=True)
            return
        if draft.status == DraftStatus.PUBLISHED.value:
            await callback.answer(texts.IMPROVE_ALREADY_PUBLISHED, show_alert=True)
            return
        await draft_repo.set_status(draft_id, DraftStatus.IMPROVING)

    await state.set_state(ImprovementStates.WAITING_FOR_IMPROVEMENT_INSTRUCTION)
    await state.update_data(draft_id=draft_id, admin_id=callback.from_user.id)

    await callback.message.answer(texts.IMPROVE_PROMPT)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("daraja_level:"))
async def on_daraja_level(callback: CallbackQuery) -> None:
    level = callback.data.split(":", 1)[1]
    if level not in VALID_CEFR:
        await callback.answer(texts.INVALID_REQUEST, show_alert=True)
        return

    await callback.message.edit_text(
        texts.DARAJA_PICK_CATEGORY.format(level=level),
        reply_markup=daraja_category_keyboard(level),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("daraja_cat:"))
async def on_daraja_category(callback: CallbackQuery, settings: Settings, llm_provider, news_provider) -> None:
    _, level, category = callback.data.split(":", 2)
    if level not in VALID_CEFR:
        await callback.answer(texts.INVALID_REQUEST, show_alert=True)
        return

    await callback.message.edit_text(texts.GENERATING)
    await callback.answer()
    await _generate_and_send(
        callback.message, settings, llm_provider, news_provider, level, category or None
    )


@router.callback_query(lambda c: c.data and c.data.startswith("yarat_topic:"))
async def on_yarat_topic(callback: CallbackQuery, state: FSMContext, settings: Settings, llm_provider, news_provider) -> None:
    topic = callback.data.split(":", 1)[1]

    if topic == "other":
        await state.set_state(FreeformStates.WAITING_FOR_PROMPT)
        await callback.message.edit_text(texts.YARAT_OTHER_PROMPT_ASK)
        await callback.answer()
        return

    if topic and topic not in VALID_CATEGORIES:
        await callback.answer(texts.INVALID_REQUEST, show_alert=True)
        return

    await callback.message.edit_text(texts.GENERATING)
    await callback.answer()
    await _generate_and_send(
        callback.message, settings, llm_provider, news_provider, settings.default_cefr_level, topic or None
    )


@router.callback_query(lambda c: c.data and c.data.startswith("auto_posting:"))
async def on_auto_posting_toggle(callback: CallbackQuery, bot: Bot, settings: Settings) -> None:
    action = callback.data.split(":", 1)[1]
    if action not in ("on", "off"):
        await callback.answer(texts.INVALID_REQUEST, show_alert=True)
        return

    enabled = action == "on"
    async with get_session() as session:
        await SettingsRepository(session).set_auto_posting_enabled(enabled)

    confirm_text = texts.AUTO_POSTING_ENABLED_CONFIRM if enabled else texts.AUTO_POSTING_DISABLED_CONFIRM
    await callback.message.edit_text(
        texts.AUTO_POSTING_STATUS.format(
            status=texts.AUTO_POSTING_ON if enabled else texts.AUTO_POSTING_OFF,
            post_times=settings.post_times,
        ),
        reply_markup=auto_posting_keyboard(enabled),
        parse_mode="HTML",
    )

    actor_id = callback.from_user.id
    actor_name = callback.from_user.full_name or str(actor_id)
    status_label = texts.AUTO_POSTING_ON if enabled else texts.AUTO_POSTING_OFF
    for admin_id in settings.admin_ids:
        if admin_id == actor_id:
            continue
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=texts.AUTO_POSTING_CHANGED_BY_OTHER.format(admin_name=actor_name, status=status_label),
                parse_mode="HTML",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("auto_posting_notify_failed", admin_id=admin_id, error=describe_exception(exc))
    await callback.answer(confirm_text, show_alert=True)
