import structlog

from app.content.generator import ContentGenerator
from app.database.models import Draft
from app.database.repositories.draft_repository import DraftRepository

logger = structlog.get_logger()


class DraftService:
    def __init__(self, generator: ContentGenerator, draft_repo: DraftRepository):
        self.generator = generator
        self.draft_repo = draft_repo

    async def discard_and_regenerate(self, draft_id: int) -> Draft:
        discarded = await self.draft_repo.mark_discarded(draft_id, reason="owner_discarded")
        if discarded is None:
            raise ValueError(f"draft {draft_id} not found")

        logger.info("draft_discarded", draft_id=draft_id)

        new_draft = await self.generator.generate(
            scheduled_for=discarded.scheduled_for,
            scheduled_time=discarded.scheduled_for,
            timezone="",  # informational only for regeneration
            cefr_level=discarded.cefr_level,
            category_override=discarded.category,
            discarded_content=[discarded.content],
        )
        return new_draft
