"""Fil pré-calculé (fan-out on write) — Track A puissance.

Revision ID: 0009_feed_entries
Revises: 0008_feed_seen
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0009_feed_entries"
down_revision = "0008_feed_seen"
branch_labels = None
depends_on = None

_T = ["social_feed_entries"]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in _T])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in reversed(_T)])
