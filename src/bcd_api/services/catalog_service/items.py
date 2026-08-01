"""Item Service (Internal)

Handles business logic for physical items (copies) management.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from ....shared.constants import IDFormat
from ...core.exceptions import ConflictError, NotFoundError, NotFoundException, ValidationError
from ...models.bibliographic_record import BiblographicRecord
from ...models.item import Item
from ...schemas.item import ItemCreate

logger = logging.getLogger(__name__)


def create_item(db: Session, item_data: ItemCreate) -> Item:
    """
    Create a new item (physical copy).
    """
    from ..settings_service import get_settings
    try:
        sys_settings = get_settings(db)
        prefix = sys_settings.item_barcode_prefix
    except Exception:
        prefix = None

    item_id = item_data.item_id.strip()
    if prefix:
        prefix_strip = prefix.strip()
        if prefix_strip and item_id.startswith(prefix_strip):
            item_id = item_id[len(prefix_strip):]

    biblio_record = (
        db.query(BiblographicRecord)
        .filter(BiblographicRecord.id == item_data.bibliographic_record_id)
        .first()
    )
    if not biblio_record:
        from ...core.exceptions import BiblographicRecordNotFoundException
        raise BiblographicRecordNotFoundException(item_data.bibliographic_record_id)

    existing = db.query(Item).filter(Item.item_id == item_id).first()
    if existing:
        from ...core.exceptions import DuplicateItemIDException
        raise DuplicateItemIDException(item_id)

    item_dict = item_data.model_dump()
    item_dict['item_id'] = item_id
    if item_dict.get('acquisition_date') is None:
        item_dict['acquisition_date'] = date.today()
    db_item = Item(**item_dict)
    db.add(db_item)

    biblio_record.total_items += 1

    db.commit()
    db.refresh(db_item)

    logger.info(f"Created item {db_item.item_id} for record {biblio_record.title}")
    return db_item


def get_item(db: Session, item_id: str) -> Item:
    """
    Get item by item_id.
    """
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise NotFoundError("Item", item_id)
    return item


def get_items_for_bibliographic_record(
    db: Session, bibliographic_record_id: int
) -> list[dict]:
    """
    Get all items for a bibliographic record with circulation details.
    """
    from ...models.circulation import CirculationTransaction

    items = (
        db.query(Item)
        .filter(Item.bibliographic_record_id == bibliographic_record_id)
        .all()
    )

    result = []
    for item in items:
        item_dict = {
            "id": item.id,
            "item_id": item.item_id,
            "call_number": item.call_number,
            "shelf_location": item.shelf_location,
            "status": item.status,
            "condition": item.condition,
            "loanable": item.loanable,
            "acquisition_date": item.acquisition_date,
            "funding_source": item.funding_source,
            "current_loan": None
        }

        if item.status == "on_loan":
            active_loan = db.query(CirculationTransaction).filter(
                and_(
                    CirculationTransaction.item_id == item.id,
                    CirculationTransaction.return_date.is_(None)
                )
            ).options(
                joinedload(CirculationTransaction.borrower)
            ).first()

            if active_loan:
                item_dict["current_loan"] = {
                    "borrower_id": active_loan.borrower.borrower_id,
                    "borrower_name": active_loan.borrower.full_name,
                    "due_date": active_loan.due_date.strftime('%d/%m/%Y'),
                    "is_overdue": active_loan.due_date < date.today(),
                    "days_overdue": (date.today() - active_loan.due_date).days if active_loan.due_date < date.today() else 0
                }

        result.append(item_dict)

    return result


def update_item(db: Session, item_id: str, update_data: dict) -> Item:
    """
    Update a single item (US6).
    """
    item = db.query(Item).filter(Item.item_id == item_id).first()

    if not item:
        raise NotFoundException(resource="Item", identifier=item_id)

    if "item_id" in update_data:
        del update_data["item_id"]

    if "acquisition_date" in update_data and isinstance(update_data["acquisition_date"], str):
        try:
            update_data["acquisition_date"] = datetime.strptime(update_data["acquisition_date"], "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Invalid acquisition_date format: {update_data['acquisition_date']}")
            del update_data["acquisition_date"]

    for field, value in update_data.items():
        if hasattr(item, field):
            setattr(item, field, value)

    db.commit()
    db.refresh(item)

    logger.info(f"Updated item {item_id} (barcode: {item.item_id})")

    return item


def _check_item_has_active_loan(db: Session, item: Item) -> Optional[dict]:
    """
    Check if an item is currently on loan.
    """
    from ...models.circulation import CirculationTransaction

    active_loan = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item.id,
            CirculationTransaction.return_date.is_(None)
        )
    ).first()

    if active_loan:
        return {
            "borrower_name": active_loan.borrower.full_name,
            "due_date": active_loan.due_date
        }
    return None


def delete_item(db: Session, item_id: str) -> None:
    """
    Delete an item by barcode.
    """
    item = db.query(Item).filter(Item.item_id == item_id).first()

    if not item:
        raise NotFoundException(resource="Item", identifier=item_id)

    active_loan_info = _check_item_has_active_loan(db, item)
    if active_loan_info:
        from ...core.exceptions import ItemHasActiveLoanException
        raise ItemHasActiveLoanException(
            item_id=item_id,
            borrower_name=active_loan_info["borrower_name"],
            due_date=active_loan_info["due_date"]
        )

    biblio_record = db.query(BiblographicRecord).filter(
        BiblographicRecord.id == item.bibliographic_record_id
    ).first()

    db.delete(item)

    if biblio_record and biblio_record.total_items > 0:
        biblio_record.total_items -= 1

    db.commit()

    logger.info(f"Deleted item {item_id}")


def get_available_item_ids(
    db: Session,
    count: int = 30,
    start_from: Optional[str] = None,
    contiguous: bool = True
) -> Dict[str, Any]:
    """
    Generate a list of available item IDs that are not currently in use.
    """
    from ..settings_service import get_settings

    settings = get_settings(db)

    if count < 1 or count > 1000:
        raise ValueError("Count must be between 1 and 1000")

    if settings.id_format == IDFormat.NUMERIC.value:
        rows = db.query(Item.item_id).all()
        used_ids = set()
        for (iid,) in rows:
            try:
                n = int(iid)
                if n > 0:
                    used_ids.add(n)
            except (ValueError, TypeError):
                pass

        if start_from:
            try:
                start_point = int(start_from)
            except ValueError:
                raise ValueError(f"Invalid start_from value for numeric format: {start_from}")
        else:
            start_point = 1

        ids = []
        candidate = start_point

        if contiguous:
            while len(ids) < count:
                all_free = True
                for offset in range(count - len(ids)):
                    if (candidate + offset) in used_ids:
                        all_free = False
                        candidate = candidate + offset + 1
                        break

                if all_free:
                    for offset in range(count - len(ids)):
                        ids.append(str(candidate + offset))
                    break
        else:
            while len(ids) < count:
                if candidate not in used_ids:
                    ids.append(str(candidate))
                candidate += 1

        return {
            "start_id": ids[0],
            "end_id": ids[-1],
            "ids": ids,
            "count": count,
            "id_format": settings.id_format,
            "contiguous": contiguous
        }

    else:
        raise NotImplementedError(
            "Alphanumeric ID generation not yet implemented. "
            "Please set id_format to 'numeric' in system settings."
        )
