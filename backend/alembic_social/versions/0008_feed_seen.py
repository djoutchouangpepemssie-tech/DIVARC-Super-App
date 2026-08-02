"""État « déjà vu » du fil (ranking multi-étages) — Couche perf B.

Revision ID: 0008_feed_seen
Revises: 0007_moderation
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0008_feed_seen"
down_revision = "0007_moderation"
branch_labels = None
depends_on = None

_T = ["social_feed_seen"]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in _T])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in reversed(_T)])
