"""Schéma initial du contexte social (profiles, posts, media, reactions, comments, edges).

Revision ID: 0001_initial_social
Revises:
Create Date: 2026-08-01

Crée le schéma depuis les modèles SQLAlchemy (les types résolvent JSONB sur PostgreSQL,
JSON sur SQLite). Réversible via drop_all.
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401 (enregistre les tables)
from app.social.adapters.persistence.db import Base

revision = "0001_initial_social"
down_revision = None
branch_labels = None
depends_on = None

# Tables de cette migration (pour un downgrade ciblé)
_TABLES = ["social_comments", "social_reactions", "social_post_media",
           "social_posts", "social_edges", "social_profiles"]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[t] for t in reversed(_TABLES)])


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=[Base.metadata.tables[t] for t in _TABLES])
