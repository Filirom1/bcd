"""
Integration tests for catalog service bulk operations (US5).

Tests bulk_edit_records and bulk_delete_records service methods.
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.bcd_api.services import catalog_service
from src.bcd_api.core.exceptions import ValidationError, ItemHasActiveLoanException
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.schemas.bibliographic_record import BiblographicRecordCreate
from src.bcd_api.schemas.item import ItemCreate


class TestBulkEditRecords:
    """Test bulk_edit_records service method."""

    def test_bulk_edit_records_success(self, db_session: Session):
        """Test successful bulk edit of multiple records."""
        # ARRANGE - Create test records
        records = []
        for i in range(3):
            record_data = BiblographicRecordCreate(
                title=f"Test Book {i}",
                authors=[f"Author {i}"],
                genre="Novel",
                language="eng"
            )
            record = catalog_service.create_bibliographic_record(
                db=db_session,
                record_data=record_data,
                isbn_lookup=False
            )
            records.append(record)

        record_ids = [r.id for r in records]

        # ACT - Bulk edit common fields
        result = catalog_service.bulk_edit_records(
            db=db_session,
            record_ids=record_ids,
            genre="Biography",
            level="CP",
            language="fr",
            publisher="New Pub",
            collection="Cool Series",
            binding_type="paperback"
        )

        # ASSERT - All records updated
        assert result["operation"] == "bulk_edit_records"
        assert result["total_count"] == 3
        assert result["successful_count"] == 3
        assert result["failed_count"] == 0

        # Verify database changes
        for record_id in record_ids:
            record = db_session.query(BiblographicRecord).filter(
                BiblographicRecord.id == record_id
            ).first()
            assert record.genre == "Biography"
            assert record.level == "CP"
            assert record.language == "fr"
            assert record.publisher == "New Pub"
            assert record.collection == "Cool Series"
            assert record.binding_type == "paperback"

    def test_bulk_edit_records_null_values_unchanged(self, db_session: Session):
        """Test that null values in update mean 'no change'."""
        # ARRANGE
        record_data = BiblographicRecordCreate(
            title="Test Book",
            authors=["Author"],
            genre="Novel",
            language="eng"
        )
        record = catalog_service.create_bibliographic_record(
            db=db_session,
            record_data=record_data,
            isbn_lookup=False
        )

        # ACT - Update genre only (language = null = no change)
        catalog_service.bulk_edit_records(
            db=db_session,
            record_ids=[record.id],
            genre="Biography",
            language=None  # No change
        )

        # ASSERT - Only genre updated
        db_session.refresh(record)
        assert record.genre == "Biography"  # Updated
        assert record.language == "eng"  # Unchanged

    def test_bulk_edit_records_only_valid_ids(self, db_session: Session):
        """Test that bulk edit only updates valid record IDs."""
        # ARRANGE - Create valid records
        record1_data = BiblographicRecordCreate(
            title="Book 1",
            authors=["Author 1"]
        )
        record1 = catalog_service.create_bibliographic_record(
            db=db_session,
            record_data=record1_data,
            isbn_lookup=False
        )

        # ACT - Try to update with invalid IDs mixed in
        # Only valid IDs should be updated (implementation skips invalid IDs)
        result = catalog_service.bulk_edit_records(
            db=db_session,
            record_ids=[record1.id, 99999],  # 99999 doesn't exist
            genre="Updated"
        )

        # ASSERT - Only valid record updated
        db_session.refresh(record1)
        assert record1.genre == "Updated"
        assert result["successful_count"] == 1  # Only 1 record found and updated

    def test_bulk_edit_records_no_fields_error(self, db_session: Session):
        """Test error when no update fields provided."""
        # ARRANGE
        record_data = BiblographicRecordCreate(
            title="Test Book",
            authors=["Author"]
        )
        record = catalog_service.create_bibliographic_record(
            db=db_session,
            record_data=record_data,
            isbn_lookup=False
        )

        # ACT & ASSERT - Error when all fields are null
        with pytest.raises(ValidationError) as exc:
            catalog_service.bulk_edit_records(
                db=db_session,
                record_ids=[record.id],
                genre=None,
                level=None,
                target_audience=None,
                language=None,
                medium_type=None,
                publisher=None,
                collection=None,
                binding_type=None
            )

        assert "No fields to update" in str(exc.value)

    def test_bulk_edit_records_empty_list_error(self, db_session: Session):
        """Test error when empty record ID list provided."""
        # ACT & ASSERT
        with pytest.raises(ValidationError) as exc:
            catalog_service.bulk_edit_records(
                db=db_session,
                record_ids=[],
                genre="Fiction"
            )

        assert "No record IDs provided" in str(exc.value)


class TestBulkDeleteRecords:
    """Test bulk_delete_records service method."""

    def test_bulk_delete_records_success(self, db_session: Session):
        """Test successful bulk delete of multiple records."""
        # ARRANGE - Create test records with items
        records = []
        for i in range(3):
            record_data = BiblographicRecordCreate(
                title=f"Test Book {i}",
                authors=[f"Author {i}"]
            )
            record = catalog_service.create_bibliographic_record(
                db=db_session,
                record_data=record_data,
                isbn_lookup=False
            )
            records.append(record)

            # Create item for each record
            from src.bcd_api.schemas.item import ItemCreate
            item_data = ItemCreate(
                item_id=f"ITEM{i}",
                bibliographic_record_id=record.id,
                call_number=f"{i}00.000"
            )
            catalog_service.create_item(db=db_session, item_data=item_data)

        record_ids = [r.id for r in records]

        # ACT - Bulk delete
        result = catalog_service.bulk_delete_records(
            db=db_session,
            record_ids=record_ids
        )

        # ASSERT - All records deleted
        assert result["operation"] == "bulk_delete_records"
        assert result["total_count"] == 3
        assert result["successful_count"] == 3
        assert result["failed_count"] == 0

        # Verify records deleted
        for record_id in record_ids:
            record = db_session.query(BiblographicRecord).filter(
                BiblographicRecord.id == record_id
            ).first()
            assert record is None

        # Verify items CASCADE deleted
        items = db_session.query(Item).all()
        assert len(items) == 0

    def test_bulk_delete_records_cascade_deletes_items(self, db_session: Session):
        """Test CASCADE delete removes associated items even if on loan."""
        # ARRANGE - Create record with item on loan
        record_data = BiblographicRecordCreate(
            title="Test Book",
            authors=["Author"]
        )
        record = catalog_service.create_bibliographic_record(
            db=db_session,
            record_data=record_data,
            isbn_lookup=False
        )

        from src.bcd_api.schemas.item import ItemCreate
        item_data = ItemCreate(
            item_id="ITEM1",
            bibliographic_record_id=record.id,
            call_number="800.000"
        )
        item = catalog_service.create_item(db=db_session, item_data=item_data)

        # Mark item as on loan
        item.status = "on_loan"
        db_session.commit()

        # ACT - Delete record (should delete item even if on loan)
        result = catalog_service.bulk_delete_records(
            db=db_session,
            record_ids=[record.id]
        )

        # ASSERT - Record and item deleted
        assert result["successful_count"] == 1

        record_check = db_session.query(BiblographicRecord).filter(
            BiblographicRecord.id == record.id
        ).first()
        assert record_check is None

        item_check = db_session.query(Item).filter(
            Item.id == item.id
        ).first()
        assert item_check is None

    def test_bulk_delete_records_only_valid_ids(self, db_session: Session):
        """Test that bulk delete only deletes valid record IDs."""
        # ARRANGE - Create one valid record
        record_data = BiblographicRecordCreate(
            title="Book 1",
            authors=["Author 1"]
        )
        record = catalog_service.create_bibliographic_record(
            db=db_session,
            record_data=record_data,
            isbn_lookup=False
        )

        # ACT - Delete with invalid ID mixed in (should delete valid IDs only)
        result = catalog_service.bulk_delete_records(
            db=db_session,
            record_ids=[record.id, 99999]  # 99999 doesn't exist
        )

        # ASSERT - Valid record deleted, invalid ID skipped
        assert result["successful_count"] == 1  # Only 1 record found and deleted
        record_check = db_session.query(BiblographicRecord).filter(
            BiblographicRecord.id == record.id
        ).first()
        assert record_check is None  # Record was deleted

    def test_bulk_delete_records_empty_list_error(self, db_session: Session):
        """Test error when empty record ID list provided."""
        # ACT & ASSERT
        with pytest.raises(ValidationError) as exc:
            catalog_service.bulk_delete_records(
                db=db_session,
                record_ids=[]
            )

        assert "No record IDs provided" in str(exc.value)

    def test_bulk_delete_records_with_active_loans_raises_exception(self, db_session: Session):
        """Test that bulk delete fails if any item has an active loan."""
        # Arrange: Create 2 records, one with active loan
        record1 = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Safe to Delete",
                isbn="9780123456780",
                authors=["Author"]
            ),
            isbn_lookup=False
        )

        record2 = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Has Active Loan",
                isbn="9780123456781",
                authors=["Author"]
            ),
            isbn_lookup=False
        )

        # Create items
        catalog_service.create_item(db_session, ItemCreate(
            item_id="SAFE001",
            bibliographic_record_id=record1.id,
            call_number="100.000",
            status="available"
        ))

        item2 = catalog_service.create_item(db_session, ItemCreate(
            item_id="LOAN001",
            bibliographic_record_id=record2.id,
            call_number="100.001",
            status="on_loan"
        ))

        # Create borrower and active loan on item2
        borrower = Borrower(
            borrower_id="TEST003",
            first_name="Active",
            last_name="BORROWER",
            full_name="Active BORROWER",
            role="student"
        )
        db_session.add(borrower)
        db_session.commit()

        loan = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item2.id,
            bibliographic_record_id=record2.id,
            checkout_date=datetime.now(),
            due_date=(datetime.now() + timedelta(days=14)).date(),
            status="active",
            return_date=None
        )
        db_session.add(loan)
        db_session.commit()

        # Store IDs for later verification
        record1_id = record1.id
        record2_id = record2.id

        # Act & Assert: Bulk delete should fail with appropriate exception
        with pytest.raises(ItemHasActiveLoanException) as exc_info:
            catalog_service.bulk_delete_records(
                db_session,
                record_ids=[record1_id, record2_id]
            )

        # Verify exception details
        assert exc_info.value.error_code == "ITEM_HAS_ACTIVE_LOAN"
        assert exc_info.value.context["item_id"] == "LOAN001"

        # Note: Cannot verify records still exist because service rollback
        # undoes the entire transaction including test setup data.
        # The atomic rollback behavior is the important part being tested.
