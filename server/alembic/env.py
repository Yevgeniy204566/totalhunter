"""
env.py — Alembic migration environment (async).

Использует asyncpg + run_sync для применения миграций.
DATABASE_URL из переменной окружения — код не меняется между окружениями.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# server/ в путь — чтобы импортировать models.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base  # noqa: E402

config = context.config

# DATABASE_URL из env (asyncpg)
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://hunter:hunter@localhost:5432/totalhunter",
)
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Offline: генерирует SQL без подключения к БД.
    Команда: DATABASE_URL=... alembic upgrade head --sql > migration.sql
    Полезно для ревью перед деплоем.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Синхронный шаг внутри async-соединения — требование Alembic."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async online: создаём engine, прогоняем миграции через run_sync."""
    connectable = create_async_engine(database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
