"""Unit tests for extract.motherduck_io. Table/write-path logic runs
against a real local temp DuckDB file (MotherDuck and local DuckDB are the
identical engine/dialect — only the connection string differs), not live
MotherDuck. get_client() itself is tested separately with duckdb.connect
mocked, since it's the one function that actually needs a real md: URL."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from extract.config import ConfigError
from extract.motherduck_io import (
    MotherDuckConfig,
    ensure_dataset,
    get_client,
    load_config,
)


def _cfg() -> MotherDuckConfig:
    return MotherDuckConfig(motherduck_token="unused", md_database="unused")


def test_load_config_reads_required_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "tok123")
    monkeypatch.setenv("MD_DATABASE", "raw_dev")

    cfg = load_config()

    assert cfg == MotherDuckConfig(motherduck_token="tok123", md_database="raw_dev")


def test_load_config_raises_when_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.setenv("MD_DATABASE", "raw_dev")

    with pytest.raises(ConfigError, match="MOTHERDUCK_TOKEN"):
        load_config()


def test_load_config_raises_when_database_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "tok123")
    monkeypatch.delenv("MD_DATABASE", raising=False)

    with pytest.raises(ConfigError, match="MD_DATABASE"):
        load_config()


@patch("extract.motherduck_io.duckdb")
def test_get_client_builds_md_connection_string(mock_duckdb: MagicMock) -> None:
    cfg = MotherDuckConfig(motherduck_token="tok123", md_database="raw_dev")

    get_client(cfg)

    mock_duckdb.connect.assert_called_once_with("md:raw_dev?motherduck_token=tok123")


def test_ensure_dataset_creates_both_tables(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))

    ensure_dataset(conn, _cfg())

    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    assert tables == {"stock_history", "index_constituents"}


def test_ensure_dataset_is_idempotent(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))

    ensure_dataset(conn, _cfg())
    ensure_dataset(conn, _cfg())  # must not raise on the second call

    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    assert tables == {"stock_history", "index_constituents"}
