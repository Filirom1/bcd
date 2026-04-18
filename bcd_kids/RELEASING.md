# Releasing BCD Godot Client

Guide rapide pour créer une nouvelle version du client Godot.

## Quick Start

Depuis la **racine du projet** (pas `bcd_kids/`):

```bash
# Voir la version actuelle
python scripts/bump_godot_version.py --current

# Release patch (bug fixes)
python scripts/bump_godot_version.py patch --push

# Release minor (new features)
python scripts/bump_godot_version.py minor --push

# Release major (breaking changes)
python scripts/bump_godot_version.py major --push
```

C'est tout ! Le script s'occupe du reste.

## Que fait le script ?

1. **Met à jour la version** dans `export_presets.cfg`:
   - `application/file_version`
   - `application/product_version`

2. **Crée un commit** git:
   ```
   chore: bump godot client version to X.X.X
   ```

3. **Crée un tag** git annoté:
   ```
   godot-vX.X.X
   ```

4. **Push** (avec `--push`):
   - Push le commit
   - Push le tag
   - Déclenche GitHub Actions

5. **GitHub Actions** (automatique):
   - Build Windows (`.exe`)
   - Build Linux (`.x86_64`)
   - Crée une GitHub Release
   - Upload les binaires + checksums

## Avant de Release

### Tests Manuels

1. Ouvrir `project.godot` dans Godot 4.6
2. Lancer avec F5
3. Tester toutes les fonctionnalités:

**Checklist**:
- [ ] Découverte serveur (mDNS)
- [ ] Connexion manuelle
- [ ] Sélection de classe
- [ ] Login élève
- [ ] Emprunter un livre
- [ ] Retourner un livre
- [ ] Recherche catalogue
- [ ] Filtres (Type, Genre, Catégorie)
- [ ] Réservations (créer, voir, annuler)
- [ ] Changement langue FR/EN
- [ ] Breadcrumb navigation
- [ ] Bouton retour

### Tests Performance (PC scolaires)

Si possible, tester sur un vieux PC:
- 4 GB RAM
- HDD (pas SSD)
- CPU ≥2 GHz
- GPU Intel HD Graphics 2000+

**Vérifier**:
- [ ] Démarrage <5 secondes
- [ ] RAM usage <300 MB
- [ ] Pas de lag dans l'interface
- [ ] Pas de freeze sur recherche

### Script de Vérification

Utiliser le script de vérification système:
```bash
# Dans bcd_kids/scripts/
powershell -ExecutionPolicy Bypass -File check-system.ps1
```

## Workflow Détaillé

### 1. Préparation

```bash
# Vérifier l'état git
git status

# Commit tous les changements non-committés
git add .
git commit -m "feat: descriptif changement"

# Vérifier qu'on est sur main
git checkout main
git pull
```

### 2. Bumper Version

**Option A: Automatique** (recommandé)
```bash
python scripts/bump_godot_version.py patch --push
```

**Option B: Manuel** (si besoin de review)
```bash
# 1. Bumper sans push
python scripts/bump_godot_version.py patch

# 2. Vérifier le commit
git show HEAD

# 3. Vérifier le tag
git tag -n | grep godot

# 4. Push quand prêt
git push && git push --tags
```

### 3. Vérification GitHub

1. Aller sur [Actions](https://github.com/Filirom1/bcd/actions)
2. Vérifier workflow "Release Godot Client" lancé
3. Attendre fin du build (~3-5 min)
4. Vérifier [Releases](https://github.com/Filirom1/bcd/releases)

### 4. Tests des Binaires

**Windows**:
```powershell
# Télécharger BCD-Godot-vX.X.X-Windows.zip
Expand-Archive BCD-Godot-vX.X.X-Windows.zip -DestinationPath C:\Test
C:\Test\BCD-Godot.exe
```

**Linux**:
```bash
# Télécharger BCD-Godot-vX.X.X-Linux.tar.gz
tar -xzf BCD-Godot-vX.X.X-Linux.tar.gz -C ~/test
chmod +x ~/test/BCD-Godot.x86_64
~/test/BCD-Godot.x86_64
```

### 5. Release Notes

Éditer la release sur GitHub:

1. Aller sur la release créée
2. Cliquer "Edit"
3. Remplir depuis `RELEASE_TEMPLATE.md`:
   - Nouveautés
   - Corrections
   - Améliorations
4. Save

## Versioning

Suivre [Semantic Versioning](https://semver.org/):

**PATCH** (1.0.X) — Bug fixes
- Fix crash dans la recherche
- Correction affichage
- Performance amélioration mineure

**MINOR** (1.X.0) — New features
- Nouvelle fonctionnalité
- Amélioration UI majeure
- Changement compatible API

**MAJOR** (X.0.0) — Breaking changes
- Incompatibilité API serveur
- Refonte architecture
- Suppression fonctionnalités

## Exemples

**Patch Release**:
```bash
# 1.0.0 -> 1.0.1
# Fix: Correction crash lors scan code-barres invalide
python scripts/bump_godot_version.py patch --push
```

**Minor Release**:
```bash
# 1.0.1 -> 1.1.0
# Feature: Ajout écran statistiques emprunts
python scripts/bump_godot_version.py minor --push
```

**Major Release**:
```bash
# 1.1.0 -> 2.0.0
# Breaking: Migration vers API v2 (incompatible v1)
python scripts/bump_godot_version.py major --push
```

## Rollback

Si la release pose problème:

1. **Supprimer le tag**:
   ```bash
   git tag -d godot-vX.X.X              # local
   git push --delete origin godot-vX.X.X # remote
   ```

2. **Supprimer la release GitHub**:
   - Releases → Delete release

3. **Revert le commit**:
   ```bash
   git revert HEAD
   git push
   ```

4. **Corriger et re-release**:
   ```bash
   # Fix le problème
   git add .
   git commit -m "fix: correction problème"

   # Re-release
   python scripts/bump_godot_version.py patch --push
   ```

## Hotfix Urgent

Pour un fix urgent en production:

1. **Fix le bug**:
   ```bash
   git checkout main
   # Faire le fix
   git add .
   git commit -m "fix: correction critique"
   ```

2. **Release immédiatement**:
   ```bash
   python scripts/bump_godot_version.py patch --push
   ```

3. **Communiquer**:
   - Éditer release notes (mention hotfix)
   - Prévenir utilisateurs si critique

## Calendrier Releases

**Patch**: À la demande (bug fixes)
**Minor**: Mensuel ou bi-mensuel (features)
**Major**: Annuel ou selon besoins (breaking changes)

## Support

- **Issues**: [GitHub Issues](https://github.com/Filirom1/bcd/issues)
- **Documentation**: [README.md](README.md), [DEPLOYMENT.md](DEPLOYMENT.md)
- **Script version**: `scripts/bump_godot_version.py --help`
