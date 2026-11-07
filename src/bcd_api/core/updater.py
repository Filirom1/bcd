"""Auto-update support for portable BCD builds.

Checks GitHub releases at startup and offers to install updates in-place.
Only meaningful in portable (PyInstaller frozen) mode — silently skipped otherwise.

Update mechanism:
  Windows: detached cmd.exe batch script (rename trick + robocopy retry)
  Linux:   detached shell script (overwrite-in-place is safe on Linux)

The main process calls sys.exit(0) after launching the script so all file
locks are released before the script starts copying files.
"""

import json
import logging
import shutil
import sys
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

GITHUB_REPO = "Filirom1/bcd"
_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "dialog_title": "Update available",
        "dialog_body": "BCD v{version} is available.\n\nDo you want to update now?\nThe application will restart automatically.",
        "download_title": "BCD – Update",
        "download_body": "Downloading update, please wait…",
        "error_title": "Update error",
        "error_body": "The update failed:\n{error}\n\nThe application will start normally.",
    },
    "fr": {
        "dialog_title": "Mise à jour disponible",
        "dialog_body": "BCD v{version} est disponible.\n\nVoulez-vous mettre à jour maintenant ?\nL'application redémarrera automatiquement.",
        "download_title": "BCD – Mise à jour",
        "download_body": "Téléchargement en cours, veuillez patienter…",
        "error_title": "Erreur de mise à jour",
        "error_body": "La mise à jour a échoué :\n{error}\n\nL'application démarre normalement.",
    },
}


def _detect_lang() -> str:
    """Return 'fr' when the OS UI language is French, 'en' otherwise."""
    import locale

    try:
        lang = locale.getdefaultlocale()[0] or ""
        if lang.lower().startswith("fr"):
            return "fr"
    except Exception:
        pass
    return "en"


def _t(key: str, **kwargs: str) -> str:
    """Return a localised string, interpolating any keyword arguments."""
    s = _STRINGS[_detect_lang()][key]
    return s.format(**kwargs) if kwargs else s


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------


def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert a version string to a comparable int tuple. Strips leading 'v'."""
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except ValueError:
        return (0,)


# ---------------------------------------------------------------------------
# GitHub release check
# ---------------------------------------------------------------------------


def _is_online() -> bool:
    """Return True if we can reach api.github.com on port 443.

    Uses a raw socket connect (no HTTP/TLS) for a fast, dependency-free check.
    Returns False immediately when offline — no timeout delay for the caller.
    """
    import socket

    try:
        with socket.create_connection(("api.github.com", 443), timeout=3):
            return True
    except OSError:
        return False


def check_for_update(current_version: str) -> tuple[str, str] | None:
    """Query GitHub for the latest release.

    Returns ``(new_version, download_url)`` when an update is available,
    or ``None`` if the app is up to date, offline, or the check fails.
    """
    if not _is_online():
        logger.debug("Update check skipped: no internet connection")
        return None

    try:
        req = urllib.request.Request(
            _GITHUB_API_URL,
            headers={"User-Agent": f"BCD/{current_version}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug(f"Update check skipped: {exc}")
        return None

    tag = data.get("tag_name", "")
    if not tag:
        return None

    latest = tag.lstrip("v")
    if _version_tuple(latest) <= _version_tuple(current_version):
        return None

    # Locate the platform-specific release asset
    suffix = "-Windows.zip" if sys.platform == "win32" else "-Linux.tar.gz"
    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(suffix):
            return latest, asset["browser_download_url"]

    logger.warning(f"Update v{latest} found but no asset matches this platform ({suffix})")
    return None


# ---------------------------------------------------------------------------
# Dialogs (tkinter — stdlib, no extra deps)
# ---------------------------------------------------------------------------


def _show_yes_no(title: str, message: str) -> bool:
    """Display a native yes/no dialog. Returns True when the user clicks Yes."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(title, message)
    root.destroy()
    return result


