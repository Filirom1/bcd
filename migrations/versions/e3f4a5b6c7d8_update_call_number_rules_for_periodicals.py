"""use full titles for periodical call numbers and full series for BD

Revision ID: e3f4a5b6c7d8
Revises: c2d8e4f6a1b3
Create Date: 2026-09-15

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "c2d8e4f6a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _update_rules(value: str | None, downgrade: bool = False) -> str | None:
    if not value:
        return value
    try:
        rules = json.loads(value)
    except (TypeError, ValueError):
        return value
    if not isinstance(rules, list):
        return value

    changed = False
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        medium = rule.get("medium_type")
        shelf = rule.get("shelf_location")
        pattern = rule.get("pattern")
        if medium == "Périodique" and shelf is None:
            if not downgrade and pattern == "":
                rule["pattern"] = "PER {TIT}"
                changed = True
            elif downgrade and pattern == "PER {TIT}":
                rule["pattern"] = ""
                changed = True
    return json.dumps(rules, ensure_ascii=False, separators=(",", ":")) if changed else value


def _apply(downgrade: bool = False) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, catalog_call_number_rules FROM system_settings")
    ).mappings()
    for row in rows:
        updated = _update_rules(row["catalog_call_number_rules"], downgrade=downgrade)
        if updated != row["catalog_call_number_rules"]:
            bind.execute(
                sa.text(
                    "UPDATE system_settings "
                    "SET catalog_call_number_rules = :rules WHERE id = :id"
                ),
                {"rules": updated, "id": row["id"]},
            )


def upgrade() -> None:
    _apply()


def downgrade() -> None:
    _apply(downgrade=True)
