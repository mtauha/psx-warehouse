"""Unit tests for extract.config."""
from __future__ import annotations

import pytest

from extract.config import Config, ConfigError, load_config


def test_load_config_defaults_to_bigquery_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND", raising=False)
    monkeypatch.delenv("INDEX_NAMES", raising=False)

    cfg = load_config()

    assert cfg == Config(backend="bigquery", index_names=("KSE100",))


def test_load_config_reads_custom_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND", "motherduck")
    monkeypatch.delenv("INDEX_NAMES", raising=False)

    cfg = load_config()

    assert cfg.backend == "motherduck"


def test_load_config_parses_custom_index_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND", raising=False)
    monkeypatch.setenv("INDEX_NAMES", "KSE100, KSE30 ,ALLSHR")

    cfg = load_config()

    assert cfg.index_names == ("KSE100", "KSE30", "ALLSHR")


def test_load_config_raises_when_index_names_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND", raising=False)
    monkeypatch.setenv("INDEX_NAMES", "  , ,")

    with pytest.raises(ConfigError, match="INDEX_NAMES"):
        load_config()
