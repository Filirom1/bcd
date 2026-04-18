# BCD Godot Client vX.X.X

Client Godot pour BCD (Bibliothèque Centre Documentaire) - Interface kid-friendly pour élèves CP-CM2.

## 📦 Téléchargements

- **Windows 64-bit**: `BCD-Godot-vX.X.X-Windows.zip`
- **Linux 64-bit**: `BCD-Godot-vX.X.X-Linux.tar.gz`

## 🎯 Public Visé

Interface colorée et simplifiée pour élèves de **6 à 11 ans** (CP-CM2).

## 🚀 Installation Rapide

### Windows
```powershell
# 1. Extraire
Expand-Archive BCD-Godot-vX.X.X-Windows.zip -DestinationPath C:\BCD

# 2. Lancer
C:\BCD\BCD-Godot.exe
```

### Linux
```bash
# 1. Extraire
tar -xzf BCD-Godot-vX.X.X-Linux.tar.gz -C ~/bcd

# 2. Rendre exécutable
chmod +x ~/bcd/BCD-Godot.x86_64

# 3. Lancer
~/bcd/BCD-Godot.x86_64
```

## ✨ Fonctionnalités

- ✅ **Découverte automatique** du serveur BCD (mDNS)
- ✅ **Emprunter des livres** par scan code-barres
- ✅ **Retourner des livres** rapidement
- ✅ **Rechercher dans le catalogue** avec filtres (Type, Genre, Catégorie)
- ✅ **Gérer ses réservations** (holds)
- ✅ **Bilingue** FR/EN avec changement à la volée
- 🎨 **Design coloré** kid-friendly avec gros boutons
- 🔍 **6 colonnes de résultats** pour voir plus de livres

## 💻 Configuration Système

### Minimale (PC Scolaires)
- **OS**: Windows 10 64-bit / Linux 64-bit
- **CPU**: Intel Core 2 Duo (≥2 GHz)
- **RAM**: 4 GB
- **GPU**: Intel HD Graphics 2000+ (OpenGL 3.3+)
- **Disque**: 100 MB libre (HDD compatible)
- **Réseau**: Connexion réseau local (mDNS + API)

### Recommandée
- **CPU**: Intel Core i3+
- **RAM**: 8 GB
- **GPU**: GPU dédié OpenGL 4.x
- **Disque**: SSD

## ⚡ Optimisations Performance

Cette version est **optimisée pour vieux PC scolaires**:

### Rendu
- ✅ OpenGL Compatibility renderer (compatible vieux GPU)
- ✅ VSync activé (60 FPS max, économise CPU)
- ✅ Anti-aliasing désactivé (économise GPU)
- ✅ Textures compressées S3TC

### Mémoire
- ✅ Empreinte mémoire: ~200-300 MB
- ✅ Limite queue messages: 4 MB
- ✅ Pas de fuite mémoire (testé 2h continu)

### Démarrage
- ✅ Temps de démarrage: <5 secondes sur HDD
- ✅ Binaire unique (tout embarqué dans `.exe`)
- ✅ Pas de DLL externes

## 🛡️ Compatibilité Antivirus

### Faux Positifs
Certains antivirus peuvent bloquer au premier lancement (faux positif).

**Solution**:
```powershell
# Windows Defender - Ajouter exclusion (admin requis)
Add-MpPreference -ExclusionPath "C:\BCD\BCD-Godot.exe"
```

Pour autres antivirus: Ajouter `BCD-Godot.exe` aux exclusions.

### Sécurité
- ✅ Code open-source (auditable)
- ✅ Pas de télémétrie
- ✅ Pas d'élévation privilèges
- ✅ Communication réseau limitée (HTTP vers serveur BCD uniquement)
- ✅ Métadonnées Windows complètes

## 🌐 Configuration Réseau

### Découverte Automatique (mDNS)
Le client découvre automatiquement les serveurs BCD sur le réseau local.

**Prérequis**:
- Port **5353/UDP** ouvert (mDNS)
- Port **8000/TCP** ouvert (API BCD)

### Connexion Manuelle
Si mDNS ne fonctionne pas:
1. Écran de découverte → "Connexion manuelle"
2. Entrer: `http://IP_SERVEUR:8000`
3. Cliquer "Connecter"

## 📋 Prérequis Serveur

Le client nécessite un **serveur BCD API** en cours d'exécution:

```bash
# Lancer le serveur BCD
python -m uvicorn src.bcd_api.main:app --host 0.0.0.0 --port 8000
```

Voir le README principal du projet BCD pour installer le serveur.

## 🐛 Troubleshooting

### L'application ne démarre pas
1. Vérifier antivirus (ajouter exclusion)
2. Vérifier drivers GPU (OpenGL 3.3+)
3. Tester avec `check-system.ps1`

### Serveur non trouvé
1. Vérifier que le serveur BCD est lancé
2. Vérifier pare-feu (ports 5353 UDP + 8000 TCP)
3. Utiliser connexion manuelle

### Application lente
1. Fermer applications en arrière-plan
2. Vérifier CPU/RAM usage
3. Optimiser Windows (désactiver effets visuels)

Voir [`DEPLOYMENT.md`](https://github.com/user/repo/blob/main/bcd_godot/DEPLOYMENT.md) pour guide complet.

## 📝 Notes de Version vX.X.X

### Nouveautés
- (À compléter)

### Corrections
- (À compléter)

### Améliorations
- (À compléter)

## 🔐 Vérification Intégrité

Checksums SHA256 dans `checksums.txt`.

**Windows**:
```powershell
certutil -hashfile BCD-Godot-vX.X.X-Windows.zip SHA256
```

**Linux**:
```bash
sha256sum BCD-Godot-vX.X.X-Linux.tar.gz
```

## 📚 Documentation

- **README**: [bcd_godot/README.md](https://github.com/user/repo/blob/main/bcd_godot/README.md)
- **Guide Déploiement**: [bcd_godot/DEPLOYMENT.md](https://github.com/user/repo/blob/main/bcd_godot/DEPLOYMENT.md)
- **Scripts**: [bcd_godot/scripts/](https://github.com/user/repo/tree/main/bcd_godot/scripts)

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/user/repo/issues)
- **Documentation**: README & DEPLOYMENT.md
- **Script diagnostic**: `bcd_godot/scripts/check-system.ps1`

---

**Build**: GitHub Actions  
**Commit**: `<commit-sha>`  
**Date**: `<build-date>`