def _show_info(title: str, message: str) -> None:
    """Display a native informational dialog."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()


def _download_with_progress(url: str, dest_path: Path) -> None:
    """Download *url* to *dest_path*, showing a 'please wait' window.

    The download runs in a background thread so the window stays responsive.
    Raises the download exception (if any) after the window closes.
    """
    import threading
    import tkinter as tk

    error_holder: list[Exception | None] = [None]

    window = tk.Tk()
    window.title(_t("download_title"))
    window.resizable(False, False)
    window.geometry("380x80")
    window.update_idletasks()
    x = (window.winfo_screenwidth() - 380) // 2
    y = (window.winfo_screenheight() - 80) // 2
    window.geometry(f"380x80+{x}+{y}")
    tk.Label(
        window,
        text=_t("download_body"),
        padx=20,
        pady=20,
    ).pack()
    window.update()

    def do_download() -> None:
        try:
            urllib.request.urlretrieve(url, str(dest_path))
        except Exception as exc:
            error_holder[0] = exc
        finally:
            window.after(0, window.destroy)

    thread = threading.Thread(target=do_download, daemon=True)
    thread.start()
    window.mainloop()
    thread.join()

    if error_holder[0]:
        raise error_holder[0]


def _rollback_storage_paths(app_dir: Path) -> tuple[Path, Path, Path]:
    """Resolve the portable data, config, and SQLite paths for rollback."""
    from sqlalchemy.engine import make_url

    from src.bcd_api.core.config import settings

    app_dir = app_dir.resolve()

    def resolve_path(value: str, default: Path) -> Path:
        path = Path(value).expanduser() if value else default
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()

    data_dir = resolve_path(settings.data_dir_path, app_dir / "data")
    config_dir = resolve_path(settings.config_dir_path, app_dir / "config")
    for label, directory in (("data", data_dir), ("configuration", config_dir)):
        if directory == app_dir or app_dir.is_relative_to(directory):
            raise ValueError(
                f"The portable {label} directory cannot be the application directory or its parent."
            )
    database_url = make_url(settings.database_url)
    if database_url.get_backend_name() != "sqlite":
        raise ValueError("Automatic rollback backups require a file-based SQLite database.")
    if not database_url.database or database_url.database == ":memory:":
        raise ValueError("Automatic rollback backups require a file-based SQLite database.")
    if database_url.database.startswith("file:"):
        raise ValueError("SQLite URI database paths are not supported for automatic rollback.")
    database_path = resolve_path(database_url.database, app_dir / "data" / "bcd.db")
    return data_dir, config_dir, database_path


def _write_rollback_script_windows(
    app_dir: Path, data_dir: Path, config_dir: Path, database_path: Path
) -> None:
    """Write the Windows rollback script alongside the portable executable."""

    def batch_value(value: Path) -> str:
        rendered = str(value).replace("/", "\\").replace("%", "%%")
        if not value.is_absolute():
            return f"%APP%{rendered}"
        return rendered

    is_french = _detect_lang() == "fr"
    no_backup_message = (
        "Aucune sauvegarde de rollback n'est disponible."
        if is_french
        else "No rollback backup is available."
    )
    close_message = (
        "Fermez BCD avant d'exécuter le rollback."
        if is_french
        else "Close BCD before running the rollback script."
    )
    confirmation = (
        'choice /C ON /M "Restaurer la version, la configuration et les données précédentes ?"'
        if is_french
        else 'choice /C YN /M "Restore the previous application, configuration, and data?"'
    )
    complete_message = (
        "Rollback terminé. Redémarrage de BCD..."
        if is_french
        else "Rollback complete. Restarting BCD..."
    )
    failed_message = (
        "Échec du rollback. Vérifiez les permissions et le dossier rollback_backup."
        if is_french
        else "Rollback failed. Check file permissions and the rollback_backup directory."
    )
    lines = [
        "@echo off",
        "setlocal",
        'set "APP=%~dp0"',
        f'set "DATA_DIR={batch_value(data_dir)}"',
        f'set "CONFIG_DIR={batch_value(config_dir)}"',
        f'set "DB_PATH={batch_value(database_path)}"',
        'set "BACKUP=%APP%rollback_backup"',
        "",
        'if not exist "%BACKUP%\\bcd.exe" (',
        f"  echo {no_backup_message}",
        "  pause",
        "  exit /b 1",
        ")",
        'tasklist /FI "IMAGENAME eq bcd.exe" /NH | find /I "bcd.exe" > nul',
        "if not errorlevel 1 (",
        f"  echo {close_message}",
        "  pause",
        "  exit /b 1",
        ")",
        confirmation,
        "if errorlevel 2 exit /b 0",
        "ping -n 3 127.0.0.1 > nul",
        "",
        'copy /y "%BACKUP%\\bcd.exe" "%APP%bcd.exe" > nul',
        "if errorlevel 1 goto restore_failed",
        'if exist "%APP%_internal" rmdir /s /q "%APP%_internal"',
        'robocopy "%BACKUP%\\_internal" "%APP%_internal" /e /copy:DAT /dcopy:DAT /R:5 /W:2 > nul',
        "if errorlevel 8 goto restore_failed",
        "",
        'if exist "%BACKUP%\\data.present" (',
        '  if exist "%DATA_DIR%" rmdir /s /q "%DATA_DIR%"',
        '  mkdir "%DATA_DIR%"',
        '  robocopy "%BACKUP%\\data" "%DATA_DIR%" /e /copy:DAT /dcopy:DAT /R:5 /W:2 > nul',
        "  if errorlevel 8 goto restore_failed",
        ') else if exist "%DATA_DIR%" rmdir /s /q "%DATA_DIR%"',
        'if exist "%BACKUP%\\config.present" (',
        '  if exist "%CONFIG_DIR%" rmdir /s /q "%CONFIG_DIR%"',
        '  mkdir "%CONFIG_DIR%"',
        '  robocopy "%BACKUP%\\config" "%CONFIG_DIR%" /e /copy:DAT /dcopy:DAT /R:5 /W:2 > nul',
        "  if errorlevel 8 goto restore_failed",
        ') else if exist "%CONFIG_DIR%" rmdir /s /q "%CONFIG_DIR%"',
        "",
        'if exist "%BACKUP%\\database.present" (',
        '  for %%I in ("%DB_PATH%") do if not exist "%%~dpI" mkdir "%%~dpI"',
        '  if exist "%DB_PATH%" del /f /q "%DB_PATH%"',
        '  if exist "%DB_PATH%-wal" del /f /q "%DB_PATH%-wal"',
        '  if exist "%DB_PATH%-shm" del /f /q "%DB_PATH%-shm"',
        '  copy /y "%BACKUP%\\database" "%DB_PATH%" > nul',
        "  if errorlevel 1 goto restore_failed",
        '  if exist "%BACKUP%\\database-wal" copy /y "%BACKUP%\\database-wal" "%DB_PATH%-wal" > nul',
        "  if errorlevel 1 goto restore_failed",
        ") else (",
        '  if exist "%DB_PATH%" del /f /q "%DB_PATH%"',
        '  if exist "%DB_PATH%-wal" del /f /q "%DB_PATH%-wal"',
        '  if exist "%DB_PATH%-shm" del /f /q "%DB_PATH%-shm"',
        ")",
        "",
        'if exist "%BACKUP%\\kids_exe.present" (',
        '  copy /y "%BACKUP%\\BCD-Kids.exe" "%APP%BCD-Kids.exe" > nul',
        "  if errorlevel 1 goto restore_failed",
        ') else if exist "%APP%BCD-Kids.exe" del /f /q "%APP%BCD-Kids.exe"',
        'if exist "%BACKUP%\\kids_pck.present" (',
        '  copy /y "%BACKUP%\\BCD-Kids.pck" "%APP%BCD-Kids.pck" > nul',
        "  if errorlevel 1 goto restore_failed",
        ') else if exist "%APP%BCD-Kids.pck" del /f /q "%APP%BCD-Kids.pck"',
        "",
        f"echo {complete_message}",
        'start "" /D "%APP%" "%APP%bcd.exe"',
        "exit /b 0",
        "",
        ":restore_failed",
        f"echo {failed_message}",
        "pause",
        "exit /b 1",
    ]
    (app_dir / "rollback.bat").write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def _write_rollback_script_linux(
    app_dir: Path, data_dir: Path, config_dir: Path, database_path: Path
) -> None:
    """Write the Linux rollback script alongside the portable executable."""
    import shlex

    def shell_value(value: Path) -> str:
        if not value.is_absolute():
            return f'"$APP"/{shlex.quote(value.as_posix())}'
        return shlex.quote(str(value))

    is_french = _detect_lang() == "fr"
    no_backup_message = (
        "Aucune sauvegarde de rollback n'est disponible."
        if is_french
        else "No rollback backup is available."
    )
    close_message = (
        "Fermez BCD avant d'exécuter le rollback."
        if is_french
        else "Close BCD before running the rollback script."
    )
    confirmation = (
        'printf "Restaurer la version, la configuration et les données précédentes ? [o/N] "'
        if is_french
        else 'printf "Restore the previous application, configuration, and data? [y/N] "'
    )
    confirmation_choices = (
        'case "$CONFIRM" in o|O|oui|OUI) ;; *) echo "Rollback annulé."; exit 0 ;; esac'
        if is_french
        else 'case "$CONFIRM" in y|Y|yes|YES) ;; *) echo "Rollback cancelled."; exit 0 ;; esac'
    )
    complete_message = (
        "Rollback terminé. Redémarrage de BCD..."
        if is_french
        else "Rollback complete. Restarting BCD..."
    )
    lines = [
        "#!/bin/sh",
        "set -eu",
        'APP=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)',
        'cd "$APP"',
        'BACKUP="$APP/rollback_backup"',
        f"DATA_DIR={shell_value(data_dir)}",
        f"CONFIG_DIR={shell_value(config_dir)}",
        f"DB_PATH={shell_value(database_path)}",
        "",
        'if [ ! -f "$BACKUP/bcd" ] || [ ! -d "$BACKUP/_internal" ]; then',
        f'    echo "{no_backup_message}" >&2',
        "    exit 1",
        "fi",
        "if command -v pgrep >/dev/null 2>&1 && pgrep -x bcd >/dev/null 2>&1; then",
        f'    echo "{close_message}" >&2',
        "    exit 1",
        "fi",
        confirmation,
        "read -r CONFIRM",
        confirmation_choices,
        "",
        'cp -p "$BACKUP/bcd" "$APP/bcd.rollback"',
        'rm -f "$APP/bcd"',
        'mv "$APP/bcd.rollback" "$APP/bcd"',
        'rm -rf "$APP/_internal"',
        'cp -a "$BACKUP/_internal" "$APP/_internal"',
        "",
        'if [ -f "$BACKUP/data.present" ]; then',
        '    rm -rf "$DATA_DIR"',
        '    mkdir -p "$(dirname -- "$DATA_DIR")"',
        '    cp -a "$BACKUP/data" "$DATA_DIR"',
        "else",
        '    rm -rf "$DATA_DIR"',
        "fi",
        'if [ -f "$BACKUP/config.present" ]; then',
        '    rm -rf "$CONFIG_DIR"',
        '    mkdir -p "$(dirname -- "$CONFIG_DIR")"',
        '    cp -a "$BACKUP/config" "$CONFIG_DIR"',
        "else",
        '    rm -rf "$CONFIG_DIR"',
        "fi",
        "",
        'if [ -f "$BACKUP/database.present" ]; then',
        '    mkdir -p "$(dirname -- "$DB_PATH")"',
        '    rm -f "$DB_PATH" "$DB_PATH-wal" "$DB_PATH-shm"',
        '    cp -p "$BACKUP/database" "$DB_PATH"',
        '    if [ -f "$BACKUP/database-wal" ]; then cp -p "$BACKUP/database-wal" "$DB_PATH-wal"; fi',
        "else",
        '    rm -f "$DB_PATH" "$DB_PATH-wal" "$DB_PATH-shm"',
        "fi",
        "",
        'if [ -f "$BACKUP/kids_exe.present" ]; then',
        '    cp -p "$BACKUP/BCD-Kids.x86_64" "$APP/BCD-Kids.x86_64"',
        '    chmod +x "$APP/BCD-Kids.x86_64"',
        "else",
        '    rm -f "$APP/BCD-Kids.x86_64"',
        "fi",
        'if [ -f "$BACKUP/kids_pck.present" ]; then',
        '    cp -p "$BACKUP/BCD-Kids.pck" "$APP/BCD-Kids.pck"',
        "else",
        '    rm -f "$APP/BCD-Kids.pck"',
        "fi",
        "",
        'chmod +x "$APP/bcd"',
        f'echo "{complete_message}"',
        '"$APP/bcd" >/dev/null 2>&1 &',
    ]
    rollback_path = app_dir / "rollback.sh"
    rollback_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rollback_path.chmod(0o755)


# ---------------------------------------------------------------------------
# Windows update script
# ---------------------------------------------------------------------------


def _apply_update_windows(archive_path: Path, new_version: str, app_dir: Path) -> None:
    """Extract the ZIP, write update.bat, launch it fully detached, then exit.

    Windows file-locking strategy:
    - bcd.exe:     rename to bcd.exe.old (rename works on open handles), then copy new
    - _internal/:  robocopy /R:5 /W:2 retries up to 5 × 2 s for any briefly-locked DLL
    - BCD-Kids.*:  never locked by bcd.exe, plain copy

    The batch script uses ``ping -n 5 127.0.0.1`` (~4 s) to wait for the
    main process to fully exit before touching any files.
    """
    import subprocess
    import zipfile

    update_dir = app_dir / "update"
    extracted_dir = update_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(extracted_dir)

    pkg = f"BCD-v{new_version}-Windows"
    data_dir, config_dir, database_path = _rollback_storage_paths(app_dir)
    _write_rollback_script_windows(app_dir, data_dir, config_dir, database_path)

    # Build the batch script as a string (CRLF line endings required on Windows)
    lines = [
        "@echo off",
        "setlocal",
        'set "APP=%~dp0"',
        f'set "SRC=%APP%update\\extracted\\{pkg}"',
        f'set "DATA_DIR={str(data_dir).replace("%", "%%")}"',
        f'set "CONFIG_DIR={str(config_dir).replace("%", "%%")}"',
        f'set "DB_PATH={str(database_path).replace("%", "%%")}"',
        'set "BACKUP_NEW=%APP%rollback_backup.new"',
        "",
        "REM Wait for bcd.exe to fully exit and release all file locks (~4 s)",
        "ping -n 5 127.0.0.1 > nul",
        "",
        "REM Stage a single previous-version backup before replacing any files",
        'if exist "%BACKUP_NEW%" rmdir /s /q "%BACKUP_NEW%"',
        'mkdir "%BACKUP_NEW%"',
        'copy /y "%APP%bcd.exe" "%BACKUP_NEW%\\bcd.exe" > nul',
        "if errorlevel 1 goto backup_failed",
        'robocopy "%APP%_internal" "%BACKUP_NEW%\\_internal" /e /copy:DAT /dcopy:DAT /R:5 /W:2 > nul',
        "if errorlevel 8 goto backup_failed",
        'if exist "%DATA_DIR%\\" (',
        '  echo present>"%BACKUP_NEW%\\data.present"',
        '  robocopy "%DATA_DIR%" "%BACKUP_NEW%\\data" /e /copy:DAT /dcopy:DAT /R:5 /W:2 > nul',
        "  if errorlevel 8 goto backup_failed",
        ")",
        'if exist "%CONFIG_DIR%\\" (',
        '  echo present>"%BACKUP_NEW%\\config.present"',
        '  robocopy "%CONFIG_DIR%" "%BACKUP_NEW%\\config" /e /copy:DAT /dcopy:DAT /R:5 /W:2 > nul',
        "  if errorlevel 8 goto backup_failed",
        ")",
        'if exist "%DB_PATH%" (',
        '  echo present>"%BACKUP_NEW%\\database.present"',
        '  copy /y "%DB_PATH%" "%BACKUP_NEW%\\database" > nul',
        "  if errorlevel 1 goto backup_failed",
        '  if exist "%DB_PATH%-wal" copy /y "%DB_PATH%-wal" "%BACKUP_NEW%\\database-wal" > nul',
        "  if errorlevel 1 goto backup_failed",
        ")",
        'if exist "%APP%BCD-Kids.exe" (',
        '  echo present>"%BACKUP_NEW%\\kids_exe.present"',
        '  copy /y "%APP%BCD-Kids.exe" "%BACKUP_NEW%\\BCD-Kids.exe" > nul',
        "  if errorlevel 1 goto backup_failed",
        ")",
        'if exist "%APP%BCD-Kids.pck" (',
        '  echo present>"%BACKUP_NEW%\\kids_pck.present"',
        '  copy /y "%APP%BCD-Kids.pck" "%BACKUP_NEW%\\BCD-Kids.pck" > nul',
        "  if errorlevel 1 goto backup_failed",
        ")",
        'if exist "%APP%rollback_backup.old" rmdir /s /q "%APP%rollback_backup.old"',
        'if exist "%APP%rollback_backup" move /y "%APP%rollback_backup" "%APP%rollback_backup.old" > nul',
        'move /y "%BACKUP_NEW%" "%APP%rollback_backup" > nul',
        "if errorlevel 1 goto backup_commit_failed",
        'if exist "%APP%rollback_backup.old" rmdir /s /q "%APP%rollback_backup.old"',
        "",
        "REM Rename old exe — rename succeeds even on open handles",
        'if exist "%APP%bcd.exe.old" del /f /q "%APP%bcd.exe.old"',
        'move /y "%APP%bcd.exe" "%APP%bcd.exe.old" > nul 2>&1',
        "",
        "REM Place new exe",
        'copy /y "%SRC%\\bcd.exe" "%APP%bcd.exe" > nul',
        "",
        "REM Replace _internal with retry for briefly-locked DLLs",
        'robocopy "%SRC%\\_internal" "%APP%_internal" /e /is /it /R:5 /W:2 > nul',
        "",
        "REM Remove old exe backup",
        'if exist "%APP%bcd.exe.old" del /f /q "%APP%bcd.exe.old"',
        "",
        "REM Replace Kids client",
        'if exist "%SRC%\\BCD-Kids.exe" copy /y "%SRC%\\BCD-Kids.exe" "%APP%BCD-Kids.exe" > nul 2>&1',
        'if exist "%SRC%\\BCD-Kids.pck" copy /y "%SRC%\\BCD-Kids.pck" "%APP%BCD-Kids.pck" > nul 2>&1',
        "",
        "REM Cleanup",
        'rmdir /s /q "%APP%update" > nul 2>&1',
        "",
        "REM Restart BCD",
        'start "" "%APP%bcd.exe"',
        "REM Self-delete",
        '(goto) 2>nul & del "%~f0"',
        "exit /b 0",
        "",
        ":backup_commit_failed",
        'if exist "%APP%rollback_backup.old" if not exist "%APP%rollback_backup" move /y "%APP%rollback_backup.old" "%APP%rollback_backup" > nul',
        "",
        ":backup_failed",
        "echo Update cancelled because the previous version could not be backed up.",
        'if exist "%BACKUP_NEW%" rmdir /s /q "%BACKUP_NEW%"',
        'if exist "%APP%update" rmdir /s /q "%APP%update"',
        'if exist "%APP%bcd.exe" start "" "%APP%bcd.exe"',
        '(goto) 2>nul & del "%~f0"',
        "exit /b 1",
    ]
    bat_content = "\r\n".join(lines) + "\r\n"

    bat_path = app_dir / "update.bat"
    bat_path.write_text(bat_content, encoding="utf-8")

    # DETACHED_PROCESS (0x8) + CREATE_NEW_PROCESS_GROUP (0x200) ensures the
    # batch process is fully independent and survives our sys.exit(0).
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat_path)],
        cwd=str(app_dir),
        creationflags=0x00000008 | 0x00000200,
        close_fds=True,
    )

    sys.exit(0)


# ---------------------------------------------------------------------------
# Linux update script
# ---------------------------------------------------------------------------


def _apply_update_linux(archive_path: Path, new_version: str, app_dir: Path) -> None:
    """Extract the tar.gz, write update.sh, launch it in a new session, then exit.

    On Linux, writing directly to an executing binary or library (overwriting in-place)
    results in a "Text file busy" (ETXTBSY) error. However, unlinking (deleting) the
    files/directories is perfectly allowed even while they are running or mapped.
    Therefore, the update script unlinks the existing bcd binary and _internal directory
    before copying the new versions, avoiding any file-in-use locks.
    """
    import shlex
    import subprocess
    import tarfile

    update_dir = app_dir / "update"
    extracted_dir = update_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as tf:
        # filter='data' (Python 3.12+) blocks unsafe tar members
        try:
            tf.extractall(extracted_dir, filter="data")
        except TypeError:
            tf.extractall(extracted_dir)

    pkg = f"BCD-v{new_version}-Linux"
    data_dir, config_dir, database_path = _rollback_storage_paths(app_dir)
    _write_rollback_script_linux(app_dir, data_dir, config_dir, database_path)

    src = str(extracted_dir / pkg)
    app = str(app_dir)

    sh_lines = [
        "#!/bin/sh",
        "sleep 2",
        f"SRC={shlex.quote(src)}",
        f"APP={shlex.quote(app)}",
        f"DATA_DIR={shlex.quote(str(data_dir))}",
        f"CONFIG_DIR={shlex.quote(str(config_dir))}",
        f"DB_PATH={shlex.quote(str(database_path))}",
        'BACKUP_NEW="$APP/rollback_backup.new"',
        "",
        "backup_current_install() {",
        '    rm -rf "$BACKUP_NEW" || return 1',
        '    mkdir -p "$BACKUP_NEW" || return 1',
        '    cp -p "$APP/bcd" "$BACKUP_NEW/bcd" || return 1',
        '    cp -a "$APP/_internal" "$BACKUP_NEW/_internal" || return 1',
        '    if [ -d "$DATA_DIR" ]; then',
        '        touch "$BACKUP_NEW/data.present" && cp -a "$DATA_DIR" "$BACKUP_NEW/data" || return 1',
        "    fi",
        '    if [ -d "$CONFIG_DIR" ]; then',
        '        touch "$BACKUP_NEW/config.present" && cp -a "$CONFIG_DIR" "$BACKUP_NEW/config" || return 1',
        "    fi",
        '    if [ -f "$DB_PATH" ]; then',
        '        touch "$BACKUP_NEW/database.present" && cp -p "$DB_PATH" "$BACKUP_NEW/database" || return 1',
        '        if [ -f "$DB_PATH-wal" ]; then cp -p "$DB_PATH-wal" "$BACKUP_NEW/database-wal" || return 1; fi',
        "    fi",
        '    if [ -f "$APP/BCD-Kids.x86_64" ]; then',
        '        touch "$BACKUP_NEW/kids_exe.present" && cp -p "$APP/BCD-Kids.x86_64" "$BACKUP_NEW/BCD-Kids.x86_64" || return 1',
        "    fi",
        '    if [ -f "$APP/BCD-Kids.pck" ]; then',
        '        touch "$BACKUP_NEW/kids_pck.present" && cp -p "$APP/BCD-Kids.pck" "$BACKUP_NEW/BCD-Kids.pck" || return 1',
        "    fi",
        "}",
        "",
        "if ! backup_current_install; then",
        '    echo "Update cancelled because the previous version could not be backed up." >&2',
        '    rm -rf "$BACKUP_NEW"',
        '    "$APP/bcd" >/dev/null 2>&1 &',
        "    exit 1",
        "fi",
        'if [ -e "$APP/rollback_backup.old" ]; then rm -rf "$APP/rollback_backup.old"; fi',
        'if [ -e "$APP/rollback_backup" ]; then mv "$APP/rollback_backup" "$APP/rollback_backup.old"; fi',
        'if ! mv "$BACKUP_NEW" "$APP/rollback_backup"; then',
        '    if [ -e "$APP/rollback_backup.old" ]; then mv "$APP/rollback_backup.old" "$APP/rollback_backup"; fi',
        '    echo "Update cancelled because the rollback backup could not be installed." >&2',
        '    "$APP/bcd" >/dev/null 2>&1 &',
        "    exit 1",
        "fi",
        'rm -rf "$APP/rollback_backup.old"',
        "",
        '# Remove old _internal directory and bcd files to prevent "Text file busy" errors',
        'rm -rf "$APP/_internal"',
        'cp -r "$SRC/_internal" "$APP/_internal"',
        'rm -f "$APP/bcd"',
        'cp "$SRC/bcd" "$APP/bcd"',
        'if [ -f "$SRC/BCD-Kids.x86_64" ]; then',
        '    rm -f "$APP/BCD-Kids.x86_64"',
        '    cp "$SRC/BCD-Kids.x86_64" "$APP/BCD-Kids.x86_64"',
        "fi",
        'if [ -f "$SRC/BCD-Kids.pck" ]; then',
        '    rm -f "$APP/BCD-Kids.pck"',
        '    cp "$SRC/BCD-Kids.pck" "$APP/BCD-Kids.pck"',
        "fi",
        'chmod +x "$APP/bcd"',
        'if [ -f "$APP/BCD-Kids.x86_64" ]; then chmod +x "$APP/BCD-Kids.x86_64"; fi',
        'rm -rf "$APP/update"',
        'rm -- "$0"',
        '"$APP/bcd"',
    ]
    sh_content = "\n".join(sh_lines) + "\n"

    sh_path = app_dir / "update.sh"
    sh_path.write_text(sh_content, encoding="utf-8")
    sh_path.chmod(0o755)

    # start_new_session=True detaches the script from our process group
    subprocess.Popen(
        [str(sh_path)],
        cwd=str(app_dir),
        start_new_session=True,
        close_fds=True,
    )

    sys.exit(0)


# ---------------------------------------------------------------------------
# Startup cleanup
# ---------------------------------------------------------------------------


def _cleanup_stale_update(app_dir: Path) -> None:
    """Remove leftover files from a previously interrupted or completed update.

    Safe to call on every startup.
    """
    old_exe = app_dir / "bcd.exe.old"
    if old_exe.exists():
        try:
            old_exe.unlink()
            logger.info("Removed bcd.exe.old from previous update")
        except Exception as exc:
            logger.warning(f"Could not remove bcd.exe.old: {exc}")

    update_dir = app_dir / "update"
    if update_dir.exists():
        try:
            shutil.rmtree(update_dir)
            logger.info("Removed update/ directory from previous update")
        except Exception as exc:
            logger.warning(f"Could not remove update/: {exc}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_and_apply_update(current_version: str, app_dir: Path) -> None:
    """Check GitHub for an update and apply it if the user consents.

    Cleans up stale update artefacts first, then queries the GitHub API.
    All errors are caught and logged — this function must never block startup.
    """
    _cleanup_stale_update(app_dir)

    try:
        result = check_for_update(current_version)
        if result is None:
            return

        new_version, download_url = result
        logger.info(f"Update available: v{new_version}")

        want_update = _show_yes_no(
            _t("dialog_title"),
            _t("dialog_body", version=new_version),
        )
        if not want_update:
            logger.info(f"Update to v{new_version} declined by user")
            return

        # Download
        update_dir = app_dir / "update"
        update_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".zip" if sys.platform == "win32" else ".tar.gz"
        archive_path = update_dir / f"BCD-v{new_version}{suffix}"

        _download_with_progress(download_url, archive_path)
        logger.info(f"Update downloaded: {archive_path}")

        # Apply (exits the process)
        if sys.platform == "win32":
            _apply_update_windows(archive_path, new_version, app_dir)
        else:
            _apply_update_linux(archive_path, new_version, app_dir)

    except SystemExit:
        raise  # let sys.exit(0) propagate

    except Exception as exc:
        logger.warning(f"Update failed (non-fatal): {exc}")
        _show_info(
            _t("error_title"),
            _t("error_body", error=str(exc)),
        )
