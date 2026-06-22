"""Integration tests for Dublin Core CSV import functionality."""

import csv
import json
from io import StringIO

from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.services.dublin_core_import import import_dublin_core_csv


class TestDublinCoreImport:
    """Test Dublin Core CSV import functionality."""

    def test_import_basic_dublin_core_csv(self, db_session):
        """Import basic Dublin Core CSV with all required fields."""
        # Arrange
        csv_content = """dc.title,dc.identifier,dc.creator,dc.type
Stuart Little,isbn:2211056466,"White, E.B.",Livre
Les Misérables,isbn:9782070360024,"Hugo, Victor",Livre"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 2
        assert result.items_created == 2
        assert result.records_skipped == 0
        assert len(result.errors) == 0

        # Verify records in database
        records = db_session.query(BiblographicRecord).all()
        assert len(records) == 2

        # Verify specific record
        stuart = db_session.query(BiblographicRecord).filter_by(isbn="isbn:2211056466").first()
        assert stuart is not None
        assert stuart.title == "Stuart Little"
        assert json.loads(stuart.authors) == ["White, E.B."]
        assert stuart.medium_type == "Livre"

    def test_import_with_french_characters(self, db_session):
        """Import CSV with French accented characters (é, è, à, ç)."""
        # Arrange
        csv_content = """dc.title,dc.identifier,dc.creator,dc.publisher,dc.description
L'Été à Paris,isbn:9782070612345,"Saint-Exupéry, Antoine de",Éditions Gallimard,Un été magnifique avec des événements extraordinaires
Noël en décembre,isbn:9782070678901,"Beauté, François",Hachette,Célébration de Noël"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 2
        assert len(result.errors) == 0

        # Verify French characters preserved
        record1 = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070612345").first()
        assert record1.title == "L'Été à Paris"
        assert record1.publisher == "Éditions Gallimard"
        assert "été" in record1.description
        assert "événements" in record1.description

        record2 = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070678901").first()
        assert record2.title == "Noël en décembre"
        assert "Beauté" in json.loads(record2.authors)[0]
        assert "Célébration" in record2.description

    def test_import_with_missing_required_title(self, db_session):
        """Import should reject rows missing required dc.title field."""
        # Arrange - No title in second row
        csv_content = """dc.title,dc.identifier
Book 1,isbn:123456
,isbn:789012"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 1
        assert result.items_created == 1
        assert len(result.errors) == 1
        assert "Missing required field" in result.errors[0]["error"]
        assert "dc.title" in result.errors[0]["error"]

    def test_import_multiple_items_same_isbn(self, db_session):
        """Multiple rows with same ISBN should create ONE record and MULTIPLE items."""
        # Arrange - Two items for same book
        csv_content = """dc.title,dc.identifier,item.id,item.callNumber
Stuart Little,isbn:2211056466,ITEM001,800.000
Stuart Little,isbn:2211056466,ITEM002,800.000"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 1  # One bibliographic record
        assert result.items_created == 2  # Two physical items

        # Verify database
        records = db_session.query(BiblographicRecord).all()
        assert len(records) == 1

        record = records[0]
        assert len(record.items) == 2
        assert record.items[0].item_id == "ITEM001"
        assert record.items[1].item_id == "ITEM002"

    def test_import_semicolon_delimiter(self, db_session):
        """Import should auto-detect semicolon delimiter."""
        # Arrange - Semicolon-separated CSV (common in French Excel)
        csv_content = """dc.title;dc.identifier;dc.creator
Les Misérables;isbn:123456;Hugo, Victor
Le Petit Prince;isbn:789012;Saint-Exupéry, Antoine de"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 2
        assert result.items_created == 2
        assert len(result.errors) == 0

    def test_import_pipe_separated_multi_values(self, db_session):
        """Multi-valued fields should be split by pipe character."""
        # Arrange - Multiple authors and keywords
        csv_content = """dc.title,dc.identifier,dc.creator,dc.subject
