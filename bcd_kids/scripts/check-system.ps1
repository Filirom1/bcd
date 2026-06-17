# check-system.ps1
# Script pour vérifier la compatibilité système avant d'installer BCD Godot Client

Write-Host "=== BCD Godot Client - Vérification Système ===" -ForegroundColor Cyan
Write-Host ""

$compatible = $true

# Vérifier OS
Write-Host "[1/6] Vérification OS..." -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
$osName = $os.Caption
$osArch = $os.OSArchitecture

Write-Host "  OS: $osName ($osArch)"

if ($osArch -ne "64-bit") {
    Write-Host "  ✗ ERREUR: Windows 64-bit requis" -ForegroundColor Red
    $compatible = $false
} else {
    Write-Host "  ✓ OK" -ForegroundColor Green
}
Write-Host ""

# Vérifier RAM
Write-Host "[2/6] Vérification RAM..." -ForegroundColor Yellow
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
Write-Host "  RAM installée: $ram GB"

if ($ram -lt 4) {
    Write-Host "  ✗ ERREUR: Minimum 4 GB requis" -ForegroundColor Red
    $compatible = $false
} elseif ($ram -lt 8) {
    Write-Host "  ⚠ AVERTISSEMENT: 8 GB recommandés pour de meilleures performances" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ OK" -ForegroundColor Green
}
Write-Host ""

# Vérifier CPU
Write-Host "[3/6] Vérification CPU..." -ForegroundColor Yellow
$cpu = Get-CimInstance Win32_Processor
$cpuName = $cpu.Name
$cpuSpeed = [math]::Round($cpu.MaxClockSpeed / 1000, 2)
$cpuCores = $cpu.NumberOfCores

Write-Host "  CPU: $cpuName"
Write-Host "  Vitesse: $cpuSpeed GHz"
Write-Host "  Coeurs: $cpuCores"

if ($cpuSpeed -lt 2.0) {
    Write-Host "  ⚠ AVERTISSEMENT: CPU lent (<2 GHz), performances limitées" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ OK" -ForegroundColor Green
}
Write-Host ""

# Vérifier GPU (optionnel)
Write-Host "[4/6] Vérification GPU..." -ForegroundColor Yellow
try {
    $gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
    $gpuName = $gpu.Name
    Write-Host "  GPU: $gpuName"
    Write-Host "  ℹ Nécessite OpenGL 3.3+ (vérifier manuellement si problèmes)" -ForegroundColor Cyan
} catch {
    Write-Host "  ⚠ Impossible de détecter le GPU" -ForegroundColor Yellow
}
Write-Host ""

# Vérifier espace disque
Write-Host "[5/6] Vérification espace disque..." -ForegroundColor Yellow
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeSpaceGB = [math]::Round($disk.FreeSpace / 1GB, 2)

Write-Host "  Espace libre C:\: $freeSpaceGB GB"

if ($freeSpaceGB -lt 0.5) {
    Write-Host "  ✗ ERREUR: Minimum 500 MB requis" -ForegroundColor Red
    $compatible = $false
} else {
    Write-Host "  ✓ OK" -ForegroundColor Green
}
Write-Host ""

# Vérifier connectivité réseau
Write-Host "[6/6] Vérification réseau..." -ForegroundColor Yellow
$network = Get-NetAdapter | Where-Object {$_.Status -eq "Up"}

if ($network.Count -eq 0) {
    Write-Host "  ✗ ERREUR: Aucune connexion réseau active" -ForegroundColor Red
    Write-Host "  Le client nécessite une connexion réseau pour communiquer avec le serveur BCD" -ForegroundColor Yellow
    $compatible = $false
} else {
    Write-Host "  ✓ Connexion réseau active détectée" -ForegroundColor Green
}
Write-Host ""

# Test de connectivité serveur (optionnel)
Write-Host "Test de connectivité serveur BCD (optionnel)..." -ForegroundColor Yellow
$serverIP = Read-Host "  Entrer l'IP du serveur BCD (ou appuyer sur Entrée pour passer)"

if ($serverIP) {
    try {
        $test = Test-NetConnection -ComputerName $serverIP -Port 8888 -WarningAction SilentlyContinue
        if ($test.TcpTestSucceeded) {
            Write-Host "  ✓ Serveur BCD joignable sur $serverIP`:8888" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Serveur BCD non joignable (vérifier pare-feu)" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ⚠ Impossible de tester la connexion" -ForegroundColor Yellow
    }
}
Write-Host ""

# Résumé
Write-Host "=== Résumé ===" -ForegroundColor Cyan

if ($compatible) {
    Write-Host "✓ Système COMPATIBLE avec BCD Godot Client" -ForegroundColor Green
    Write-Host ""
    Write-Host "Vous pouvez installer l'application en suivant ces étapes:" -ForegroundColor White
    Write-Host "1. Extraire BCD-Godot-vX.X.X-Windows.zip dans C:\BCD" -ForegroundColor Gray
    Write-Host "2. Lancer C:\BCD\BCD-Godot.exe" -ForegroundColor Gray
    Write-Host "3. Si l'antivirus bloque, ajouter une exclusion pour C:\BCD\BCD-Godot.exe" -ForegroundColor Gray
} else {
    Write-Host "✗ Système NON COMPATIBLE" -ForegroundColor Red
    Write-Host ""
    Write-Host "Corrigez les erreurs ci-dessus avant d'installer." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Documentation complète: bcd_godot/DEPLOYMENT.md" -ForegroundColor Cyan
Write-Host ""

# Optionnel: générer un rapport
$generateReport = Read-Host "Générer un rapport de compatibilité (o/n)?"
if ($generateReport -eq "o" -or $generateReport -eq "O") {
    $reportPath = "$env:USERPROFILE\Desktop\BCD-SystemCheck.txt"

    @"
BCD Godot Client - Rapport de Compatibilité Système
Généré le: $(Get-Date)
========================================================

OS: $osName ($osArch)
RAM: $ram GB
CPU: $cpuName ($cpuSpeed GHz, $cpuCores coeurs)
GPU: $gpuName
Espace disque C:\: $freeSpaceGB GB
Réseau: $($network.Count) connexion(s) active(s)

Statut: $(if ($compatible) { "COMPATIBLE" } else { "NON COMPATIBLE" })

Pour plus d'informations, voir:
- bcd_godot/README.md
- bcd_godot/DEPLOYMENT.md
"@ | Out-File -FilePath $reportPath -Encoding UTF8

    Write-Host "Rapport sauvegardé: $reportPath" -ForegroundColor Green
}

Write-Host ""
Read-Host "Appuyer sur Entrée pour quitter"
