"""Unit tests for Satisfactory HTTPS API client (pure helpers only).

Tests request construction, token path, and token caching.
Does NOT call network functions (health_check, password_login, save_game).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from road_poneglyph.satisfactory_api import (
    _build_request,
    _get_token_path,
    load_token,
    save_token,
)


def test_build_request_basic() -> None:
    """_build_request constructs correct Request with JSON body and Content-Type."""
    req = _build_request("HealthCheck")
    assert req.get_header("Content-type") == "application/json"
    import json
    body = json.loads(req.data.decode("utf-8"))
    assert body["function"] == "HealthCheck"
    assert "data" not in body
    assert req.method == "POST"


def test_build_request_with_token() -> None:
    """_build_request with token adds Authorization: Bearer header."""
    req = _build_request("SaveGame", data={"SaveName": "test"}, token="mytoken123")
    assert req.get_header("Authorization") == "Bearer mytoken123"
    import json
    body = json.loads(req.data.decode("utf-8"))
    assert body["function"] == "SaveGame"
    assert body["data"]["SaveName"] == "test"


def test_get_token_path() -> None:
    """_get_token_path returns path containing satisfactory-api-token."""
    path = _get_token_path()
    assert "satisfactory-api-token" in str(path)
    assert ".config/road-poneglyph" in str(path)


def test_save_and_load_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """save_token writes file with 0600 permissions; load_token reads it back."""
    token_file = tmp_path / "satisfactory-api-token"
    monkeypatch.setattr(
        "road_poneglyph.satisfactory_api._TOKEN_PATH", token_file
    )
    save_token("test-bearer-token-abc")
    assert token_file.exists()
    # Check 0600 permissions
    mode = oct(token_file.stat().st_mode & 0o777)
    assert mode == "0o600", f"Expected 0600, got {mode}"
    loaded = load_token()
    assert loaded == "test-bearer-token-abc"


def test_save_token_creates_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """save_token creates parent directory if missing."""
    token_file = tmp_path / "subdir" / "nested" / "satisfactory-api-token"
    monkeypatch.setattr(
        "road_poneglyph.satisfactory_api._TOKEN_PATH", token_file
    )
    save_token("another-token")
    assert token_file.exists()
    assert token_file.parent.exists()


def test_load_token_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """load_token returns None if file does not exist."""
    token_file = tmp_path / "nonexistent-token"
    monkeypatch.setattr(
        "road_poneglyph.satisfactory_api._TOKEN_PATH", token_file
    )
    result = load_token()
    assert result is None
