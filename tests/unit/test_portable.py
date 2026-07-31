from pathlib import Path

from bcd_api.core import portable


def test_development_app_dir_is_project_root():
    assert portable.get_app_dir() == Path(__file__).parents[2]


def test_portable_detection(monkeypatch):
    monkeypatch.setattr(portable.sys, "frozen", True, raising=False)
    monkeypatch.setattr(portable.sys, "_MEIPASS", "/tmp/bcd", raising=False)
    assert portable.is_portable() is True


def test_data_and_config_dirs_use_environment(monkeypatch, tmp_path):
    data = tmp_path / "data"
    config = tmp_path / "config"
    monkeypatch.setenv("DATA_DIR_PATH", str(data))
    monkeypatch.setenv("CONFIG_DIR_PATH", str(config))
    assert portable.get_data_dir() == data
    assert portable.get_config_dir() == config
    assert data.is_dir() and config.is_dir()


def test_bundled_resource_supports_meipass_and_internal(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "_internal" / "assets").mkdir(parents=True)
    resource = bundle / "_internal" / "assets" / "help.txt"
    resource.write_text("help")
    monkeypatch.setattr(portable.sys, "frozen", True, raising=False)
    monkeypatch.setattr(portable.sys, "_MEIPASS", str(bundle), raising=False)
    assert portable.get_bundled_resource("assets/help.txt") == resource


def test_create_default_env_file(tmp_path, monkeypatch):
    monkeypatch.setattr(portable.sys, "platform", "linux")
    target = tmp_path / ".env"
    portable.create_default_env_file(target)
    content = target.read_text()
    assert "API_HOST=127.0.0.1" in content
    assert "KIDS_CLIENT_PATH=./BCD-Kids.x86_64" in content


def test_initialize_portable_environment_is_noop_in_development(monkeypatch, tmp_path):
    monkeypatch.delenv("DATA_DIR_PATH", raising=False)
    monkeypatch.setattr(portable, "is_portable", lambda: False)
    portable.initialize_portable_environment()
    assert not (tmp_path / "sample_imports").exists()


def test_get_app_dir_portable(monkeypatch, tmp_path):
    monkeypatch.setattr(portable, "is_portable", lambda: True)
    executable = tmp_path / "bin" / "bcd.exe"
    monkeypatch.setattr(portable.sys, "executable", str(executable))
    assert portable.get_app_dir() == tmp_path / "bin"


def test_get_migrations_dir_portable(monkeypatch, tmp_path):
    monkeypatch.setattr(portable, "is_portable", lambda: True)
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    monkeypatch.setattr(portable, "get_app_dir", lambda: app_dir)

    # _internal/migrations exists
    internal_migrations = app_dir / "_internal" / "migrations"
    internal_migrations.mkdir(parents=True)
    assert portable.get_migrations_dir() == internal_migrations

    # Fallback when _internal/migrations does not exist
    internal_migrations.rmdir()
    assert portable.get_migrations_dir() == app_dir / "migrations"


def test_get_alembic_ini_path_portable(monkeypatch, tmp_path):
    monkeypatch.setattr(portable, "is_portable", lambda: True)
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    monkeypatch.setattr(portable, "get_app_dir", lambda: app_dir)

    # _internal/alembic.ini exists
    internal_ini = app_dir / "_internal" / "alembic.ini"
    internal_ini.parent.mkdir(parents=True, exist_ok=True)
    internal_ini.touch()
    assert portable.get_alembic_ini_path() == internal_ini

    # Fallback to app_dir/alembic.ini
    internal_ini.unlink()
    assert portable.get_alembic_ini_path() == app_dir / "alembic.ini"


def test_create_default_env_file_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(portable.sys, "platform", "win32")
    target = tmp_path / ".env"
    portable.create_default_env_file(target)
    content = target.read_text()
    assert "KIDS_CLIENT_PATH=BCD-Kids.exe" in content


def test_initialize_portable_environment_portable(monkeypatch, tmp_path):
    monkeypatch.setattr(portable, "is_portable", lambda: True)
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    monkeypatch.setattr(portable, "get_app_dir", lambda: app_dir)

    portable.initialize_portable_environment()
    assert (app_dir / "data" / "sample_imports").is_dir()
    assert (app_dir / "config" / ".env").is_file()

