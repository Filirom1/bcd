"""Unit tests for Dublin Core import service"""

from datetime import date

from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.services.catalog.import_dc import (
    _map_dc_type_to_medium_type,
    import_dublin_core_csv,
)


class TestImportDublinCoreCSV:
    """Test Dublin Core CSV import functionality"""

    def test_basic_import_comma_separated(self, db_session):
        """Test basic import with comma-separated CSV"""
        csv_content = """dc.title,dc.identifier,dc.creator,item.id,item.callNumber
Harry Potter,978-0747532699,Rowling| J.K.,HP001,823.92"""

        result = import_dublin_core_csv(db_session, csv_content)

        assert result.records_created == 1
        assert result.items_created == 1
        assert len(result.errors) == 0

        # Verify bibliographic record
        biblio = db_session.query(BibliographicRecord).first()
        assert biblio is not None
        assert biblio.title == "Harry Potter"
        # ISBN is normalized (hyphens removed)
        assert biblio.isbn == "isbn:9780747532699"

        # Verify item
        item = db_session.query(Item).first()
        assert item is not None
        assert item.item_id == "HP001"
        assert item.call_number == "823.92"

    def test_basic_import_semicolon_separated(self, db_session):
        """Test basic import with semicolon-separated CSV (auto-detect delimiter)"""
        csv_content = """dc.title;dc.identifier;dc.creator;item.id;item.callNumber
Le Petit Prince;978-2070408504;Saint-Exupéry| Antoine de;PP001;843.91"""

        result = import_dublin_core_csv(db_session, csv_content)

        assert result.records_created == 1
        assert result.items_created == 1
        assert len(result.errors) == 0

    def test_multi_valued_fields(self, db_session):
        """Test parsing of pipe-separated multi-valued fields"""
        csv_content = """dc.title,dc.identifier,dc.creator,dc.contributor,dc.subject,item.id
Test Book,123456,Author One|Author Two,Illustrator One|Illustrator Two,Subject A|Subject B|Subject C,T001"""

        result = import_dublin_core_csv(db_session, csv_content)

        assert result.records_created == 1

        biblio = db_session.query(BibliographicRecord).first()

        # Authors should be stored as JSON
        import json
        authors = json.loads(biblio.authors)
        assert len(authors) == 2
        assert "Author One" in authors
        assert "Author Two" in authors

        # Illustrators (contributors)
        illustrators = json.loads(biblio.illustrators)
        assert len(illustrators) == 2
        assert "Illustrator One" in illustrators

        # Keywords (subjects)
        keywords = json.loads(biblio.keywords)
        assert len(keywords) == 3
        assert "Subject A" in keywords

    def test_year_extraction_from_date(self, db_session):
        """Test extraction of publication year from dc.date field"""
        # Test YYYY format
        csv_content1 = """dc.title,dc.identifier,dc.date,item.id
Book 2020,123,2020,B001"""

        result1 = import_dublin_core_csv(db_session, csv_content1)
        biblio1 = db_session.query(BibliographicRecord).first()
        assert biblio1.publication_year == 2020

        # Clear session
        db_session.query(BibliographicRecord).delete()
        db_session.query(Item).delete()
        db_session.commit()

        # Test YYYY-MM-DD format
        csv_content2 = """dc.title,dc.identifier,dc.date,item.id
Book 2021,456,2021-06-15,B002"""

        result2 = import_dublin_core_csv(db_session, csv_content2)
        biblio2 = db_session.query(BibliographicRecord).first()
        assert biblio2.publication_year == 2021

    def test_page_count_extraction_from_format(self, db_session):
        """Test extraction of page count from dc.format field"""
        # Test "300 pages" format
        csv_content1 = """dc.title,dc.identifier,dc.format,item.id
Book One,123,300 pages,B001"""

        result1 = import_dublin_core_csv(db_session, csv_content1)
        biblio1 = db_session.query(BibliographicRecord).first()
        assert biblio1.page_count == 300

        # Clear session
        db_session.query(BibliographicRecord).delete()
        db_session.query(Item).delete()
        db_session.commit()

        # Test "173 p" format
        csv_content2 = """dc.title,dc.identifier,dc.format,item.id
Book Two,456,173 p,B002"""

        result2 = import_dublin_core_csv(db_session, csv_content2)
        biblio2 = db_session.query(BibliographicRecord).first()
        assert biblio2.page_count == 173

    def test_dc_type_to_medium_type_mapping(self, db_session):
        """Test mapping of Dublin Core Type to MediumType"""
        # Test Text -> LIVRE
        csv_text = """dc.title,dc.identifier,dc.type,item.id
Text Book,123,Text,T001"""

        result = import_dublin_core_csv(db_session, csv_text)
        biblio = db_session.query(BibliographicRecord).first()
        assert biblio.medium_type == "Livre"

        # Clear and test Sound -> CD
        db_session.query(BibliographicRecord).delete()
        db_session.query(Item).delete()
        db_session.commit()

        csv_sound = """dc.title,dc.identifier,dc.type,item.id
Music Album,456,Sound,S001"""

        result = import_dublin_core_csv(db_session, csv_sound)
        biblio = db_session.query(BibliographicRecord).first()
        assert biblio.medium_type == "CD"

    def test_rights_to_loanable_mapping(self, db_session):
        """Test mapping of dc.rights to item loanable field"""
        # Test "Loanable" -> True
        csv_loanable = """dc.title,dc.identifier,dc.rights,item.id
Book One,123,Loanable,B001"""

        result = import_dublin_core_csv(db_session, csv_loanable)
        item = db_session.query(Item).first()
        assert item.loanable is True

        # Clear and test "Not loanable" -> False
        db_session.query(BibliographicRecord).delete()
        db_session.query(Item).delete()
        db_session.commit()

        csv_not_loanable = """dc.title,dc.identifier,dc.rights,item.id
Book Two,456,Not loanable,B002"""

        result = import_dublin_core_csv(db_session, csv_not_loanable)
        item = db_session.query(Item).first()
        assert item.loanable is False

    def test_acquisition_date_parsing(self, db_session):
        """Test parsing of item acquisition date"""
        csv_content = """dc.title,dc.identifier,item.id,item.acquisitionDate
Test Book,123,T001,2024-09-15"""

        result = import_dublin_core_csv(db_session, csv_content)
        item = db_session.query(Item).first()

        assert item.acquisition_date == date(2024, 9, 15)

    def test_grouping_by_isbn(self, db_session):
        """Test that multiple items with same ISBN share one bibliographic record"""
        csv_content = """dc.title,dc.identifier,dc.creator,item.id,item.callNumber
Harry Potter,978-0747532699,Rowling| J.K.,HP001,823.92
Harry Potter,978-0747532699,Rowling| J.K.,HP002,823.92
Harry Potter,978-0747532699,Rowling| J.K.,HP003,823.92"""

        result = import_dublin_core_csv(db_session, csv_content)

        # Should create 1 bibliographic record and 3 items
        assert result.records_created == 1
        assert result.items_created == 3

        biblio_count = db_session.query(BibliographicRecord).count()
        item_count = db_session.query(Item).count()

        assert biblio_count == 1
        assert item_count == 3

    def test_grouping_by_title_when_no_isbn(self, db_session):
        """Test that items without ISBN group by title"""
        csv_content = """dc.title,dc.identifier,item.id
Custom Book,,CB001
Custom Book,,CB002"""

        result = import_dublin_core_csv(db_session, csv_content)

        # Should create 1 bibliographic record (grouped by title) and 2 items
        assert result.records_created == 1
        assert result.items_created == 2

    def test_skip_existing_isbn(self, db_session):
        """Test that existing ISBN is skipped"""
        # Create existing record with normalized ISBN (no hyphens)
        existing = BibliographicRecord(
            title="Existing Book",
            isbn="isbn:9780747532699",  # Now stored with isbn: prefix
            medium_type="Livre",
        )
        db_session.add(existing)
        db_session.commit()

        # Try to import same ISBN (with hyphens - will be normalized)
        csv_content = """dc.title,dc.identifier,item.id
New Book,978-0747532699,NB001"""

        result = import_dublin_core_csv(db_session, csv_content)

        # Should skip bibliographic record but create item
        assert result.records_created == 0
        assert result.records_skipped == 1
        assert result.items_created == 1

        # Item should be linked to existing record
        item = db_session.query(Item).filter_by(item_id="NB001").first()
        assert item.bibliographic_record_id == existing.id

    def test_skip_existing_item_id(self, db_session):
        """Test that existing item_id is skipped"""
        # Create existing biblio and item
        biblio = BibliographicRecord(
            title="Existing Book",
            isbn="123456",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.flush()

        existing_item = Item(
            item_id="EXIST001",
            bibliographic_record_id=biblio.id,
        )
        db_session.add(existing_item)
        db_session.commit()

        # Try to import same item_id
        csv_content = """dc.title,dc.identifier,item.id
Different Book,789,EXIST001"""

        result = import_dublin_core_csv(db_session, csv_content)

        # Should create new biblio but skip item
        assert result.records_created == 1
        assert result.items_created == 0
        assert result.items_skipped == 1

    def test_duplicate_item_id_in_csv(self, db_session):
        """Test that duplicate item_id within CSV is skipped"""
        csv_content = """dc.title,dc.identifier,item.id
Book One,111,DUP001
Book Two,222,DUP001"""

        result = import_dublin_core_csv(db_session, csv_content)

        # Should create 2 biblios but only 1 item (second is duplicate)
        assert result.records_created == 2
        assert result.items_created == 1
        assert result.items_skipped == 1

    def test_missing_title_error(self, db_session):
        """Test that missing required title field generates error"""
        csv_content = """dc.identifier,item.id
123456,T001"""

        result = import_dublin_core_csv(db_session, csv_content)

        assert result.records_created == 0
        assert len(result.errors) > 0
        assert "dc.title" in result.errors[0]["error"]

    def test_missing_item_id_error(self, db_session):
        """Test that missing item ID generates error"""
        csv_content = """dc.title,dc.identifier
Test Book,"""

        result = import_dublin_core_csv(db_session, csv_content)

        # Biblio created but item skipped
        assert result.records_created == 1
        assert result.items_skipped == 1
        assert len(result.errors) > 0

    def test_item_id_fallback_to_identifier(self, db_session):
        """Test that item.id falls back to dc.identifier if not present"""
        csv_content = """dc.title,dc.identifier
Test Book,FALLBACK001"""

        result = import_dublin_core_csv(db_session, csv_content)

        assert result.records_created == 1
        assert result.items_created == 1

        item = db_session.query(Item).first()
        assert item.item_id == "FALLBACK001"

    def test_all_dublin_core_fields_imported(self, db_session):
        """Test that all Dublin Core fields are properly imported"""
        csv_content = """dc.title,dc.identifier,dc.creator,dc.contributor,dc.subject,dc.description,dc.publisher,dc.date,dc.type,dc.format,dc.language,dc.source,dc.relation,dc.coverage,dc.rights,item.id,item.callNumber,item.acquisitionDate,item.fundingSource
Complete Book,978-1234567890,Author A|Author B,Illustrator C,keyword1|keyword2|keyword3,A complete test description,Test Publisher,2020,Text,300 pages,eng,Test Series,Volume 1,Advanced,Loanable,CB001,100.500,2024-01-15,Budget 2024"""

        result = import_dublin_core_csv(db_session, csv_content)

        assert result.records_created == 1
        assert result.items_created == 1

        # Verify bibliographic record fields
        biblio = db_session.query(BibliographicRecord).first()
        assert biblio.title == "Complete Book"
        assert biblio.isbn == "isbn:9781234567890"  # Stored with isbn: prefix
        assert biblio.publisher == "Test Publisher"
        assert biblio.publication_year == 2020
        assert biblio.description == "A complete test description"
        assert biblio.page_count == 300
        assert biblio.language == "eng"
        assert biblio.collection == "Test Series"
        assert biblio.series_number == "Volume 1"
        assert biblio.level == "Advanced"

        # Verify item fields
        item = db_session.query(Item).first()
        assert item.item_id == "CB001"
        assert item.call_number == "100.500"
        assert item.acquisition_date == date(2024, 1, 15)
        assert item.funding_source == "Budget 2024"
        assert item.loanable is True

    def test_bulk_import_performance(self, db_session):
        """Test bulk import with multiple records"""
        # Create CSV with 100 rows
        header = "dc.title,dc.identifier,item.id\n"
        rows = "\n".join([f"Book {i},ISBN{i:03d},ITEM{i:03d}" for i in range(1, 101)])
        csv_content = header + rows

        result = import_dublin_core_csv(db_session, csv_content)

        assert result.records_created == 100
        assert result.items_created == 100
        assert len(result.errors) == 0

        # Verify database counts
        biblio_count = db_session.query(BibliographicRecord).count()
        item_count = db_session.query(Item).count()

        assert biblio_count == 100
        assert item_count == 100


class TestMapDcTypeToMediumType:
    """Test Dublin Core Type to MediumType mapping"""

    def test_text_mapping(self):
        """Test that 'Text' maps to LIVRE"""
        assert _map_dc_type_to_medium_type("Text") == "Livre"
        assert _map_dc_type_to_medium_type("text") == "Livre"
        assert _map_dc_type_to_medium_type("Book") == "Livre"

    def test_sound_mapping(self):
        """Test that 'Sound' maps to CD"""
        assert _map_dc_type_to_medium_type("Sound") == "CD"
        assert _map_dc_type_to_medium_type("Audio") == "CD"
        assert _map_dc_type_to_medium_type("CD") == "CD"

    def test_moving_image_mapping(self):
        """Test that 'MovingImage' maps to DVD"""
        assert _map_dc_type_to_medium_type("MovingImage") == "DVD"
        assert _map_dc_type_to_medium_type("Video") == "DVD"
        assert _map_dc_type_to_medium_type("DVD") == "DVD"
        assert _map_dc_type_to_medium_type("Film") == "DVD"

    def test_periodical_mapping(self):
        """Test that periodicals map to PERIODIQUE"""
        assert _map_dc_type_to_medium_type("Periodical") == "Périodique"
        assert _map_dc_type_to_medium_type("Journal") == "Périodique"
        assert _map_dc_type_to_medium_type("Magazine") == "Périodique"

    def test_empty_mapping(self):
        """Test that empty type maps to default LIVRE"""
        assert _map_dc_type_to_medium_type("") == "Livre"
        assert _map_dc_type_to_medium_type("   ") == "Livre"

    def test_unknown_mapping(self):
        """Test that unknown type is returned as-is (allowing custom values)"""
        assert _map_dc_type_to_medium_type("Unknown") == "Unknown"
        assert _map_dc_type_to_medium_type("Dataset") == "Dataset"
        assert _map_dc_type_to_medium_type("Bande dessinée") == "Bande dessinée"
        # Explicitly test "Autre" / "Other" mapping
        assert _map_dc_type_to_medium_type("Autre") == "Autre"
        assert _map_dc_type_to_medium_type("Other") == "Autre"
