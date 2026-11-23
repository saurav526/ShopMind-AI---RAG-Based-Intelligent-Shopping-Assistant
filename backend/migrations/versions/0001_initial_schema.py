"""Initial ShopMind AI relational schema migration (11 tables)

# this explain the initial migration script for the ShopMind AI application, which defines the relational database schema consisting of 11 tables. The migration uses Alembic to create the necessary tables and relationships in the database, including users, products, product categories, conversations, messages, user preferences, evaluation runs and results, security events, ingestion jobs, and audit logs. The script provides both upgrade and downgrade functions to apply or revert the schema changes as needed.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-23
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.database.session import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.database.session import Base
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
