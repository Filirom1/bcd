import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from src.bcd_cli.commands import config as config_module


def test_load_config_defaults_and_save(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.json")
    assert config_module.load_config()["language"] == "fr"
    config_module.save_config({"language": "en"})
    assert json.loads((tmp_path / "config.json").read_text())["language"] == "en"


def test_load_config_invalid_json_returns_defaults(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("invalid")
    monkeypatch.setattr(config_module, "CONFIG_FILE", path)
    assert config_module.load_config() == config_module.DEFAULT_CONFIG


def test_set_config_converts_types(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.json")
    result = CliRunner().invoke(config_module.config, ["set", "timeout", "45"])
    assert result.exit_code == 0
    assert config_module.load_config()["timeout"] == 45


def test_reset_config_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.json")
    result = CliRunner().invoke(config_module.config, ["reset"], input="y\n")
    assert result.exit_code == 0
    assert config_module.load_config() == config_module.DEFAULT_CONFIG
