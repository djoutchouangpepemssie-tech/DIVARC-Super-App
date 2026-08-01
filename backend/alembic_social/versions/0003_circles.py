"""Ajoute les cercles (listes d'amis) — Couche 4.

Revision ID: 0003_circles
Revises: 0002_bookmarks
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0003_circles"
down_revision = "0002_bookmarks"
branch_labels = None
depends_on = None

_T = ["social_circles", "social_circle_members"]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in _T])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in reversed(_T)])
