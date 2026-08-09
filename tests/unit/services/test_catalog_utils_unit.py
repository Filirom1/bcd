from src.bcd_api.services._catalog_utils import (
    normalize,
    token_overlap,
    score_match,
)


def test_normalize():
    assert normalize("Le Petit Prince") == "le petit prince"
    assert normalize("Éléphant") == "elephant"
    assert normalize("l'arbre, vert!") == "l arbre vert"


def test_token_overlap():
    assert token_overlap("Le Petit Prince", "Le Petit Prince") == 1.0
    assert token_overlap("Le Petit Prince", "Petit") == 0.5
    assert token_overlap("le la", "les des") == 0.5  # no meaningful tokens


def test_score_match():
    # perfect title match
    assert score_match("Le Petit Prince", "Saint-Exupery", "Le Petit Prince", "Saint-Exupéry") > 0.85
    # partial title match
    assert score_match("Le Petit Prince", "Saint-Exupery", "Le Petit", "Saint-Exupéry") > 0.5
    # no author lastname provided
    assert score_match("Le Petit Prince", "", "Le Petit Prince", "Saint-Exupéry") == 0.85 * 1.0 + 0.15 * 0.5
