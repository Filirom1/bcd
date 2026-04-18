# BCD Godot Client

Client Godot simplifié pour enfants CP-CM2 (6-11 ans) pour le système de bibliothèque BCD.

## Fonctionnalités

- **Découverte automatique de serveurs** : mDNS pour trouver les instances BCD sur le réseau local
- **Connexion manuelle** : Possibilité de saisir une URL si la découverte échoue
- **Emprunter des livres** : Scan de code-barres avec retour immédiat
- **Rendre des livres** : Retour direct depuis le menu ou par scan
- **Rechercher** : Autocomplete + filtres dynamiques (Type, Genre, Catégorie, Public)
- **Réserver** : Système de réservations avec file d'attente
- **i18n** : Français/Anglais avec changement à la volée

## Architecture

### Autoloads (Singletons)
- **GS.gd** : État global (utilisateur, livres, paramètres)
- **API.gd** : Client HTTP pour l'API REST BCD
- **I18n.gd** : Système de traduction FR/EN
- **Mgr.gd** : Gestionnaire d'écrans + notifications

### Composants Réutilisables
- **AutocompleteInput** : Champ avec suggestions + détection scanner
- **FilterPanel** : Panneau de filtres dynamiques
- **BookCard** : Carte livre avec statut et actions

### Écrans
0. **SServerDiscovery** : Découverte automatique des serveurs BCD (mDNS) + connexion manuelle
1. **SClassSelect** : Sélection de classe
2. **SNameInput** : Saisie prénom avec recherche
3. **SMainMenu** : Menu principal (hub)
4. **SCheckout** : Emprunter par scan
5. **SReturnScan** : Rendre par scan
6. **SSearch** : Recherche avancée avec filtres
7. **SHoldConfirm** : Confirmation réservation
8. **SMyHolds** : Gestion des réservations

## Configuration

### Paramètres (Résolution et Qualité graphique)

Accessible via le bouton ⚙️ dans l'écran de sélection de classe.

