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
        "dialog_title":    "Update available",
        "dialog_body":     "BCD v{version} is available.\n\nDo you want to update now?\nThe application will restart automatically.",
        "download_title":  "BCD – Update",
        "download_body":   "Downloading update, please wait…",
        "error_title":     "Update error",
        "error_body":      "The update failed:\n{error}\n\nThe application will start normally.",
    },
    "fr": {
        "dialog_title":    "Mise à jour disponible",
        "dialog_body":     "BCD v{version} est disponible.\n\nVoulez-vous mettre à jour maintenant ?\nL'application redémarrera automatiquement.",
        "download_title":  "BCD – Mise à jour",
        "download_body":   "Téléchargement en cours, veuillez patienter…",
        "error_title":     "Erreur de mise à jour",
        "error_body":      "La mise à jour a échoué :\n{error}\n\nL'application démarre normalement.",
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

    # Build the batch script as a string (CRLF line endings required on Windows)
    lines = [
        "@echo off",
        "setlocal",
        'set "APP=%~dp0"',
        f'set "SRC=%APP%update\\extracted\\{pkg}"',
        "",
        "REM Wait for bcd.exe to fully exit and release all file locks (~4 s)",
        "ping -n 5 127.0.0.1 > nul",
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
        "",
        "REM Self-delete",
        '(goto) 2>nul & del "%~f0"',
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
    src = str(extracted_dir / pkg)
    app = str(app_dir)

    sh_lines = [
        "#!/bin/sh",
        "sleep 2",
        f'SRC="{src}"',
        f'APP="{app}"',
        '# Remove old _internal directory and bcd files to prevent "Text file busy" errors',
        'rm -rf "$APP/_internal"',
        'cp -r "$SRC/_internal" "$APP/_internal"',
        'rm -f "$APP/bcd"',
        'cp "$SRC/bcd" "$APP/bcd"',
        'if [ -f "$SRC/BCD-Kids.x86_64" ]; then',
        '    rm -f "$APP/BCD-Kids.x86_64"',
        '    cp "$SRC/BCD-Kids.x86_64" "$APP/BCD-Kids.x86_64"',
        'fi',
        'if [ -f "$SRC/BCD-Kids.pck" ]; then',
        '    rm -f "$APP/BCD-Kids.pck"',
        '    cp "$SRC/BCD-Kids.pck" "$APP/BCD-Kids.pck"',
        'fi',
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
