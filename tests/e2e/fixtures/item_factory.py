"""
Item Factory for E2E Tests

Provides flexible test data creation for bibliographic records and items.
"""

from datetime import date, datetime, timedelta

from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.item import Item


class ItemFactory:
    """Factory for creating test items and bibliographic records."""

    def __init__(self, db_session):
        self.db = db_session
        self._item_counter = 5000
        self._record_counter = 1

    def create_record(self, **kwargs):
        """
        Create a bibliographic record.

        Args:
            title: Book title (default: "Test Book {counter}")
            authors: JSON array of authors (default: '["Test Author"]')
            publisher: Publisher name (default: "Test Publisher")
            publication_year: Year (default: 2024)
            isbn: ISBN (default: None)
            language: Language code (default: "fr")
            medium_type: Medium type (default: "Livre")

        Returns:
            BiblographicRecord: Created record instance
        """
        title = kwargs.get('title', f"Test Book {self._record_counter}")
        self._record_counter += 1

        record = BiblographicRecord(
            title=title,
            authors=kwargs.get('authors', '["Test Author"]'),
            publisher=kwargs.get('publisher', 'Test Publisher'),
            publication_year=kwargs.get('publication_year', 2024),
            isbn=kwargs.get('isbn'),
            language=kwargs.get('language', 'fr'),
            medium_type=kwargs.get('medium_type', 'Livre')
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return record

    def create(self, **kwargs):
        """
        Create an item (automatically creates record if not provided).

        Args:
            item_id: Item barcode (auto-generated if not provided)
            bibliographic_record_id: Record ID (creates new record if not provided)
            status: Item status (default: "available")
            acquisition_date: Acquisition date (default: today)

        Returns:
            Item: Created item instance
        """
        item_id = kwargs.get('item_id', str(self._item_counter))
        self._item_counter += 1

        # Create record if not provided
        record_id = kwargs.get('bibliographic_record_id')
        if not record_id:
            record = self.create_record(
                title=kwargs.get('title', f"Book for Item {item_id}")
            )
            record_id = record.id

        item = Item(
            item_id=item_id,
            bibliographic_record_id=record_id,
            status=kwargs.get('status', 'available'),
            acquisition_date=kwargs.get('acquisition_date', date.today())
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        return item

    def create_batch(self, count=5, **kwargs):
        """Create multiple items."""
        items = []
        for i in range(count):
            item = self.create(**kwargs)
            items.append(item)
        return items

    def create_with_record(self, title="Test Book", **kwargs):
        """Create item with explicit record."""
        record = self.create_record(title=title, **kwargs)
        item = self.create(bibliographic_record_id=record.id, **kwargs)
        return item, record

    def create_on_loan(self, borrower_id, **kwargs):
        """
        Create an item that is currently on loan to a borrower.

        Args:
            borrower_id: ID of borrower who has the item
            checkout_date: When item was checked out (default: today)
            due_date: When item is due (default: 14 days from checkout)
            renewal_count: Number of times renewed (default: 0)
            title: Book title (default: "Test Book")

        Returns:
            tuple: (item, record, transaction)
        """
        # Create item and record
        item, record = self.create_with_record(
            title=kwargs.get('title', 'Test Book'),
            status='on_loan'
        )

        # Calculate dates
        checkout_date = kwargs.get('checkout_date', datetime.now())
        if isinstance(checkout_date, date) and not isinstance(checkout_date, datetime):
            checkout_date = datetime.combine(checkout_date, datetime.min.time())

        due_date = kwargs.get('due_date')
        if not due_date:
            due_date = (checkout_date + timedelta(days=14)).date()

        # Create circulation transaction WITH all required fields
        transaction = CirculationTransaction(
            borrower_id=borrower_id,
            item_id=item.id,
            bibliographic_record_id=record.id,  # REQUIRED
            checkout_date=checkout_date,
            due_date=due_date,
            return_date=kwargs.get('return_date'),
            status=kwargs.get('status', 'active'),
            renewal_count=kwargs.get('renewal_count', 0),  # NOT renewals_count
            checked_out_by=kwargs.get('checked_out_by'),
            notes=kwargs.get('notes')
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return item, record, transaction

    def create_overdue(self, borrower_id, days_overdue=5, **kwargs):
        """
        Create an item that is overdue.

        Args:
            borrower_id: ID of borrower who has the item
            days_overdue: How many days overdue (default: 5)

        Returns:
            tuple: (item, record, transaction)
        """
        checkout_date = datetime.now() - timedelta(days=14 + days_overdue)
        due_date = (checkout_date + timedelta(days=14)).date()

        return self.create_on_loan(
            borrower_id=borrower_id,
            checkout_date=checkout_date,
            due_date=due_date,
            status='overdue',
            **kwargs
        )

    def create_returned(self, borrower_id, **kwargs):
        """
        Create an item that was borrowed and returned.

        Args:
            borrower_id: ID of borrower who borrowed the item
            checkout_date: When item was checked out
            return_date: When item was returned (default: today)

        Returns:
            tuple: (item, record, transaction)
        """
        checkout_date = kwargs.get('checkout_date', datetime.now() - timedelta(days=7))
        return_date = kwargs.get('return_date', datetime.now())

        if isinstance(checkout_date, date) and not isinstance(checkout_date, datetime):
            checkout_date = datetime.combine(checkout_date, datetime.min.time())
        if isinstance(return_date, date) and not isinstance(return_date, datetime):
            return_date = datetime.combine(return_date, datetime.min.time())

        # Create item and record
        item, record = self.create_with_record(
            title=kwargs.get('title', 'Test Book'),
            status='available'
        )

        # Create returned transaction
        transaction = CirculationTransaction(
            borrower_id=borrower_id,
            item_id=item.id,
            bibliographic_record_id=record.id,  # REQUIRED
            checkout_date=checkout_date,
            due_date=(checkout_date + timedelta(days=14)).date(),
            return_date=return_date,
            status='returned',
            renewal_count=kwargs.get('renewal_count', 0),
            checked_out_by=kwargs.get('checked_out_by'),
            returned_by=kwargs.get('returned_by'),
            notes=kwargs.get('notes')
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return item, record, transaction
