"""Unit tests for Satisfactory INI adapter (configparser-based).

Tests parse/save roundtrip, case preservation, multi-section handling,
and missing-file behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from road_poneglyph.main import _satisfactory_ini_parse, _satisfactory_ini_save


SAMPLE_INI = """\
[/Script/Engine.GameSession]
MaxPlayers=8

[/Script/FactoryGame.FGGameUserSettings]
FG.DisableSeasonalEvents=0
"""


def test_parse_multi_section(tmp_path: Path) -> None:
    """Parse a multi-section INI and get section-qualified keys."""
    ini = tmp_path / "GameUserSettings.ini"
    ini.write_text(SAMPLE_INI)
    result = _satisfactory_ini_parse(ini)
    assert result["[/Script/Engine.GameSession]/MaxPlayers"] == "8"
    assert result["[/Script/FactoryGame.FGGameUserSettings]/FG.DisableSeasonalEvents"] == "0"


def test_roundtrip_modify(tmp_path: Path) -> None:
    """Parse -> modify a value -> save -> re-parse should reflect the change."""
    ini = tmp_path / "GameUserSettings.ini"
    ini.write_text(SAMPLE_INI)
    settings = _satisfactory_ini_parse(ini)
    settings["[/Script/Engine.GameSession]/MaxPlayers"] = "16"
    _satisfactory_ini_save(ini, settings)
    reloaded = _satisfactory_ini_parse(ini)
    assert reloaded["[/Script/Engine.GameSession]/MaxPlayers"] == "16"


def test_case_preservation(tmp_path: Path) -> None:
    """Key 'MaxPlayers' stays 'MaxPlayers' (not lowercased)."""
    ini = tmp_path / "GameUserSettings.ini"
    ini.write_text(SAMPLE_INI)
    result = _satisfactory_ini_parse(ini)
    keys = list(result.keys())
    assert any("MaxPlayers" in k for k in keys), f"Case not preserved: {keys}"
    assert not any("maxplayers" in k for k in keys), f"Keys were lowercased: {keys}"


def test_multi_section_preservation(tmp_path: Path) -> None:
    """Sections survive roundtrip — both sections still present after save+re-parse."""
    ini = tmp_path / "GameUserSettings.ini"
    ini.write_text(SAMPLE_INI)
    settings = _satisfactory_ini_parse(ini)
    _satisfactory_ini_save(ini, settings)
    reloaded = _satisfactory_ini_parse(ini)
    sections = {k.split("]/")[0] + "]" for k in reloaded}
    assert "[/Script/Engine.GameSession]" in sections
    assert "[/Script/FactoryGame.FGGameUserSettings]" in sections


def test_missing_file_raises(tmp_path: Path) -> None:
    """Missing file raises FileNotFoundError (not caught inside adapter)."""
    missing = tmp_path / "does_not_exist.ini"
    with pytest.raises(FileNotFoundError):
        _satisfactory_ini_parse(missing)
