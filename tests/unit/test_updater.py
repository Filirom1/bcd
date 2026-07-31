import io
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# Custom dummy classes to mock tkinter completely and avoid "_tkinter" import errors and MagicMock renaming conflicts
class DummyTk:
    def __init__(self):
        pass
    def withdraw(self):
        pass
    def destroy(self):
        pass
    def title(self, title):
        pass
    def resizable(self, w, h):
        pass
    def geometry(self, geom):
        pass
    def update_idletasks(self):
        pass
    def winfo_screenwidth(self):
        return 1024
    def winfo_screenheight(self):
        return 768
    def update(self):
        pass
    def mainloop(self):
        pass
    def after(self, delay, callback):
        callback()

    @staticmethod
    def Tk():
        return DummyTk()

class DummyLabel:
    def __init__(self, parent, text, **kwargs):
        pass
    def pack(self):
        pass

DummyTk.Label = DummyLabel

class DummyMessagebox:
    mock_askyesno = MagicMock(return_value=True)
    mock_showinfo = MagicMock()

    @classmethod
    def askyesno(cls, title, message):
        return cls.mock_askyesno(title, message)
    
    @classmethod
    def showinfo(cls, title, message):
        return cls.mock_showinfo(title, message)

DummyTk.messagebox = DummyMessagebox

sys.modules["tkinter"] = DummyTk
sys.modules["tkinter.messagebox"] = DummyMessagebox

from bcd_api.core import updater


def test_version_tuple_handles_v_prefix_and_invalid_values():
    assert updater._version_tuple("v1.2.3") == (1, 2, 3)
    assert updater._version_tuple("invalid") == (0,)


def test_detect_lang_and_translation(monkeypatch):
    monkeypatch.setattr("locale.getdefaultlocale", lambda: ("fr_FR", "UTF-8"))
    assert updater._detect_lang() == "fr"
    assert "disponible" in updater._t("dialog_title")
    assert "2.0" in updater._t("dialog_body", version="2.0")


def test_check_for_update_returns_none_when_offline(monkeypatch):
    monkeypatch.setattr(updater, "_is_online", lambda: False)
    assert updater.check_for_update("1.0.0") is None


def test_check_for_update_selects_platform_asset(monkeypatch):
    monkeypatch.setattr(updater, "_is_online", lambda: True)
    payload = {
        "tag_name": "v2.0.0",
        "assets": [
            {"name": "BCD-v2.0.0-Linux.tar.gz", "browser_download_url": "https://example/update"}
        ],
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    monkeypatch.setattr(updater.sys, "platform", "linux")
    assert updater.check_for_update("1.0.0") == ("2.0.0", "https://example/update")


def test_check_for_update_ignores_current_or_malformed_release(monkeypatch):
    monkeypatch.setattr(updater, "_is_online", lambda: True)

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"tag_name": "v1.0.0"}'

    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert updater.check_for_update("1.0.0") is None


def test_cleanup_stale_update_removes_files_and_directory(tmp_path):
    (tmp_path / "bcd.exe.old").write_text("old")
    update = tmp_path / "update"
    update.mkdir()
    (update / "partial.zip").write_text("partial")
    updater._cleanup_stale_update(tmp_path)
    assert not (tmp_path / "bcd.exe.old").exists()
    assert not update.exists()


def test_cleanup_stale_update_ignores_missing_paths(tmp_path):
    updater._cleanup_stale_update(tmp_path)


def test_show_yes_no_mocked():
    """Test _show_yes_no dialog returns the mocked tkinter value."""
    DummyMessagebox.mock_askyesno.reset_mock()
    DummyMessagebox.mock_askyesno.return_value = True
    assert updater._show_yes_no("Title", "Message") is True
    DummyMessagebox.mock_askyesno.assert_called_once_with("Title", "Message")


def test_show_info_mocked():
    """Test _show_info dialog is called."""
    DummyMessagebox.mock_showinfo.reset_mock()
    updater._show_info("Title", "Message")
    DummyMessagebox.mock_showinfo.assert_called_once_with("Title", "Message")


def test_download_with_progress_mocked(tmp_path):
    """Test _download_with_progress mocks the tkinter GUI download window and urllib download."""
    dest = tmp_path / "download.zip"

    # Mock urlretrieve to succeed immediately
    with patch("urllib.request.urlretrieve") as mock_retrieve:
        updater._download_with_progress("https://example/file.zip", dest)
        mock_retrieve.assert_called_once_with("https://example/file.zip", str(dest))


def test_apply_update_windows_mocked(tmp_path, monkeypatch):
    """Test _apply_update_windows zip extraction, batch script creation and process spawning."""
    mock_zip = MagicMock()
    mock_popen = MagicMock()
    app_dir = tmp_path / "app"
    archive = tmp_path / "archive.zip"

    monkeypatch.setattr(updater.sys, "exit", lambda code: None)

    with patch("zipfile.ZipFile", return_value=mock_zip), \
         patch("subprocess.Popen", mock_popen):
        updater._apply_update_windows(archive, "2.0.0", app_dir)

        # Zip extracted?
        mock_zip.__enter__.return_value.extractall.assert_called_once()
        
        # update.bat written?
        bat_file = app_dir / "update.bat"
        assert bat_file.exists()
        content = bat_file.read_text()
        assert "ping -n 5" in content
        assert "robocopy" in content

        # Process launched?
        mock_popen.assert_called_once()


def test_apply_update_linux_mocked(tmp_path, monkeypatch):
    """Test _apply_update_linux tar extraction, shell script creation and process spawning."""
    mock_tar = MagicMock()
    mock_popen = MagicMock()
    app_dir = tmp_path / "app"
    archive = tmp_path / "archive.tar.gz"

    monkeypatch.setattr(updater.sys, "exit", lambda code: None)

    with patch("tarfile.open", return_value=mock_tar), \
         patch("subprocess.Popen", mock_popen):
        # We can pass an exception on filter parameter to trigger the fallback extraction
        mock_tar.__enter__.return_value.extractall.side_effect = [TypeError("filter not supported"), None]

        updater._apply_update_linux(archive, "2.0.0", app_dir)

        # update.sh written?
        sh_file = app_dir / "update.sh"
        assert sh_file.exists()
        content = sh_file.read_text()
        assert "sleep 2" in content
        assert "rm -rf" in content

        # Process launched?
        mock_popen.assert_called_once()


def test_check_and_apply_update_full_workflow_mocked(tmp_path, monkeypatch):
    """Test the full check_and_apply_update workflow when an update is found and accepted."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Mock all helpers so it runs completely mock-isolated without network or native windows
    monkeypatch.setattr(updater, "check_for_update", lambda version: ("2.0.0", "https://example/file.zip"))
    monkeypatch.setattr(updater, "_show_yes_no", lambda title, msg: True)
    monkeypatch.setattr(updater, "_download_with_progress", lambda url, dest: dest.write_text("partial"))
    
    mock_apply = MagicMock()
    monkeypatch.setattr(updater, "_apply_update_linux", mock_apply)
    monkeypatch.setattr(updater.sys, "platform", "linux")

    # Run workflow
    updater.check_and_apply_update("1.0.0", app_dir)

    # Verify Linux updater was called with correct download destination
    mock_apply.assert_called_once()
    assert mock_apply.call_args[0][0] == app_dir / "update" / "BCD-v2.0.0.tar.gz"
    assert mock_apply.call_args[0][1] == "2.0.0"
