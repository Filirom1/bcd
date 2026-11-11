"""SQLite FTS5 index for general bibliographic-record searches."""

from sqlalchemy.engine import Connection

CATALOG_FTS_TABLE = "catalog_search_fts"
CATALOG_SEARCH_FIELDS = (
    "title",
    "subtitle",
    "authors",
    "publisher",
    "collection",
    "keywords",
    "description",
)


def _transliterated_sql(expression: str) -> str:
    return (
        f"replace(replace(replace(replace(COALESCE({expression}, ''), "
        "'œ', 'oe'), 'Œ', 'oe'), 'æ', 'ae'), 'Æ', 'ae')"
    )


def create_catalog_search_index(connection: Connection) -> None:
    """Create and populate the trigram index and its synchronization triggers."""
    exists = connection.exec_driver_sql(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (CATALOG_FTS_TABLE,),
    ).first()
    if exists:
        return

    fields = ", ".join(f'"{field}"' for field in CATALOG_SEARCH_FIELDS)
    connection.exec_driver_sql(
        f"CREATE VIRTUAL TABLE {CATALOG_FTS_TABLE} USING fts5("
        f"{fields}, tokenize='trigram remove_diacritics 1')"
    )

    new_values = ", ".join(_transliterated_sql(f"NEW.{field}") for field in CATALOG_SEARCH_FIELDS)
    updated_fields = ", ".join(CATALOG_SEARCH_FIELDS)
    connection.exec_driver_sql(
        f"""
        CREATE TRIGGER catalog_search_fts_insert
        AFTER INSERT ON bibliographic_record
        BEGIN
            INSERT INTO {CATALOG_FTS_TABLE}(rowid, {fields})
            VALUES (NEW.id, {new_values});
        END
        """
    )
    connection.exec_driver_sql(
        f"""
        CREATE TRIGGER catalog_search_fts_update
        AFTER UPDATE OF id, {updated_fields} ON bibliographic_record
        BEGIN
            DELETE FROM {CATALOG_FTS_TABLE} WHERE rowid = OLD.id;
            INSERT INTO {CATALOG_FTS_TABLE}(rowid, {fields})
            VALUES (NEW.id, {new_values});
        END
        """
    )
    connection.exec_driver_sql(
        f"""
        CREATE TRIGGER catalog_search_fts_delete
        AFTER DELETE ON bibliographic_record
        BEGIN
            DELETE FROM {CATALOG_FTS_TABLE} WHERE rowid = OLD.id;
        END
        """
    )

    select_values = ", ".join(_transliterated_sql(field) for field in CATALOG_SEARCH_FIELDS)
    connection.exec_driver_sql(
        f"""
        INSERT INTO {CATALOG_FTS_TABLE}(rowid, {fields})
        SELECT id, {select_values} FROM bibliographic_record
        """
    )


def drop_catalog_search_index(connection: Connection) -> None:
    """Drop the trigram index and its synchronization triggers."""
    for trigger in (
        "catalog_search_fts_insert",
        "catalog_search_fts_update",
        "catalog_search_fts_delete",
    ):
        connection.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trigger}")
    connection.exec_driver_sql(f"DROP TABLE IF EXISTS {CATALOG_FTS_TABLE}")
