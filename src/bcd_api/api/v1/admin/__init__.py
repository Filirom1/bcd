"""Admin API endpoints.

The admin API is split by responsibility while this package keeps the
original ``src.bcd_api.api.v1.admin`` import surface intact.
"""

from fastapi import APIRouter

from ....core import mdns as mdns_module
from ....core.config import settings as app_settings
from ....schemas.system_settings import SystemSettingsUpdate
from ....services import (
    admin_service,
    borrower_service,
    inventory_service,
)
from ....services import (
    catalog as catalog_service,
)
from ....services.admin import archive as archive_service
from ....services.admin import backup as backup_service
from ....services.admin import settings as settings_service
from . import archive, backups, bulk, covers, maintenance, settings, shelf_suggestion
from .archive import (
    archive_transactions,
    get_archive_stats,
    get_archived_transactions,
    health_check,
)
from .backups import (
    cleanup_old_backups_endpoint,
    create_backup_endpoint,
    download_backup_endpoint,
    import_backup_endpoint,
    list_backups_endpoint,
    restore_backup_endpoint,
    verify_backup_endpoint,
)
from .bulk import (
    bulk_change_class_endpoint,
    bulk_change_role_endpoint,
    bulk_delete_borrowers_endpoint,
    bulk_delete_records_endpoint,
    bulk_edit_borrowers_endpoint,
    bulk_edit_records_endpoint,
    delete_orphan_records_endpoint,
    get_orphan_records_endpoint,
)
from .covers import (
    _download_lock,
    _download_missing_covers_task,
    _download_status,
    backfill_covers,
    cancel_download_missing_covers,
    get_download_missing_covers_status,
    start_download_missing_covers,
)
from .maintenance import set_acquisition_dates_from_publication_year
from .settings import (
    SettingsUpdate,
    get_env_file_content,
    get_settings,
    reset_settings,
    update_env_file_content,
    update_settings,
)
from .shelf_suggestion import get_shelf_suggestion_status, train_shelf_suggestion

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(settings.router)
router.include_router(backups.router)
router.include_router(archive.router)
router.include_router(bulk.router)
router.include_router(covers.router)
router.include_router(maintenance.router)
router.include_router(shelf_suggestion.router)

__all__ = [
    "router",
    "app_settings",
    "mdns_module",
    "admin_service",
    "borrower_service",
    "catalog_service",
    "inventory_service",
    "settings_service",
    "archive_service",
    "backup_service",
    "SettingsUpdate",
    "SystemSettingsUpdate",
    "get_env_file_content",
    "update_env_file_content",
    "get_settings",
    "update_settings",
    "reset_settings",
    "create_backup_endpoint",
    "list_backups_endpoint",
    "restore_backup_endpoint",
    "download_backup_endpoint",
    "import_backup_endpoint",
    "cleanup_old_backups_endpoint",
    "verify_backup_endpoint",
    "get_archive_stats",
    "archive_transactions",
    "get_archived_transactions",
    "health_check",
    "bulk_change_class_endpoint",
    "bulk_change_role_endpoint",
    "bulk_delete_borrowers_endpoint",
    "bulk_edit_records_endpoint",
    "bulk_delete_records_endpoint",
    "get_orphan_records_endpoint",
    "delete_orphan_records_endpoint",
    "bulk_edit_borrowers_endpoint",
    "backfill_covers",
    "_download_lock",
    "_download_status",
    "_download_missing_covers_task",
    "start_download_missing_covers",
    "get_download_missing_covers_status",
    "cancel_download_missing_covers",
    "set_acquisition_dates_from_publication_year",
    "get_shelf_suggestion_status",
    "train_shelf_suggestion",
]
