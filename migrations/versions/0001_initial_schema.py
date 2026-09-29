"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_admins_telegram_user_id", "admins", ["telegram_user_id"])

    op.create_table(
        "drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduled_for", sa.String(32), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("cefr_level", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("generation_attempt", sa.Integer(), nullable=False),
        sa.Column("discard_reason", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
    )

    op.create_table(
        "revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "publications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("channel_id", sa.String(64), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "content_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("topic", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "scheduler_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduled_for", sa.String(32), nullable=False, unique=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("drafts.id"), nullable=True),
    )
    op.create_index("ix_scheduler_runs_scheduled_for", "scheduler_runs", ["scheduled_for"])

    op.create_table(
        "category_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_category_usage_category", "category_usage", ["category"])


def downgrade() -> None:
    op.drop_table("category_usage")
    op.drop_table("scheduler_runs")
    op.drop_table("content_history")
    op.drop_table("publications")
    op.drop_table("revisions")
    op.drop_table("drafts")
    op.drop_table("admins")
