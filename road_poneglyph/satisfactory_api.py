"""Minimal HTTPS API client for Satisfactory dedicated server.

Uses only stdlib (urllib.request + ssl + json). No new pip dependencies.
API docs: https://localhost:7777/api/v1 -- self-signed cert (skip verification).

Endpoints implemented:
  - HealthCheck (no auth)
  - PasswordLogin (returns bearer token, cached to disk)
  - SaveGame (admin auth required)
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


_API_BASE = "https://localhost:7777/api/v1"
_TOKEN_PATH = Path.home() / ".config" / "road-poneglyph" / "satisfactory-api-token"


def _ssl_context() -> ssl.SSLContext:
    """Create an SSL context that accepts self-signed certs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _build_request(
    function: str,
    data: Optional[dict] = None,
    token: Optional[str] = None,
    base_url: str = _API_BASE,
) -> urllib.request.Request:
    """Build a urllib Request for the Satisfactory API."""
    payload: dict = {"function": function}
    if data:
        payload["data"] = data
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return req


def _get_token_path() -> Path:
    """Return the path where the API token is cached."""
    return _TOKEN_PATH


def load_token() -> Optional[str]:
    """Load cached bearer token. Returns None if not cached."""
    path = _get_token_path()
    if not path.exists():
        return None
    return path.read_text().strip()


def save_token(token: str) -> None:
    """Cache bearer token at ~/.config/road-poneglyph/satisfactory-api-token (mode 0600)."""
    path = _get_token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + "\n")
    os.chmod(path, 0o600)


def health_check(base_url: str = _API_BASE) -> dict:
    """Call HealthCheck (no auth required). Returns parsed response or raises."""
    req = _build_request("HealthCheck", base_url=base_url)
    try:
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as e:
        raise ConnectionError(f"Health check failed: {e}") from e


def password_login(password: str, base_url: str = _API_BASE) -> str:
    """Authenticate with admin password. Returns bearer token string."""
    req = _build_request(
        "PasswordLogin",
        data={"MinimumPrivilegeLevel": "Admin", "Password": password},
        base_url=base_url,
    )
    try:
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            token = body["data"]["authenticationToken"]
            save_token(token)
            return token
    except (urllib.error.URLError, OSError, KeyError) as e:
        raise ConnectionError(f"Password login failed: {e}") from e


def save_game(
    save_name: str = "",
    token: Optional[str] = None,
    base_url: str = _API_BASE,
) -> bool:
    """Call SaveGame API. Returns True on success, raises on failure."""
    if token is None:
        token = load_token()
    if not token:
        raise RuntimeError(
            "No API token available. Run `road-poneglyph satisfactory save` "
            "interactively first to authenticate."
        )
    data = {"SaveName": save_name} if save_name else {}
    req = _build_request("SaveGame", data=data, token=token, base_url=base_url)
    try:
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=30) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError(
                "API token expired or invalid. Delete token and re-authenticate."
            ) from e
        raise ConnectionError(
            f"SaveGame failed (HTTP {e.code}): {e.reason}"
        ) from e
    except (urllib.error.URLError, OSError) as e:
        raise ConnectionError(f"SaveGame failed: {e}") from e
