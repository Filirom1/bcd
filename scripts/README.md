# Scripts BCD

Utilitaires pour le développement et le déploiement de BCD.

## Version Management

### bump_version.py (UNIFIED)

**Script unifié** qui gère la version pour TOUT le projet (API + CLI + Kids client).

**Usage**:
```bash
# Voir la version actuelle
python scripts/bump_version.py --current

# Bumper la version (met à jour API ET Kids)
python scripts/bump_version.py patch   # 1.0.0 -> 1.0.1 (bug fixes)
python scripts/bump_version.py minor   # 1.0.0 -> 1.1.0 (new features)
python scripts/bump_version.py major   # 1.0.0 -> 2.0.0 (breaking changes)

# Bumper et push (déclenche TOUTES les releases)
python scripts/bump_version.py patch --push
```

**Actions**:
- Met à jour `pyproject.toml` (source unique de vérité)
- Met à jour `bcd_kids/export_presets.cfg` (synchronisé avec pyproject.toml)
- Crée commit `chore: bump version to X.X.X`
- Crée DEUX tags annotés:
  - `vX.X.X` → déclenche releases API (Windows + Linux)
  - `godot-vX.X.X` → déclenche release Kids client (Windows + Linux)
- (Avec `--push`) Push commit + tags → déclenche workflows:
  - `.github/workflows/release-windows.yml`
  - `.github/workflows/release-linux.yml`
  - `.github/workflows/release-godot.yml`

**Options**:
- `--current` — Affiche la version actuelle
- `--push` — Push automatiquement après création des tags
- `--no-commit` — Seulement mettre à jour les fichiers, pas de commit/tags

**Important**: Une seule version pour tout le projet! Le script maintient API et Kids client synchronisés.

## Workflow de Release

### Backend Python

1. Vérifier tests:
   ```bash
   pytest tests/unit tests/integration
   ```

2. Bumper version et push:
   ```bash
   python scripts/bump_version.py patch --push
   ```

3. GitHub Actions:
   - Build portable Windows (PyInstaller)
   - Build portable Linux (PyInstaller)
   - Crée GitHub Release avec binaires + checksums
   - Upload artifacts

### Client Kids

1. Tester le client:
   ```bash
   # Ouvrir bcd_kids/project.godot dans Kids 4.6
   # Lancer avec F5, tester les fonctionnalités
   ```

2. Bumper version et push:
   ```bash
   python scripts/bump_godot_version.py patch --push
   ```

3. GitHub Actions:
   - Build Windows (Kids export)
   - Build Linux (Kids export)
   - Crée GitHub Release avec binaires + checksums
   - Upload artifacts

## Versioning Scheme

Les deux projets suivent [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes (incompatibilités API/fonctionnalités)
- **MINOR**: Nouvelles fonctionnalités (rétro-compatibles)
- **PATCH**: Bug fixes (rétro-compatibles)

### Exemples

**Backend**:
- `1.0.0 → 1.0.1` — Correction bug dans l'API de recherche
- `1.0.1 → 1.1.0` — Ajout endpoint API pour statistiques
- `1.1.0 → 2.0.0` — Refonte complète du modèle de données

**Kids Client**:
- `1.0.0 → 1.0.1` — Fix crash lors de la recherche
- `1.0.1 → 1.1.0` — Ajout écran de statistiques
- `1.1.0 → 2.0.0` — Changement d'architecture (incompatible API v1)

## Autres Scripts

### reset_and_simulate.py

Réinitialise la BDD et simule 9 mois d'activité:
```bash
python reset_and_simulate.py
```

Utile pour:
- Tests de performance
- Démo
- Développement avec données réalistes

### download-vendor.py

Télécharge les dépendances vendored pour le web UI:
```bash
python scripts/download-vendor.py
```

### take_screenshots.py

Génère les screenshots pour la documentation:
```bash
python scripts/take_screenshots.py
```

### generate_help_screenshots.py

Génère les screenshots pour l'aide contextuelle:
```bash
python scripts/generate_help_screenshots.py
```

### enrich_bibliopuce.py

Enrichit un export BiblioPuce avec des données BNF:
```bash
python scripts/enrich_bibliopuce.py input.csv output.csv
```

## Notes

- Tous les scripts Python utilisent `#!/usr/bin/env python3`
- Les scripts de version nécessitent un dépôt git propre (pas de changes non-committés)
- Les scripts de version demandent confirmation avant de procéder
- Les tags créés sont annotés (avec message descriptif)
- Les workflows GitHub Actions sont déclenchés automatiquement par les tags