Astérix,isbn:123456,"Goscinny, René|Uderzo, Albert",Humour|Histoire|Bande dessinée"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 1

        record = db_session.query(BiblographicRecord).first()
        authors = json.loads(record.authors)
        assert len(authors) == 2
        assert "Goscinny, René" in authors
        assert "Uderzo, Albert" in authors

        keywords = json.loads(record.keywords)
        assert len(keywords) == 3
        assert "Humour" in keywords
        assert "Histoire" in keywords
        assert "Bande dessinée" in keywords

    def test_import_with_optional_fields(self, db_session):
        """Import with all optional Dublin Core fields."""
        # Arrange - All Dublin Core fields populated
        csv_content = """dc.title,dc.identifier,dc.creator,dc.subject,dc.description,dc.publisher,dc.contributor,dc.date,dc.type,dc.format,dc.language,dc.source,dc.relation,dc.coverage,dc.rights
Complete Book,isbn:9782070123456,"Author Name",Science|Tech,A complete description,Publisher Inc,"Illustrator Name",2024,Livre,300 pages,fr,Science Collection,Volume 1,Adult,Loanable"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 1

        record = db_session.query(BiblographicRecord).first()
        assert record.title == "Complete Book"
        assert record.isbn == "isbn:9782070123456"
        assert json.loads(record.authors) == ["Author Name"]
        assert json.loads(record.keywords) == ["Science", "Tech"]
        assert record.description == "A complete description"
        assert record.publisher == "Publisher Inc"
        assert json.loads(record.illustrators) == ["Illustrator Name"]
        assert record.publication_year == 2024
        assert record.medium_type == "Livre"
        assert record.page_count == 300
        assert record.language == "fr"
        assert record.collection == "Science Collection"
        assert record.series_number == "Volume 1"
        assert record.level == "Adult"

    def test_import_with_item_fields(self, db_session):
        """Import with item extension fields (item.id, item.callNumber, etc.)."""
        # Arrange
        csv_content = """dc.title,dc.identifier,item.id,item.callNumber,item.acquisitionDate,item.fundingSource
Book Title,isbn:123456,INV001,800.000,2024-01-15,Budget 2024"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.items_created == 1

        item = db_session.query(Item).first()
        assert item.item_id == "INV001"
        assert item.call_number == "800.000"
        assert str(item.acquisition_date) == "2024-01-15"
        assert item.funding_source == "Budget 2024"

    def test_import_duplicate_isbn_skipped(self, db_session):
        """Importing duplicate ISBN should skip the bibliographic record."""
        # Arrange - Create existing record
        existing = BiblographicRecord(
            title="Existing Book",
            isbn="isbn:9782070123456",
            medium_type="Livre"
        )
        db_session.add(existing)
        db_session.flush()

        existing_item = Item(
            item_id="OLD001",
            bibliographic_record_id=existing.id
        )
        db_session.add(existing_item)
        db_session.commit()

        # Import CSV with same ISBN
        csv_content = """dc.title,dc.identifier,item.id
New Book Title,isbn:9782070123456,NEW001"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_skipped == 1  # Record skipped (duplicate ISBN)
        assert result.items_created == 1  # But item still created

        # Verify database
        records = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070123456").all()
        assert len(records) == 1  # Only one record
        assert records[0].title == "Existing Book"  # Original title preserved

        # But item was added
        items = db_session.query(Item).filter_by(bibliographic_record_id=existing.id).all()
        assert len(items) == 2
        item_ids = [item.item_id for item in items]
        assert "OLD001" in item_ids
        assert "NEW001" in item_ids

    def test_import_year_parsing(self, db_session):
        """Test various year format parsing (YYYY, YYYY-MM-DD)."""
        # Arrange
        csv_content = """dc.title,dc.identifier,dc.date
