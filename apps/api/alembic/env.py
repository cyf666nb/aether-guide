# SCORE-IMPACT: Controlled schema migrations and rollback readiness.
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from aether_api.config import get_settings
from aether_api.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# If the caller (pytest, Makefile) hasn't set the URL explicitly, fall back to settings.
if not config.get_main_option("sqlalchemy.url"):
    settings = get_settings()
    config.set_main_option("sqlalchemy.url", settings.database_url)


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


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Supports both sync (sqlite://) and async (sqlite+aiosqlite://) URLs so the
    regression test suite and the make migrate target can share one env.py.
    """
    section = config.get_section(config.config_ini_section, {})
    url = section.get("sqlalchemy.url", "")

    if "+aiosqlite" in url or "+asyncpg" in url or "+asyncmy" in url:
        import asyncio

        async def _run_async() -> None:
            connectable = async_engine_from_config(
                section,
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)
            await connectable.dispose()

        asyncio.run(_run_async())
    else:
        from sqlalchemy import engine_from_config

        connectable = engine_from_config(
            section,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            do_run_migrations(connection)
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
