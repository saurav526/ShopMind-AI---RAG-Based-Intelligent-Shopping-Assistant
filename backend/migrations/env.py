"""Alembic migration environment configured for ShopMind AI SQLAlchemy models."""

# Alembic migration :- IT is a lightweight database migration tool for SQLAlchemy. It allows developers to manage changes to the database schema over time, providing a way to version control and apply incremental updates to the database structure. Alembic is commonly used in Python applications that utilize SQLAlchemy ORM for database interactions, enabling smooth transitions between different versions of the database schema while preserving data integrity.

# SqlAlchemy models :- SQLAlchemy is a popular Python SQL toolkit and Object-Relational Mapping (ORM) library that provides a high-level interface for interacting with relational databases. It allows developers to define database schemas using Python classes (models) and provides an abstraction layer for querying and manipulating data in a database-agnostic manner. SQLAlchemy models represent tables in the database, with attributes corresponding to columns, and support relationships between tables, making it easier to work with complex data structures in Python applications.

from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.core.config import settings
from app.database.session import Base
from app.models import models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
