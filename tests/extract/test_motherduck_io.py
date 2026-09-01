"""Unit tests for extract.motherduck_io. Table/write-path logic runs
against a real local temp DuckDB file (MotherDuck and local DuckDB are the
identical engine/dialect — only the connection string differs), not live
MotherDuck. get_client() itself is tested separately with duckdb.connect
mocked, since it's the one function that actually needs a real md: URL."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from extract.config import ConfigError
from extract.motherduck_io import (
    STOCK_HISTORY_TABLE,
    MotherDuckConfig,
    ensure_dataset,
    fetch_latest_hashes,
    get_client,
    load_config,
    load_stock_history_rows,
    supersede_stock_history_keys,
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


def test_fetch_latest_hashes_returns_dict_for_is_latest_rows(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())
    conn.execute(
        "INSERT INTO stock_history VALUES "
        "('h1', 'ENGRO', '2024-01-05', 481.99, 496.0, 474.01, 481.38, 4496408, "
        "FALSE, 'abc123', TRUE, '2024-01-05 10:00:00', NULL)"
    )

    result = fetch_latest_hashes(conn, _cfg(), "ENGRO")

    assert result == {("ENGRO", "2024-01-05"): "abc123"}


def test_fetch_latest_hashes_scoped_to_requested_symbol(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())
    conn.execute(
        "INSERT INTO stock_history VALUES "
        "('h1', 'LUCK', '2024-01-05', 1.0, 1.0, 1.0, 1.0, 1, FALSE, 'zzz', TRUE, "
        "'2024-01-05 10:00:00', NULL)"
    )

    result = fetch_latest_hashes(conn, _cfg(), "ENGRO")

    assert result == {}


def test_fetch_latest_hashes_excludes_non_latest_rows(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())
    conn.execute(
        "INSERT INTO stock_history VALUES "
        "('h1', 'ENGRO', '2024-01-05', 1.0, 1.0, 1.0, 1.0, 1, FALSE, 'old', FALSE, "
        "'2024-01-05 10:00:00', '2024-01-06 10:00:00')"
    )

    result = fetch_latest_hashes(conn, _cfg(), "ENGRO")

    assert result == {}


def test_load_stock_history_rows_noop_on_empty_dataframe(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())

    load_stock_history_rows(conn, _cfg(), pd.DataFrame())

    count = conn.execute(f"SELECT COUNT(*) FROM {STOCK_HISTORY_TABLE}").fetchone()[0]
    assert count == 0


def test_load_stock_history_rows_inserts_with_required_columns(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())
    rows_df = pd.DataFrame({
        "symbol": ["ENGRO"],
        "date": [pd.Timestamp("2024-01-05")],
        "open": [481.99], "high": [496.0], "low": [474.01], "close": [481.38],
        "volume": [4496408], "is_anomaly": [False], "row_hash": ["abc123"],
    })

    load_stock_history_rows(conn, _cfg(), rows_df)

    row = conn.execute(
        f"SELECT symbol, date, is_latest, superseded_at, history_id FROM {STOCK_HISTORY_TABLE}"
    ).fetchone()
    assert row[0] == "ENGRO"
    assert row[1] == date(2024, 1, 5)
    assert row[2] is True
    assert row[3] is None
    assert isinstance(row[4], str) and len(row[4]) > 0


def test_supersede_stock_history_keys_noop_on_empty_list(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())

    supersede_stock_history_keys(conn, _cfg(), [], datetime.now(timezone.utc))

    count = conn.execute(f"SELECT COUNT(*) FROM {STOCK_HISTORY_TABLE}").fetchone()[0]
    assert count == 0


def test_supersede_stock_history_keys_flips_prior_row(tmp_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())
    run_started_at = datetime.now(timezone.utc)
    conn.execute(
        "INSERT INTO stock_history VALUES "
        "('old-id', 'ENGRO', '2024-01-05', 1.0, 1.0, 1.0, 1.0, 1, FALSE, "
        "'stale-hash', TRUE, ?, NULL)",
        [run_started_at - timedelta(hours=1)],
    )

    supersede_stock_history_keys(conn, _cfg(), [("ENGRO", "2024-01-05")], run_started_at)

    row = conn.execute(
        f"SELECT is_latest, superseded_at FROM {STOCK_HISTORY_TABLE} WHERE history_id = 'old-id'"
    ).fetchone()
    assert row[0] is False
    assert row[1] is not None


def test_supersede_stock_history_keys_excludes_just_inserted_row(tmp_path: Path) -> None:
    """Regression guard mirroring the BigQuery Critical bug fix: inserting a
    changed row THEN superseding its key must flip only the prior row, not
    the just-inserted replacement — both share (symbol, date) and
    is_latest=TRUE at the moment supersede runs."""
    import duckdb

    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_dataset(conn, _cfg())
    run_started_at = datetime.now(timezone.utc)
    # Prior run's row — loaded before this run started.
    conn.execute(
        "INSERT INTO stock_history VALUES "
        "('old-id', 'ENGRO', '2024-01-05', 1.0, 1.0, 1.0, 1.0, 1, FALSE, "
        "'stale-hash', TRUE, ?, NULL)",
        [run_started_at - timedelta(hours=1)],
    )
    # This run's replacement row for the same key — loaded_at >= run_started_at.
    rows_df = pd.DataFrame({
        "symbol": ["ENGRO"], "date": [pd.Timestamp("2024-01-05")],
        "open": [2.0], "high": [2.0], "low": [2.0], "close": [2.0],
        "volume": [2], "is_anomaly": [False], "row_hash": ["fresh-hash"],
    })
    load_stock_history_rows(conn, _cfg(), rows_df)

    supersede_stock_history_keys(conn, _cfg(), [("ENGRO", "2024-01-05")], run_started_at)

    remaining_latest = conn.execute(
        f"SELECT row_hash FROM {STOCK_HISTORY_TABLE} WHERE is_latest = TRUE"
    ).fetchall()
    assert remaining_latest == [("fresh-hash",)]
