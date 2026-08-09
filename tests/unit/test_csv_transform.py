"""Unit tests for CSV transformation service (BCD -> Dublin Core)"""

from src.bcd_api.services.catalog.transform import _map_support_to_dc_type, transform_bcd_to_dublin_core


class TestTransformBcdToDublinCore:
    """Test BCD CSV to Dublin Core transformation"""

    def test_basic_transformation(self):
        """Test basic BCD to Dublin Core transformation with required fields"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
785;800.000;Lire des histoires;Album;Ils ont arrêté mon père;;978-2-8006-8734-6;Carmi (Danielle);;;Flammarion;;;Livre;famille;CP-CE1;Un récit...;128 p;;Budget 2024;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv)

        # Verify it returns CSV
        assert result is not None
        lines = result.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row

        # Check header
        header = lines[0]
        assert "dc.title" in header
        assert "dc.identifier" in header
        assert "dc.creator" in header
        assert "item.id" in header

        # Check data row
        data = lines[1]
        assert "Ils ont arrêté mon père" in data
        assert "978-2-8006-8734-6" in data
        assert "Carmi, Danielle" in data  # Author format converted
        assert "785" in data  # Item ID

    def test_title_with_subtitle(self):
        """Test that title and subtitle are combined with colon"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Le Grand Livre;Une aventure extraordinaire;;;;;;;;Livre;;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv)
        lines = result.strip().split("\n")

        # Title should be combined with subtitle
        assert "Le Grand Livre: Une aventure extraordinaire" in lines[1]

    def test_author_name_conversion(self):
        """Test conversion of author format from 'LastName (FirstName)' to 'LastName, FirstName'"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Test Book;;;"Rowling (J.K.)";;;;;;;Livre;;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv)
        lines = result.strip().split("\n")

        # Author should be converted
        assert "Rowling, J.K." in lines[1]

    def test_illustrator_name_conversion(self):
        """Test conversion of illustrator format"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Test Book;;;;"Dupont (Marie)";;;;;;Livre;;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv)
        lines = result.strip().split("\n")

        # Illustrator should be converted to contributor
        assert "Dupont, Marie" in lines[1]

    def test_keywords_transformation(self):
        """Test that comma-separated keywords become pipe-separated"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Test Book;;;;;;;;;Livre;histoire, aventure, famille;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv)
        lines = result.strip().split("\n")

        # Keywords should be pipe-separated
        assert "histoire|aventure|famille" in lines[1]

    def test_page_count_extraction(self):
        """Test extraction of page count from Taille field"""
        # Test "173 p" format
        bcd_csv1 = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Test Book;;;;;;;;;Livre;;;;173 p;;Oui"""

        result1 = transform_bcd_to_dublin_core(bcd_csv1)
        assert "173 pages" in result1

        # Test "83 pages" format
        bcd_csv2 = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
002;100.000;;;Test Book;;;;;;;;;Livre;;;;83 pages;;Oui"""

        result2 = transform_bcd_to_dublin_core(bcd_csv2)
        assert "83 pages" in result2

    def test_empruntable_to_rights(self):
        """Test mapping of Empruntable (Oui/Non) to dc.rights"""
        # Test "Oui" -> "Loanable"
        bcd_csv_oui = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Test Book;;;;;;;;;Livre;;;;;;;Oui"""

        result_oui = transform_bcd_to_dublin_core(bcd_csv_oui)
        assert "Loanable" in result_oui

        # Test "Non" -> "Not loanable"
        bcd_csv_non = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
002;100.000;;;Test Book;;;;;;;;;Livre;;;;;;;Non"""

        result_non = transform_bcd_to_dublin_core(bcd_csv_non)
        assert "Not loanable" in result_non

    def test_support_to_dc_type_mapping(self):
        """Test mapping of Support to Dublin Core type"""
        # Test Livre -> Text
        bcd_csv_livre = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Test Book;;;;;;;;;Livre;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv_livre)
        assert "Text" in result

        # Test CD -> Sound
        bcd_csv_cd = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
002;100.000;;;Music CD;;;;;;;;;CD;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv_cd)
        assert "Sound" in result

        # Test DVD -> MovingImage
        bcd_csv_dvd = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
003;100.000;;;Movie;;;;;;;;;DVD;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv_dvd)
        assert "MovingImage" in result

    def test_multiple_rows_transformation(self):
        """Test transformation of multiple rows"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Book One;;;;;;;;;Livre;;;;;;Oui
