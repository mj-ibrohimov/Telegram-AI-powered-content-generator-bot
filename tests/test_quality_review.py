import pytest

from app.ai.base import GeneratedPost, QualityIssue, QualityReview
from app.content.duplicate_detector import DuplicateDetector
from app.content.generator import ContentGenerator, GenerationFailedError
from app.content.strategy import ContentStrategy
from app.database.repositories.content_history_repository import ContentHistoryRepository
from app.database.repositories.draft_repository import DraftRepository
from tests.fakes import FakeLLMProvider


def _make_generator(llm, draft_repo, history_repo, max_attempts=3):
    return ContentGenerator(
        llm=llm,
        strategy=ContentStrategy(),
        duplicate_detector=DuplicateDetector(),
        draft_repo=draft_repo,
        history_repo=history_repo,
        max_attempts=max_attempts,
    )


@pytest.mark.asyncio
async def test_clean_review_passes_through_unchanged(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    llm = FakeLLMProvider(
        posts=[GeneratedPost(title="T", content="A" * 100)],
        reviews=[QualityReview(valid=True, issues=[])],
    )
    generator = _make_generator(llm, draft_repo, history_repo)

    draft = await generator.generate(
        scheduled_for="2026-09-29_08:00",
        scheduled_time="08:00",
        timezone="Asia/Tashkent",
        cefr_level="Mixed",
        category_override="daily_phrases",
    )

    assert draft.content == "A" * 100
    assert len(llm.improve_calls) == 0
    assert len(llm.review_calls) == 1


@pytest.mark.asyncio
async def test_minor_issues_do_not_trigger_a_fix(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    llm = FakeLLMProvider(
        posts=[GeneratedPost(title="T", content="A" * 100)],
        reviews=[
            QualityReview(
                valid=True,
                issues=[QualityIssue(field="naturalness", problem="slightly stiff phrasing", severity="minor")],
            )
        ],
    )
    generator = _make_generator(llm, draft_repo, history_repo)

    draft = await generator.generate(
        scheduled_for="2026-09-29_08:00",
        scheduled_time="08:00",
        timezone="Asia/Tashkent",
        cefr_level="Mixed",
        category_override="daily_phrases",
    )

    assert draft.content == "A" * 100
    assert len(llm.improve_calls) == 0


@pytest.mark.asyncio
async def test_major_issue_triggers_targeted_fix_not_full_regeneration(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    llm = FakeLLMProvider(
        posts=[GeneratedPost(title="T", content="A" * 100)],
        reviews=[
            QualityReview(
                valid=False,
                issues=[QualityIssue(field="grammar", problem="wrong case used", severity="major")],
                fix_instruction="Fix the grammar: use accusative case in sentence 2.",
            ),
            QualityReview(valid=True, issues=[]),
        ],
    )
    generator = _make_generator(llm, draft_repo, history_repo)

    draft = await generator.generate(
        scheduled_for="2026-09-29_08:00",
        scheduled_time="08:00",
        timezone="Asia/Tashkent",
        cefr_level="Mixed",
        category_override="daily_phrases",
    )

    # improve_post was called (targeted fix), generate_post was called only once (no full restart)
    assert llm.call_count == 1
    assert len(llm.improve_calls) == 1
    assert llm.improve_calls[0][1] == "Fix the grammar: use accusative case in sentence 2."
    assert draft.content == "A" * 100 + " Fix the grammar: use accusative case in sentence 2."


@pytest.mark.asyncio
async def test_review_with_no_fix_instruction_falls_back_to_full_regeneration(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    llm = FakeLLMProvider(
        posts=[
            GeneratedPost(title="T1", content="A" * 100),
            GeneratedPost(title="T2", content="B" * 100),
        ],
        reviews=[
            QualityReview(
                valid=False,
                issues=[QualityIssue(field="factual_accuracy", problem="invented a fact", severity="major")],
                fix_instruction=None,
            ),
            QualityReview(valid=True, issues=[]),
        ],
    )
    generator = _make_generator(llm, draft_repo, history_repo, max_attempts=3)

    draft = await generator.generate(
        scheduled_for="2026-09-29_08:00",
        scheduled_time="08:00",
        timezone="Asia/Tashkent",
        cefr_level="Mixed",
        category_override="daily_phrases",
    )

    # No fix_instruction -> targeted fix skipped -> next outer attempt regenerates from scratch
    assert llm.call_count == 2
    assert len(llm.improve_calls) == 0
    assert draft.content == "B" * 100


@pytest.mark.asyncio
async def test_persistent_major_issues_exhaust_fix_rounds_and_regenerate(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)
    always_bad_review = QualityReview(
        valid=False,
        issues=[QualityIssue(field="cefr_level", problem="too advanced for A2", severity="major")],
        fix_instruction="Simplify to A2 level.",
    )
    llm = FakeLLMProvider(
        posts=[
            GeneratedPost(title="T1", content="A" * 100),
            GeneratedPost(title="T2", content="B" * 100),
        ],
        reviews=[always_bad_review, always_bad_review, always_bad_review, QualityReview(valid=True, issues=[])],
    )
    generator = _make_generator(llm, draft_repo, history_repo, max_attempts=3)

    draft = await generator.generate(
        scheduled_for="2026-09-29_08:00",
        scheduled_time="08:00",
        timezone="Asia/Tashkent",
        cefr_level="A2",
        category_override="daily_phrases",
    )

    # First attempt: generate + 2 fix rounds (both still bad) -> attempt fails, retried
    # Second attempt: fresh generate_post -> clean review -> succeeds
    assert llm.call_count == 2
    assert draft.content == "B" * 100


@pytest.mark.asyncio
async def test_review_unavailable_is_treated_as_failed_attempt_and_retried(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)

    class FlakyReviewProvider(FakeLLMProvider):
        async def review_post(self, post, context):
            if len(self.review_calls) == 0:
                self.review_calls.append(post)
                raise RuntimeError("review LLM timed out")
            return await super().review_post(post, context)

    llm = FlakyReviewProvider(
        posts=[
            GeneratedPost(title="T1", content="A" * 100),
            GeneratedPost(title="T2", content="B" * 100),
        ],
    )
    generator = _make_generator(llm, draft_repo, history_repo, max_attempts=3)

    draft = await generator.generate(
        scheduled_for="2026-09-29_08:00",
        scheduled_time="08:00",
        timezone="Asia/Tashkent",
        cefr_level="Mixed",
        category_override="daily_phrases",
    )

    assert llm.call_count == 2
    assert draft.content == "B" * 100


@pytest.mark.asyncio
async def test_review_unavailable_on_every_attempt_raises_generation_failed(session):
    draft_repo = DraftRepository(session)
    history_repo = ContentHistoryRepository(session)

    class AlwaysFlakyReviewProvider(FakeLLMProvider):
        async def review_post(self, post, context):
            raise RuntimeError("review LLM down")

    llm = AlwaysFlakyReviewProvider(posts=[GeneratedPost(title="T", content="A" * 100)])
    generator = _make_generator(llm, draft_repo, history_repo, max_attempts=2)

    with pytest.raises(GenerationFailedError) as exc_info:
        await generator.generate(
            scheduled_for="2026-09-29_08:00",
            scheduled_time="08:00",
            timezone="Asia/Tashkent",
            cefr_level="Mixed",
            category_override="daily_phrases",
        )

    assert "quality review unavailable" in str(exc_info.value)
