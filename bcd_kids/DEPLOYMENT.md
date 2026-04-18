# Déploiement sur PC Scolaires

Guide pour déployer le client Godot BCD sur de vieux PC scolaires (4GB RAM, HDD, Windows 10).

## Configuration Système Minimale

### Matériel
- **CPU**: Intel Core 2 Duo / AMD équivalent (≥2 GHz)
- **RAM**: 4 GB minimum (l'application utilise ~200-300 MB)
- **Disque**: 100 MB d'espace libre (HDD compatible)
- **GPU**: Intel HD Graphics 2000 ou supérieur (OpenGL 3.3+)
- **Réseau**: Connexion réseau local (pour mDNS et API)

### Logiciel
- **OS**: Windows 10 (64-bit)
- **Drivers**: Pilotes graphiques à jour recommandés
- **Antivirus**: Compatible avec tous les antivirus scolaires

## Optimisations Implémentées

### Performance
1. **Renderer OpenGL Compatibility** — compatible vieux hardware
2. **VSync activé** — limite FPS à 60 pour économiser CPU
3. **MSAA désactivé** — pas d'anti-aliasing (économise GPU)
4. **Limite mémoire messages** — 4MB max (économise RAM)
5. **Textures optimisées** — compression S3TC (standard), BPTC désactivé

### Démarrage rapide
- **Binaire unique** — tout dans un seul `.exe` (embed_pck)
- **Pas de console** — évite les faux positifs antivirus
- **Métadonnées Windows** — informations produit complètes

### Résolution
- **1280x720** — résolution standard, bonne lisibilité
- **Mode fenêtre maximisée** — pas fullscreen (évite problèmes multi-écrans)
- **Resizable** — adaptable à l'écran

## Installation sur PC Scolaire

### 1. Préparation
```powershell
# Créer un dossier sur le disque local (plus rapide que réseau)
New-Item -Path "C:\BCD" -ItemType Directory -Force
```

### 2. Extraction
```powershell
# Extraire le ZIP
Expand-Archive -Path "BCD-Godot-v1.0.0-Windows.zip" -DestinationPath "C:\BCD"
```

### 3. Exclusion Antivirus (si nécessaire)
Si l'antivirus bloque l'exécution:

**Windows Defender**:
```powershell
# Ajouter une exclusion (nécessite admin)
Add-MpPreference -ExclusionPath "C:\BCD\BCD-Godot.exe"
```

**Autres antivirus** (Kaspersky, Symantec, etc.):
- Ajouter `C:\BCD\BCD-Godot.exe` aux exclusions
- Ou soumettre le fichier pour analyse (faux positif)

### 4. Lancement
```powershell
# Lancer l'application
Start-Process "C:\BCD\BCD-Godot.exe"
```

## Configuration Réseau

### mDNS Discovery
Le client découvre automatiquement les serveurs BCD via mDNS.

**Prérequis**:
- Pare-feu autorise port **5353/UDP** (mDNS)
- Pare-feu autorise port **8000/TCP** (API BCD)

**Test de connectivité**:
```powershell
# Vérifier que le serveur est joignable
Test-NetConnection -ComputerName "192.168.1.100" -Port 8000
```

### Connexion Manuelle
Si mDNS ne fonctionne pas:
1. Lancer l'application
2. Écran de découverte → section "Connexion manuelle"
3. Entrer l'URL: `http://IP_SERVEUR:8000`
4. Cliquer "Connecter"

## Troubleshooting

### L'application ne démarre pas

**Symptôme**: Double-clic sans effet ou erreur "Application bloquée"

**Solution**:
1. Vérifier que l'antivirus n'a pas mis en quarantaine
2. Ajouter une exclusion antivirus
3. Vérifier les drivers graphiques (OpenGL 3.3+ requis)

**Test OpenGL**:
```powershell
# Télécharger OpenGL Extensions Viewer
# Vérifier version OpenGL ≥ 3.3
```

### L'application est lente

**Symptôme**: Interface laggy, transitions saccadées

**Solution**:
1. Vérifier CPU usage (doit être <30% au repos)
2. Fermer les applications en arrière-plan
3. Vérifier que le disque n'est pas saturé (HDD lent)

**Optimisation Windows**:
```powershell
# Désactiver les effets visuels Windows
SystemPropertiesPerformance.exe
# → "Adjust for best performance"
```

### Pas de serveur trouvé (mDNS)

**Symptôme**: Écran de découverte reste vide

**Solutions**:
1. Vérifier que le serveur BCD est lancé
2. Vérifier que le PC et le serveur sont sur le même réseau
3. Tester le pare-feu:
   ```powershell
   # Autoriser mDNS (admin requis)
   New-NetFirewallRule -DisplayName "mDNS" -Direction Inbound -Protocol UDP -LocalPort 5353 -Action Allow
   ```
4. Utiliser la connexion manuelle en attendant

### Erreur "API non joignable"

**Symptôme**: Après sélection du serveur, erreur de connexion

**Solutions**:
1. Vérifier que le serveur BCD répond:
   ```powershell
   Invoke-WebRequest -Uri "http://IP_SERVEUR:8000/api/v1/settings"
   ```
2. Vérifier le pare-feu sur le serveur
3. Vérifier le pare-feu sur le PC client

## Déploiement en Masse (GPO)

### Script de déploiement
```powershell
# deploy-bcd-godot.ps1
# À exécuter via GPO ou SCCM

$Source = "\\serveur\partage\BCD-Godot-v1.0.0-Windows.zip"
$Destination = "C:\BCD"
$Exe = "$Destination\BCD-Godot.exe"

# Créer le dossier
New-Item -Path $Destination -ItemType Directory -Force

# Copier et extraire
Copy-Item -Path $Source -Destination "$Destination\bcd.zip"
Expand-Archive -Path "$Destination\bcd.zip" -DestinationPath $Destination -Force
Remove-Item "$Destination\bcd.zip"

# Créer un raccourci sur le bureau
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:Public\Desktop\BCD Bibliothèque.lnk")
$Shortcut.TargetPath = $Exe
$Shortcut.Description = "BCD - Bibliothèque Centre Documentaire"
$Shortcut.Save()

# Ajouter exclusion Windows Defender (si admin)
try {
    Add-MpPreference -ExclusionPath $Exe -ErrorAction SilentlyContinue
} catch {
    Write-Warning "Impossible d'ajouter l'exclusion antivirus (droits admin requis)"
}

Write-Host "Déploiement terminé : $Exe"
```

### GPO Settings
1. **Computer Configuration** → **Preferences** → **Control Panel Settings** → **Scheduled Tasks**
2. Créer une tâche unique au démarrage
3. Action: `powershell.exe -ExecutionPolicy Bypass -File \\serveur\scripts\deploy-bcd-godot.ps1`

## Performance Monitoring

### Métriques à surveiller
- **RAM usage**: <300 MB normal, >500 MB problème
- **CPU usage**: <30% repos, <60% utilisation intensive
- **Temps de démarrage**: <5 secondes normal, >10 secondes problème

### Outils
```powershell
# Monitorer les ressources
Get-Process -Name "BCD-Godot" | Select-Object CPU, WorkingSet, Handles
```

## Support

### Logs
L'application ne génère pas de logs par défaut.

Pour activer le mode debug:
```powershell
# Lancer avec console (nécessite le console wrapper)
# Note: désactivé par défaut pour éviter faux positifs antivirus
```

### Rapporter un Bug
1. Noter la configuration (CPU, RAM, GPU, OS version)
2. Noter le comportement exact
3. Créer une issue sur GitHub avec ces infos

## Compatibilité Antivirus Testée

✅ **Compatible confirmé**:
- Windows Defender (Windows 10)
- (À compléter après tests en environnement scolaire)

⚠️ **Faux positifs possibles**:
- Certains antivirus stricts peuvent bloquer au premier lancement
- Solution: Ajouter une exclusion ou soumettre pour analyse

## Notes de Sécurité

- ✅ Pas d'accès fichier système (lecture/écriture limitée)
- ✅ Pas d'élévation de privilèges
- ✅ Communication réseau limitée (HTTP vers serveur BCD uniquement)
- ✅ Pas de télémétrie ou tracking
- ✅ Pas de dépendances externes (tout embarqué)
- ✅ Code open-source (auditable)

## Références

- [Godot Performance Optimization](https://docs.godotengine.org/en/stable/tutorials/performance/index.html)
- [Windows Defender Application Control](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-defender-application-control/)
- [GPO Deployment Guide](https://learn.microsoft.com/en-us/troubleshoot/windows-server/group-policy/use-group-policy-to-install-software)