Book A,isbn:9782070111111,2024
Book B,isbn:9782070222222,2024-05-15
Book C,isbn:9782070333333,invalid
Book D,isbn:9782070444444,999"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 4

        book_a = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070111111").first()
        assert book_a.publication_year == 2024

        book_b = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070222222").first()
        assert book_b.publication_year == 2024  # Extracts year from date

        book_c = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070333333").first()
        assert book_c.publication_year is None  # Invalid year

        book_d = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070444444").first()
        assert book_d.publication_year is None  # Out of range (< 1000)

    def test_import_page_count_extraction(self, db_session):
        """Test page count extraction from dc.format field."""
        # Arrange
        csv_content = """dc.title,dc.identifier,dc.format
Book A,isbn:9782070111111,300 pages
Book B,isbn:9782070222222,173 p
Book C,isbn:9782070333333,Not a page count"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        book_a = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070111111").first()
        assert book_a.page_count == 300

        book_b = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070222222").first()
        assert book_b.page_count == 173

        book_c = db_session.query(BiblographicRecord).filter_by(isbn="isbn:9782070333333").first()
        assert book_c.page_count is None

    def test_import_empty_csv(self, db_session):
        """Import empty CSV should return zero records."""
        # Arrange
        csv_content = """dc.title,dc.identifier"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 0
        assert result.items_created == 0
        assert len(result.errors) == 0

    def test_import_large_dataset_performance(self, db_session):
        """Test bulk import performance with 100 records."""
        # Arrange - Generate 100 records
        rows = [["dc.title", "dc.identifier"]]
        for i in range(100):
            rows.append([f"Book {i}", f"isbn:ISBN{i:05d}"])

        output = StringIO()
        writer = csv.writer(output)
        writer.writerows(rows)
        csv_content = output.getvalue()

        # Act
        import time
        start = time.time()
        result = import_dublin_core_csv(db_session, csv_content)
        duration = time.time() - start

        # Assert
        assert result.records_created == 100
        assert result.items_created == 100
        assert duration < 10.0  # Should complete in under 10 seconds (SC-002)

    def test_import_isbn_normalization(self, db_session):
        """Test ISBN normalization (remove hyphens, spaces)."""
        # Arrange - ISBNs with different formatting but each unique after normalization
        csv_content = """dc.title,dc.identifier
Book A,isbn:978-2-07-061275-8
Book B,isbn:2 07 061 276 5
Book C,isbn:2070612772"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 3

        book_a = db_session.query(BiblographicRecord).filter_by(title="Book A").first()
        assert book_a.isbn == "isbn:9782070612758"  # Hyphens removed, prefix added

        book_b = db_session.query(BiblographicRecord).filter_by(title="Book B").first()
        assert book_b.isbn == "isbn:2070612765"  # Spaces removed, prefix added

        book_c = db_session.query(BiblographicRecord).filter_by(title="Book C").first()
        assert book_c.isbn == "isbn:2070612772"  # Prefix added

    def test_import_without_isbn_uses_title_as_key(self, db_session):
        """Records without ISBN should use title as deduplication key."""
        # Arrange - Two rows with same title, no ISBN
        csv_content = """dc.title,dc.identifier,item.id
Book Without ISBN,,ITEM001
Book Without ISBN,,ITEM002"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 1  # One record (deduplicated by title)
        assert result.items_created == 2  # Two items

        records = db_session.query(BiblographicRecord).filter_by(title="Book Without ISBN").all()
        assert len(records) == 1
        assert len(records[0].items) == 2

    def test_import_error_recovery(self, db_session):
        """Import should continue after errors and report them."""
        # Arrange - Mix of valid and invalid rows
        csv_content = """dc.title,dc.identifier
Valid Book 1,isbn:111111
,isbn:222222
Valid Book 2,isbn:333333
,isbn:444444"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 2  # Two valid records
        assert len(result.errors) == 2  # Two errors for missing titles

        # Verify valid records were imported
        records = db_session.query(BiblographicRecord).all()
        assert len(records) == 2
        titles = [r.title for r in records]
        assert "Valid Book 1" in titles
        assert "Valid Book 2" in titles

    def test_import_strips_item_prefix(self, db_session):
        """Test that importing items automatically strips the item barcode prefix."""
        # Arrange - Get actual prefix from settings
        from src.bcd_api.services.settings_service import get_settings
        settings = get_settings(db_session)
        prefix = settings.item_barcode_prefix or "."

        prefixed_id = f"{prefix}785"
        csv_content = f"""dc.title,dc.identifier,item.id
Book with Prefixed Item,isbn:9782070611111,{prefixed_id}"""

        # Act
        result = import_dublin_core_csv(db_session, csv_content)

        # Assert
        assert result.records_created == 1
        assert result.items_created == 1
        assert len(result.errors) == 0

        # Verify database has "785" and not ".785"
        db_item = db_session.query(Item).filter_by(item_id="785").first()
        assert db_item is not None
        assert db_session.query(Item).filter_by(item_id=prefixed_id).first() is None