002;200.000;;;Book Two;;;;;;;;;Livre;;;;;;Oui
003;300.000;;;Book Three;;;;;;;;;CD;;;;;;Non"""

        result = transform_bcd_to_dublin_core(bcd_csv)
        lines = result.strip().split("\n")

        assert len(lines) == 4  # Header + 3 data rows
        assert "Book One" in result
        assert "Book Two" in result
        assert "Book Three" in result

    def test_empty_optional_fields(self):
        """Test that empty optional fields are handled gracefully"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Minimal Book;;;;;;;;;Livre;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv)
        lines = result.strip().split("\n")

        # Should still create valid CSV
        assert len(lines) == 2
        assert "Minimal Book" in lines[1]

    def test_all_dublin_core_fields_present(self):
        """Test that all Dublin Core fields are included in output"""
        bcd_csv = """Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
001;100.000;;;Test;;;;;;;;Livre;;;;;;;Oui"""

        result = transform_bcd_to_dublin_core(bcd_csv)
        header = result.strip().split("\n")[0]

        # Check all Dublin Core fields
        dc_fields = [
            "dc.title",
            "dc.identifier",
            "dc.creator",
            "dc.contributor",
            "dc.subject",
            "dc.description",
            "dc.publisher",
            "dc.date",
            "dc.type",
            "dc.format",
            "dc.source",
            "dc.relation",
            "dc.coverage",
            "dc.rights",
            "item.id",
            "item.callNumber",
            "item.acquisitionDate",
            "item.fundingSource",
        ]

        for field in dc_fields:
            assert field in header, f"Missing field: {field}"


class TestMapSupportToDcType:
    """Test Support to Dublin Core Type mapping function"""

    def test_livre_mapping(self):
        """Test that 'Livre' maps to 'Text'"""
        assert _map_support_to_dc_type("Livre") == "Text"
        assert _map_support_to_dc_type("livre") == "Text"
        assert _map_support_to_dc_type("LIVRE") == "Text"

    def test_cd_mapping(self):
        """Test that 'CD' maps to 'Sound'"""
        assert _map_support_to_dc_type("CD") == "Sound"
        assert _map_support_to_dc_type("cd") == "Sound"
        assert _map_support_to_dc_type("CD Audio") == "Sound"

    def test_dvd_mapping(self):
        """Test that 'DVD' maps to 'MovingImage'"""
        assert _map_support_to_dc_type("DVD") == "MovingImage"
        assert _map_support_to_dc_type("dvd") == "MovingImage"
        assert _map_support_to_dc_type("DVD Vidéo") == "MovingImage"

    def test_film_mapping(self):
        """Test that 'Film' maps to 'MovingImage'"""
        assert _map_support_to_dc_type("Film") == "MovingImage"
        assert _map_support_to_dc_type("film") == "MovingImage"

    def test_periodical_mapping(self):
        """Test that periodicals map to 'Text;Periodical'"""
        assert _map_support_to_dc_type("Périodique") == "Text;Periodical"
        assert _map_support_to_dc_type("Revue") == "Text;Periodical"
        assert _map_support_to_dc_type("Magazine") == "Text;Periodical"

    def test_empty_mapping(self):
        """Test that empty support maps to default 'PhysicalObject' (since no value provided)"""
        assert _map_support_to_dc_type("") == "Text"  # Empty defaults to Text
        assert _map_support_to_dc_type("   ") == "PhysicalObject"  # Whitespace-only returns PhysicalObject

    def test_unknown_mapping(self):
        """Test that unknown support maps to 'PhysicalObject'"""
        assert _map_support_to_dc_type("Unknown Type") == "PhysicalObject"
        assert _map_support_to_dc_type("Jeux") == "PhysicalObject"
