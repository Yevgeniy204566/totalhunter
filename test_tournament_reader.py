import os
import json
import pytest
import tournament_reader as tr


def test_load_config_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tr, "CONFIG_PATH", os.path.join(str(tmp_path), "tournament_config.json"))
    with pytest.raises(FileNotFoundError) as exc_info:
        tr.load_config()
    assert "tournament_config.example.json" in str(exc_info.value)


def test_load_config_missing_keys_raises(tmp_path, monkeypatch):
    config_path = os.path.join(str(tmp_path), "tournament_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"api_url": "https://api.total-hunter.com"}, f)
    monkeypatch.setattr(tr, "CONFIG_PATH", config_path)
    with pytest.raises(ValueError) as exc_info:
        tr.load_config()
    assert "api_token" in str(exc_info.value)


def test_load_config_valid(tmp_path, monkeypatch):
    config_path = os.path.join(str(tmp_path), "tournament_config.json")
    data = {
        "api_url": "https://api.total-hunter.com",
        "api_token": "secret123",
        "alliance_tag": "K229",
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    monkeypatch.setattr(tr, "CONFIG_PATH", config_path)
    result = tr.load_config()
    assert result == data
