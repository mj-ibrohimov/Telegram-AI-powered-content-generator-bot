import structlog

from app.ai.base import GeneratedPost, GenerationContext, LLMProvider, QualityReview
from app.errors import describe_exception
from app.content.duplicate_detector import DuplicateDetector
from app.content.strategy import ContentStrategy
from app.content.validator import validate
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from app.news.base import NewsProvider

logger = structlog.get_logger()

# How many times, per outer generation attempt, we ask the LLM to fix its own
# flagged quality issues before giving up on that attempt and regenerating
# from scratch. Kept small and separate from max_attempts so a review loop
# can never spiral into unbounded LLM calls.
MAX_TARGETED_FIX_ROUNDS = 2


class GenerationFailedError(Exception):
    pass


class ContentGenerator:
    def __init__(
        self,
        llm: LLMProvider,
        strategy: ContentStrategy,
        duplicate_detector: DuplicateDetector,
        draft_repo: DraftRepository,
        history_repo: ContentHistoryRepository,
        news_provider: NewsProvider | None = None,
        max_attempts: int = 3,
    ):
        self.llm = llm
        self.strategy = strategy
        self.duplicate_detector = duplicate_detector
        self.draft_repo = draft_repo
        self.history_repo = history_repo
        self.news_provider = news_provider
        self.max_attempts = max_attempts

    async def _build_context(
        self,
        scheduled_time: str,
        timezone: str,
        cefr_level: str,
        category: str,
        discarded_content: list[str] | None = None,
        custom_instruction: str | None = None,
    ) -> GenerationContext:
        recent = await self.draft_repo.get_recent_by_category(category, limit=5)
        recent_categories = await self.history_repo.get_recent_category_sequence(limit=5)

        news_items = None
        if category == "news" and self.news_provider is not None:
            items = await self.news_provider.search("Deutschland")
            news_items = [
                {
                    "title": i.title,
                    "summary": i.summary,
                    "source": i.source,
                    "source_url": i.source_url,
                    "publication_date": i.publication_date,
                }
                for i in items
            ]

        return GenerationContext(
            scheduled_time=scheduled_time,
            timezone=timezone,
            category=category,
            cefr_level=cefr_level,
            recent_posts=[d.content[:300] for d in recent],
            discarded_posts=discarded_content or [],
            recent_categories=recent_categories,
            marketing_ratio=self.strategy.marketing_ratio,
            news_items=news_items,
            custom_instruction=custom_instruction,
        )

    async def _review_and_fix(
        self,
        post: GeneratedPost,
        context: GenerationContext,
        attempt: int,
    ) -> tuple[GeneratedPost, str | None]:
        """AI quality review (grammar, naturalness, translation accuracy,
        meaning preservation, CEFR fit, usefulness, category adherence,
        factual accuracy). When only minor issues are found, the post is
        accepted as-is. When major issues are found, asks the LLM to fix
        only those issues (targeted regeneration via improve_post, not a
        full restart) and re-reviews, up to MAX_TARGETED_FIX_ROUNDS times.

        Returns (post, error) -- error is None if the post is now acceptable,
        or a description of the unresolved issues if it still isn't after
        exhausting the fix rounds (the caller then falls back to a full
        regeneration attempt).
        """
        current = post
        review: QualityReview = await self.llm.review_post(current, context)

        for fix_round in range(1, MAX_TARGETED_FIX_ROUNDS + 1):
            if review.valid and not review.has_major_issues:
                if review.issues:
                    logger.info(
                        "quality_review_passed_with_minor_issues",
                        attempt=attempt,
                        issues=[f"{i.field}: {i.problem}" for i in review.issues],
                    )
                return current, None

            major_issues = [i for i in review.issues if i.severity == "major"]
            logger.warning(
                "quality_review_found_major_issues",
                attempt=attempt,
                fix_round=fix_round,
                issues=[f"{i.field}: {i.problem}" for i in major_issues],
            )

            if not review.fix_instruction:
                # The review flagged major issues but gave nothing actionable
                # to fix -- no point calling improve_post with no instruction.
                break

            current = await self.llm.improve_post(current.content, review.fix_instruction, context)
            review = await self.llm.review_post(current, context)

        if review.valid and not review.has_major_issues:
            return current, None

        remaining = [i for i in review.issues if i.severity == "major"] or review.issues
        summary = "; ".join(f"{i.field}: {i.problem}" for i in remaining) or "quality review failed"
        return current, f"quality review: {summary}"

    async def generate(
        self,
        scheduled_for: str,
        scheduled_time: str,
        timezone: str,
        cefr_level: str,
        category_override: str | None = None,
        discarded_content: list[str] | None = None,
        custom_instruction: str | None = None,
    ):
        if custom_instruction:
            category = "custom"
        else:
            recent_categories = await self.history_repo.get_recent_category_sequence(limit=5)
            category = self.strategy.select_category(
                scheduled_time=scheduled_time,
                recent_categories=recent_categories,
                category_override=category_override,
            )

        if category == "news" and self.news_provider is None:
            category = "culture"

        existing_for_dup_check = [d.content for d in await self.draft_repo.get_recent_by_category(category, limit=10)]

        last_error: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            context = await self._build_context(
                scheduled_time=scheduled_time,
                timezone=timezone,
                cefr_level=cefr_level,
                category=category,
                discarded_content=discarded_content,
                custom_instruction=custom_instruction,
            )

            try:
                post: GeneratedPost = await self.llm.generate_post(context)
            except Exception as exc:  # noqa: BLE001 - log and retry within attempt budget
                error_detail = describe_exception(exc)
                logger.warning("generation_attempt_failed", attempt=attempt, category=category, error=error_detail)
                last_error = error_detail
                continue

            validation = validate(post.title, post.content)
            if not validation.valid:
                logger.warning("generation_validation_failed", attempt=attempt, errors=validation.errors)
                last_error = "; ".join(validation.errors)
                continue

            try:
                post, quality_error = await self._review_and_fix(post, context, attempt)
            except Exception as exc:  # noqa: BLE001 - the quality review is a required gate; if it can't
                # run at all, this attempt did not pass validation and must be retried like any other failure.
                error_detail = describe_exception(exc)
                logger.warning("quality_review_unavailable", attempt=attempt, category=category, error=error_detail)
                last_error = f"quality review unavailable: {error_detail}"
                continue

            if quality_error is not None:
                last_error = quality_error
                continue

            if self.duplicate_detector.is_duplicate(post.content, existing_for_dup_check):
                logger.warning("generation_duplicate_detected", attempt=attempt, category=category)
                last_error = "duplicate content detected"
                continue

            draft = await self.draft_repo.create(
                scheduled_for=scheduled_for,
                category=category,
                cefr_level=cefr_level,
                title=post.title,
                content=post.content,
                generation_attempt=attempt,
            )
            await self.history_repo.record_category_usage(category)
            logger.info("draft_created", draft_id=draft.id, category=category, attempt=attempt)
            return draft

        logger.error("generation_failed_all_attempts", category=category, error=last_error)
        raise GenerationFailedError(last_error or "unknown error")
