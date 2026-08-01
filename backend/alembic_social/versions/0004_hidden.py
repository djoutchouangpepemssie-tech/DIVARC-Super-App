"""Ajoute les posts masqués (« voir moins ») — Couche 5.

Revision ID: 0004_hidden
Revises: 0003_circles
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0004_hidden"
down_revision = "0003_circles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables["social_hidden_posts"]])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables["social_hidden_posts"]])
