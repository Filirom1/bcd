# Guide de versioning

## Script de montée de version automatique

Le script `bump_version.py` gère automatiquement les montées de version avec git tag.

### Utilisation

```bash
# Afficher la version actuelle
python scripts/bump_version.py --current

# Patch (1.0.0 → 1.0.1) - Corrections de bugs
python scripts/bump_version.py patch

# Minor (1.0.0 → 1.1.0) - Nouvelles fonctionnalités
python scripts/bump_version.py minor

# Major (1.0.0 → 2.0.0) - Breaking changes
python scripts/bump_version.py major

# Avec push automatique vers remote
python scripts/bump_version.py patch --push
```

### Ce que fait le script

1. ✅ Lit la version actuelle dans `pyproject.toml`
2. ✅ Calcule la nouvelle version
3. ✅ Met à jour `pyproject.toml`
4. ✅ Crée un commit git : `chore: bump version to X.Y.Z`
5. ✅ Crée un tag git annoté : `vX.Y.Z`
6. ✅ (Optionnel) Pousse le commit et le tag vers remote

### Semantic Versioning

Le projet suit [Semantic Versioning 2.0.0](https://semver.org/) :

- **MAJOR** (X.0.0) : Changements incompatibles avec l'API précédente
- **MINOR** (x.Y.0) : Nouvelles fonctionnalités, rétro-compatible
- **PATCH** (x.y.Z) : Corrections de bugs, rétro-compatible

### Exemples

```bash
# Bug fix : 1.0.0 → 1.0.1
python scripts/bump_version.py patch

# Nouvelle fonctionnalité : 1.0.1 → 1.1.0
python scripts/bump_version.py minor

# Breaking change : 1.1.0 → 2.0.0
python scripts/bump_version.py major
```

### Workflow complet

```bash
# 1. Finir vos modifications
git add .
git commit -m "feat: add delete buttons to edit forms"

# 2. Bumper la version
python scripts/bump_version.py minor

# 3. Pousser vers remote (si pas fait avec --push)
git push && git push --tags

# 4. Créer une release sur GitHub/GitLab (optionnel)
```

### Options avancées

```bash
# Seulement mettre à jour pyproject.toml (pas de commit/tag)
python scripts/bump_version.py patch --no-commit

# Voir l'aide complète
python scripts/bump_version.py --help
```

## Impact sur le cache navigateur

Chaque nouvelle version force automatiquement le navigateur à télécharger les nouveaux fichiers JS/CSS grâce au cache busting :

```html
<!-- Version 1.0.0 -->
<script src="/static/js/app.js?v=1.0.0"></script>

<!-- Version 1.0.1 (après bump patch) -->
<script src="/static/js/app.js?v=1.0.1"></script>
```

Les utilisateurs reçoivent **automatiquement** la nouvelle version, même si leur navigateur a mis en cache l'ancienne.
