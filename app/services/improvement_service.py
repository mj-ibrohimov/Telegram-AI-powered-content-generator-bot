import structlog

from app.ai.base import GenerationContext, LLMProvider
from app.content.validator import validate
from app.database.models import Draft
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from app.errors import describe_exception

logger = structlog.get_logger()


class ImprovementFailedError(Exception):
    pass


class ImprovementService:
    def __init__(
        self,
        llm: LLMProvider,
        draft_repo: DraftRepository,
        history_repo: ContentHistoryRepository,
        timezone: str,
        marketing_ratio: float,
    ):
        self.llm = llm
        self.draft_repo = draft_repo
        self.history_repo = history_repo
        self.timezone = timezone
        self.marketing_ratio = marketing_ratio

    async def improve(self, draft: Draft, instruction: str) -> Draft:
        recent_categories = await self.history_repo.get_recent_category_sequence(limit=5)
        context = GenerationContext(
            scheduled_time=draft.scheduled_for,
            timezone=self.timezone,
            category=draft.category,
            cefr_level=draft.cefr_level,
            recent_categories=recent_categories,
            marketing_ratio=self.marketing_ratio,
        )

        logger.info("improvement_requested", draft_id=draft.id, instruction=instruction)
        try:
            improved = await self.llm.improve_post(draft.content, instruction, context)
        except Exception as exc:  # noqa: BLE001
            detail = describe_exception(exc)
            logger.error("improvement_failed", draft_id=draft.id, error=detail)
            raise ImprovementFailedError(detail) from exc

        validation = validate(improved.title, improved.content)
        if not validation.valid:
            logger.error("improvement_validation_failed", draft_id=draft.id, errors=validation.errors)
            raise ImprovementFailedError("; ".join(validation.errors))

        updated = await self.draft_repo.add_revision(draft.id, improved.content, instruction)
        if updated is not None:
            updated.title = improved.title
            await self.draft_repo.session.commit()
            await self.draft_repo.session.refresh(updated)
        logger.info("draft_improved", draft_id=draft.id)
        return updated