**Résolution** :
- **1280×720** (petits écrans, vieux PC)
- **1920×1080** (grands écrans)
- **Maximisée** (recommandé, s'adapte automatiquement)

**Qualité graphique** :

*Basse qualité* (par défaut) :
- Textures pixelisées (nearest neighbor filtering)
- Pas d'antialiasing
- Optimisé pour vieux PC (4 GB RAM, HDD)
- Meilleure performance

*Haute qualité* :
- Textures lissées (linear + mipmaps)
- Antialiasing 2x
- Pour PC récents (8+ GB RAM, SSD)
- Meilleure apparence

**Sauvegarde** : Les paramètres sont sauvegardés automatiquement dans `user://bcd_settings.cfg` et restaurés au prochain démarrage.

### Découverte automatique (Recommandé)

Le client démarre avec un écran de découverte qui :
1. Cherche automatiquement les serveurs BCD sur le réseau local via mDNS
2. Affiche les serveurs trouvés avec leur nom de bibliothèque
3. Permet de sélectionner le serveur souhaité

**Prérequis** : Le serveur BCD doit avoir un `library_code` configuré dans les paramètres pour être découvert.

### Connexion manuelle

Si la découverte échoue ou pour se connecter à un serveur distant :
1. Utiliser le champ "Connexion manuelle" dans l'écran de découverte
2. Entrer l'URL complète (ex: `http://192.168.1.100:8000`)
3. Cliquer sur "Connecter"

### Changer de serveur

Un bouton 🌐 dans l'écran de sélection de classe permet de retourner à l'écran de découverte.

## Style

- **Palette de couleurs vives** adaptée aux enfants
- **Gros boutons** (≥60px hauteur)
- **Texte lisible** (≥14pt)
- **Animations** (pop-in, flash, shake) pour le feedback
- **Pas de sons** (environnement bibliothèque silencieux)
- **Qualité graphique réglable** : basse (vieux PC, pixelisé) ou haute (PC récent, lissé)

## Configuration Système

### Minimale (PC scolaires)
- **CPU**: Intel Core 2 Duo / AMD équivalent (≥2 GHz)
- **RAM**: 4 GB (l'application utilise ~200-300 MB)
- **GPU**: Intel HD Graphics 2000 ou supérieur (OpenGL 3.3+)
- **Disque**: 100 MB d'espace libre (compatible HDD)
- **OS**: Windows 10 64-bit ou Linux 64-bit
- **Réseau**: Connexion réseau local pour mDNS et API

### Recommandée
- **CPU**: Intel Core i3 ou supérieur
- **RAM**: 8 GB
- **GPU**: GPU dédié avec OpenGL 4.x
- **Disque**: SSD

## Optimisations Implémentées

Le client est optimisé pour tourner sur de **vieux PC scolaires**:

### Performance
- ✅ **OpenGL Compatibility renderer** — compatible vieux hardware
- ✅ **VSync activé** — limite à 60 FPS (économise CPU)
- ✅ **Anti-aliasing désactivé** — économise GPU
- ✅ **Textures optimisées** — compression légère
- ✅ **Limite mémoire** — 4MB max pour queue messages
- ✅ **Binaire unique** — un seul `.exe` (pas de DLL externes)

### Compatibilité Antivirus
- ✅ **Console wrapper désactivé** — évite faux positifs
- ✅ **Métadonnées Windows complètes** — informations produit
- ✅ **Pas d'obfuscation** — code transparent
- ✅ **Open source** — auditable

### Démarrage Rapide
- ✅ **Temps de démarrage** — <5 secondes sur HDD
- ✅ **Faible empreinte mémoire** — ~200MB au repos
- ✅ **Pas de dépendances** — tout embarqué

Voir [`DEPLOYMENT.md`](DEPLOYMENT.md) pour le guide de déploiement complet sur PC scolaires.

## Utilisation

1. Ouvrir le projet dans Godot 4.6+
2. Lancer la scène `main.tscn`
3. L'API BCD doit être démarrée sur `localhost:8000`

## Notes Techniques

- **Construction UI procédurale** : Pas de fichiers .tscn pour les écrans
- **Approche mockup** : Style inspiré du mockup de référence
- **API réelle** : Intégration complète avec l'API FastAPI de BCD
- **Barcode prefixes** : Automatiquement retirés (`.` pour items, `%` pour emprunteurs)

## Développement

Le code suit le style du mockup dans `~/Downloads/Godot_v4.6.2-stable_win64.exe/bcd` mais avec:
- Connexion API réelle (pas de Mock.gd)
- Fonctionnalités complètes (recherche, réservations, i18n)
- Gestion d'erreurs structurée
- Filtres configurables depuis settings API

## Déploiement sur PC Scolaires

### Vérification Compatibilité

Avant d'installer, vérifier la compatibilité du système:

```powershell
cd bcd_kids/scripts
.\check-system.ps1
```

Le script vérifie RAM, CPU, GPU, espace disque et réseau.

### Guide Complet

Voir [`DEPLOYMENT.md`](DEPLOYMENT.md) pour:
- Installation sur PC scolaires
- Configuration antivirus
- Déploiement en masse (GPO)
- Troubleshooting
- Script PowerShell de déploiement automatique

## Build & CI/CD

### Release (Production)

Pour créer une nouvelle version:
```bash
# Depuis la racine du projet
python scripts/bump_godot_version.py patch --push   # Bug fixes
python scripts/bump_godot_version.py minor --push   # New features
python scripts/bump_godot_version.py major --push   # Breaking changes
```

Voir [`RELEASING.md`](RELEASING.md) pour le guide complet.

### Build local (Development)

1. Ouvrir le projet dans Godot 4.6
2. Menu **Project → Export...**
3. Sélectionner le preset (Windows/Linux)
4. Cliquer "Export Project"

Les presets sont définis dans `export_presets.cfg`:
- **Windows Desktop** (`.exe` 64-bit)
- **Linux/X11** (`.x86_64` 64-bit)

Note: Le client Godot nécessite une connexion à un serveur BCD API (découverte automatique via mDNS).

### GitHub Actions

Deux workflows automatiques:

#### 1. Build continu (`.github/workflows/build-godot.yml`)

Déclenché sur push/PR vers `main` ou `develop` quand `bcd_kids/**` change:
- Build Windows et Linux
- Upload des artifacts (rétention 14 jours)

#### 2. Release (`.github/workflows/release-godot.yml`)

Déclenché sur tag `godot-v*.*.*`.

**Créer une release**:
```bash
# Depuis la racine du projet
python scripts/bump_godot_version.py patch --push   # 1.0.0 -> 1.0.1
# ou
python scripts/bump_godot_version.py minor --push   # 1.0.0 -> 1.1.0
# ou
python scripts/bump_godot_version.py major --push   # 1.0.0 -> 2.0.0
```

Le script:
- Met à jour la version dans `export_presets.cfg`
- Crée un commit `chore: bump godot client version to X.X.X`
- Crée un tag `godot-vX.X.X`
- Push commit + tag (avec `--push`)
- Déclenche automatiquement le workflow GitHub Actions

Actions automatiques:
- Build Windows et Linux
- Crée des archives ZIP/tar.gz
- Génère checksums SHA256
- Crée une GitHub Release avec les artifacts

### Artifacts

Les builds sont disponibles:
- **Actions runs**: Artifacts uploadés pendant 14 jours (builds) ou 90 jours (releases)
- **GitHub Releases**: Permanent pour les tags `godot-v*.*.*`

### Structure des exports

```
builds/
├── windows/
│   └── BCD-Godot.exe
└── linux/
    └── BCD-Godot.x86_64
```
