# Release Process

Guide rapide pour créer une nouvelle release de BCD.

## Backend (Python API + CLI)

### Préparation

1. **Tests**:
   ```bash
   pytest tests/unit tests/integration --cov=src --cov-report=html
   ```

2. **Code quality**:
   ```bash
   black src/ tests/
   ruff src/ tests/
   ```

3. **Update CHANGELOG** (si présent):
   ```markdown
   ## [Unreleased]
   ### Added
   - Feature X
   ### Fixed
   - Bug Y
   ```

### Release

**Automatique** (recommandé):
```bash
# Patch (bug fixes): 1.0.0 -> 1.0.1
python scripts/bump_version.py patch --push

# Minor (new features): 1.0.0 -> 1.1.0
python scripts/bump_version.py minor --push

# Major (breaking changes): 1.0.0 -> 2.0.0
python scripts/bump_version.py major --push
```

Le script:
- ✅ Met à jour `pyproject.toml`
- ✅ Crée commit + tag `vX.X.X`
- ✅ Push vers GitHub
- ✅ Déclenche workflows CI/CD
- ✅ Génère releases Windows + Linux

**Manuel** (si besoin):
```bash
# 1. Bumper version (sans push)
python scripts/bump_version.py patch

# 2. Review changes
git show HEAD
git log --oneline -5

# 3. Push quand prêt
git push && git push --tags
```

### Vérification

1. Aller sur [GitHub Actions](https://github.com/Filirom1/bcd/actions)
2. Vérifier que les workflows `release-windows` et `release-linux` sont lancés
3. Attendre la fin du build (~5-10 min)
4. Vérifier la [Release](https://github.com/Filirom1/bcd/releases) créée

## Client Godot

### Préparation

1. **Tests manuels**:
   - Ouvrir `bcd_kids/project.godot` dans Godot 4.6
   - Lancer avec F5
   - Tester:
     - ✓ Découverte serveur (mDNS)
     - ✓ Connexion manuelle
     - ✓ Sélection classe
     - ✓ Login élève
     - ✓ Emprunter livre
     - ✓ Retourner livre
     - ✓ Recherche + filtres
     - ✓ Réservations
     - ✓ Changement langue FR/EN

2. **Vérifier optimisations**:
   - Tester sur vieux PC si possible (4GB RAM, HDD)
   - Vérifier démarrage <5 secondes
   - Vérifier RAM <300 MB

### Release

**Automatique** (recommandé):
```bash
# Patch (bug fixes): 1.0.0 -> 1.0.1
python scripts/bump_godot_version.py patch --push

# Minor (new features): 1.0.0 -> 1.1.0
python scripts/bump_godot_version.py minor --push

# Major (breaking changes): 1.0.0 -> 2.0.0
python scripts/bump_godot_version.py major --push
```

Le script:
- ✅ Met à jour `bcd_kids/export_presets.cfg`
- ✅ Crée commit + tag `godot-vX.X.X`
- ✅ Push vers GitHub
- ✅ Déclenche workflow CI/CD
- ✅ Génère releases Windows + Linux

**Manuel** (si besoin):
```bash
# 1. Bumper version (sans push)
python scripts/bump_godot_version.py patch

# 2. Review changes
git show HEAD
git log --oneline -5

# 3. Push quand prêt
git push && git push --tags
```

### Vérification

1. Aller sur [GitHub Actions](https://github.com/Filirom1/bcd/actions)
2. Vérifier que le workflow `build-godot` est lancé
3. Attendre la fin du build (~3-5 min)
4. Vérifier la [Release](https://github.com/Filirom1/bcd/releases) créée
5. Télécharger et tester les binaires:
   - Windows: `BCD-Godot-vX.X.X-Windows.zip`
   - Linux: `BCD-Godot-vX.X.X-Linux.tar.gz`

## Release Notes

### Backend

Les release notes sont générées automatiquement par le workflow.

Pour personnaliser, éditer la release sur GitHub après création.

**Template**:
```markdown
## What's Changed
- Feature A (#123)
- Bug fix B (#124)

## Installation
See INSTALL.md for installation instructions.

## System Requirements
- Windows 10/11 or Linux
- 500 MB disk space
- No Python required (portable builds)
```

### Godot Client

Utiliser le template dans `bcd_kids/RELEASE_TEMPLATE.md`.

**Sections à remplir**:
- Nouveautés (Added)
- Corrections (Fixed)
- Améliorations (Improved)

## Versioning

Suivre [Semantic Versioning](https://semver.org/):

- **MAJOR** (`X.0.0`) — Breaking changes
  - Changement d'API incompatible
  - Suppression de fonctionnalités
  - Migration de données requise

- **MINOR** (`0.X.0`) — New features
  - Nouvelles fonctionnalités
  - Améliorations majeures
  - Rétro-compatible

- **PATCH** (`0.0.X`) — Bug fixes
  - Corrections de bugs
  - Petites améliorations
  - Hotfixes

## Calendrier de Release

**Backend**: Release à la demande (bug fixes) ou mensuelle (features)

**Godot Client**: Release synchronisée avec backend si changements API

## Rollback

Si une release pose problème:

1. **Supprimer le tag** (local + remote):
   ```bash
   git tag -d vX.X.X              # local
   git push --delete origin vX.X.X # remote
   ```

2. **Supprimer la release GitHub**:
   - Aller sur [Releases](https://github.com/Filirom1/bcd/releases)
   - Cliquer sur "Delete" pour la release

3. **Revert le commit de version**:
   ```bash
   git revert HEAD
   git push
   ```

4. **Re-release** avec version corrigée:
   ```bash
   python scripts/bump_version.py patch --push
   ```

## Checklist Release

### Backend
- [ ] Tests passent (unit + integration)
- [ ] Coverage ≥80%
- [ ] Code quality OK (black + ruff)
- [ ] CHANGELOG mis à jour (si présent)
- [ ] Documentation à jour
- [ ] Migration DB testée (si applicable)
- [ ] Bumper version avec script
- [ ] Vérifier workflow GitHub Actions
- [ ] Tester binaires (Windows + Linux)
- [ ] Personnaliser release notes si besoin

### Godot Client
- [ ] Tests manuels complets
- [ ] Performance OK sur vieux PC
- [ ] Connexion serveur OK (mDNS + manuel)
- [ ] Toutes fonctionnalités testées
- [ ] UI/UX OK (pas de débordement)
- [ ] i18n FR/EN complet
- [ ] Bumper version avec script
- [ ] Vérifier workflow GitHub Actions
- [ ] Tester binaires (Windows + Linux)
- [ ] Remplir release notes depuis template

## Support

- **Issues**: [GitHub Issues](https://github.com/Filirom1/bcd/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Filirom1/bcd/discussions)
- **Documentation**: README.md, INSTALL.md, CLAUDE.md
