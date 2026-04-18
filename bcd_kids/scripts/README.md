# Scripts de Déploiement BCD Godot

Scripts pour faciliter le déploiement sur PC scolaires.

## check-system.ps1

Vérification de compatibilité système avant installation.

### Utilisation

**Option 1: PowerShell normal**
```powershell
cd bcd_godot/scripts
.\check-system.ps1
```

**Option 2: Depuis l'Explorateur**
1. Clic droit sur `check-system.ps1`
2. "Exécuter avec PowerShell"

**Option 3: Bypass politique d'exécution**
```powershell
powershell -ExecutionPolicy Bypass -File check-system.ps1
```

### Vérifications

Le script vérifie:
- ✓ OS Windows 64-bit
- ✓ RAM ≥ 4 GB
- ✓ CPU ≥ 2 GHz
- ✓ GPU compatible OpenGL 3.3+ (info)
- ✓ Espace disque ≥ 500 MB
- ✓ Connexion réseau active
- ✓ (Optionnel) Connectivité serveur BCD

### Rapport

Le script peut générer un rapport `.txt` sur le bureau avec toutes les informations système.

Utile pour:
- Support technique
- Documentation des déploiements
- Vérification avant achat de matériel

## Futurs Scripts

D'autres scripts peuvent être ajoutés ici:
- `deploy-mass.ps1` — déploiement en masse via GPO
- `uninstall.ps1` — désinstallation propre
- `update.ps1` — mise à jour automatique
- `backup-settings.ps1` — sauvegarde configuration utilisateur
