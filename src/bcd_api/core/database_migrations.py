"""Alembic database migration helpers."""

import logging

from .config import settings
from .portable import get_alembic_ini_path

logger = logging.getLogger(__name__)


def upgrade_database(config_settings=None) -> None:
    """Upgrade the configured database schema to the latest Alembic revision.

    Exceptions are intentionally allowed to propagate so callers can decide
    whether a failed migration is fatal or should be handled non-fatally.
    """
    if config_settings is None:
        config_settings = settings

    from alembic.command import upgrade
    from alembic.config import Config

    logger.info("Checking database schema (running migrations)...")

    alembic_ini = get_alembic_ini_path()
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("sqlalchemy.url", config_settings.database_url)
    alembic_cfg.set_main_option("script_location", str(alembic_ini.parent / "migrations"))

    upgrade(alembic_cfg, "head")

    logger.info("Database schema is up to date.")
