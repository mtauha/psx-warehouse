"""Unit tests for extract.main orchestration. psxdata and bigquery_io are
mocked at the module level — no live PSX or GCP access."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from psxdata.exceptions import PSXConnectionError

from extract import bigquery_io, config, motherduck_io
from extract.main import ExtractionFailed, _get_storage, main, run


def _cfg() -> config.Config:
    return config.Config(backend="bigquery", index_names=("KSE100",))


def _constituents_df() -> pd.DataFrame:
    return pd.DataFrame({"symbol": ["ENGRO", "LUCK"], "idx_weight": [5.0, 3.0]})


def _history_df(close: float) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [pd.Timestamp("2024-01-05")],
        "open": [100.0], "high": [105.0], "low": [99.0], "close": [close],
        "volume": [1000], "is_anomaly": [False],
    })


@patch("extract.main.psxdata")
def test_run_writes_batched_changes_once(mock_psxdata: MagicMock) -> None:
    mock_psxdata.indices.return_value = _constituents_df()
    mock_psxdata.stocks.side_effect = [_history_df(101.0), _history_df(102.0)]
    mock_storage = MagicMock()
    mock_storage.fetch_latest_hashes.return_value = {}

    run(_cfg(), mock_storage, MagicMock())

    mock_storage.load_index_constituents.assert_called_once()
    mock_storage.load_stock_history_rows.assert_called_once()
    written_df = mock_storage.load_stock_history_rows.call_args[0][2]
    assert len(written_df) == 2
    assert sorted(written_df["symbol"].tolist()) == ["ENGRO", "LUCK"]
    mock_storage.supersede_stock_history_keys.assert_called_once()


@patch("extract.main.psxdata")
def test_run_skips_ticker_on_fetch_failure_and_continues(
    mock_psxdata: MagicMock,
) -> None:
    mock_psxdata.indices.return_value = _constituents_df()
    mock_psxdata.stocks.side_effect = [PSXConnectionError("down"), _history_df(102.0)]
    mock_storage = MagicMock()
    mock_storage.fetch_latest_hashes.return_value = {}

    run(_cfg(), mock_storage, MagicMock())

    written_df = mock_storage.load_stock_history_rows.call_args[0][2]
    assert len(written_df) == 1
    assert written_df["symbol"].iloc[0] == "LUCK"


@patch("extract.main.psxdata")
def test_run_raises_when_constituents_fetch_fails(
    mock_psxdata: MagicMock,
) -> None:
    mock_psxdata.indices.side_effect = PSXConnectionError("down")
    mock_storage = MagicMock()

    with pytest.raises(ExtractionFailed, match="constituents"):
        run(_cfg(), mock_storage, MagicMock())

    mock_storage.load_stock_history_rows.assert_not_called()


@patch("extract.main.psxdata")
def test_run_raises_when_constituents_empty(
    mock_psxdata: MagicMock,
) -> None:
    mock_psxdata.indices.return_value = pd.DataFrame()

    with pytest.raises(ExtractionFailed, match="no constituents"):
        run(_cfg(), MagicMock(), MagicMock())


@patch("extract.main.psxdata")
def test_run_raises_when_zero_rows_fetched_across_all_tickers(
    mock_psxdata: MagicMock,
) -> None:
    mock_psxdata.indices.return_value = _constituents_df()
    mock_psxdata.stocks.return_value = pd.DataFrame()
    mock_storage = MagicMock()
    mock_storage.fetch_latest_hashes.return_value = {}

    with pytest.raises(ExtractionFailed, match="Zero OHLCV"):
        run(_cfg(), mock_storage, MagicMock())


@patch("extract.main.psxdata")
def test_run_writes_nothing_when_no_changes_detected(
    mock_psxdata: MagicMock,
) -> None:
    mock_psxdata.indices.return_value = _constituents_df()
    fresh = _history_df(101.0)
    mock_psxdata.stocks.return_value = fresh
    from extract.diff import add_row_hashes

    # fetch_latest_hashes is scoped per-symbol (bigquery_io.py), so the mock
    # must key its response on the symbol argument rather than return one
    # fixed dict — otherwise a run with >1 ticker can't express "no changes
    # detected for any ticker" (only the first ticker's hash would match).
    existing_hashes = {
        symbol: add_row_hashes(fresh.assign(symbol=symbol))["row_hash"].iloc[0]
        for symbol in ("ENGRO", "LUCK")
    }
    mock_storage = MagicMock()
    mock_storage.fetch_latest_hashes.side_effect = (
        lambda client, backend_cfg, symbol: {
            (symbol, "2024-01-05"): existing_hashes[symbol]
        }
    )

    run(_cfg(), mock_storage, MagicMock())

    mock_storage.load_stock_history_rows.assert_not_called()
    mock_storage.supersede_stock_history_keys.assert_not_called()


@patch("extract.main.psxdata")
def test_run_writes_changed_row_and_supersedes_its_key(
    mock_psxdata: MagicMock,
) -> None:
    """Regression guard for Finding 1: a CHANGED (not new) row must be both
    inserted (load_stock_history_rows) and superseded (supersede_stock_
    history_keys with that key present) — the exact path where the old fix
    superseded the just-inserted row instead of only the prior one."""
    mock_psxdata.indices.return_value = pd.DataFrame({"symbol": ["ENGRO"], "idx_weight": [5.0]})
    fresh = _history_df(101.0)
    mock_psxdata.stocks.return_value = fresh
    mock_storage = MagicMock()
    mock_storage.fetch_latest_hashes.return_value = {
        ("ENGRO", "2024-01-05"): "stale-hash-that-does-not-match"
    }

    run(_cfg(), mock_storage, MagicMock())

    mock_storage.load_stock_history_rows.assert_called_once()
    written_df = mock_storage.load_stock_history_rows.call_args[0][2]
    assert len(written_df) == 1
    assert written_df["symbol"].iloc[0] == "ENGRO"

    mock_storage.supersede_stock_history_keys.assert_called_once()
    call_args = mock_storage.supersede_stock_history_keys.call_args[0]
    superseded_keys = call_args[2]
    assert ("ENGRO", "2024-01-05") in superseded_keys
    run_started_at = call_args[3]
    assert run_started_at is not None


@patch("extract.main.psxdata")
def test_run_skips_ticker_with_malformed_row_and_continues(
    mock_psxdata: MagicMock,
) -> None:
    """Finding 3: a malformed OHLCV row (None open price) raises TypeError
    inside compute_row_hash, which is not a PSXDataError. The run must not
    abort — it should skip that ticker and still write the other valid
    ticker's data."""
    mock_psxdata.indices.return_value = _constituents_df()
    malformed_df = pd.DataFrame({
        "date": [pd.Timestamp("2024-01-05")],
        "open": [None], "high": [105.0], "low": [99.0], "close": [101.0],
        "volume": [1000], "is_anomaly": [False],
    })
    mock_psxdata.stocks.side_effect = [malformed_df, _history_df(102.0)]
    mock_storage = MagicMock()
    mock_storage.fetch_latest_hashes.return_value = {}

    run(_cfg(), mock_storage, MagicMock())

    mock_storage.load_stock_history_rows.assert_called_once()
    written_df = mock_storage.load_stock_history_rows.call_args[0][2]
    assert len(written_df) == 1
    assert written_df["symbol"].iloc[0] == "LUCK"


def test_get_storage_selects_bigquery() -> None:
    assert _get_storage("bigquery") is bigquery_io


def test_get_storage_selects_motherduck() -> None:
    assert _get_storage("motherduck") is motherduck_io


def test_get_storage_raises_on_unknown_backend() -> None:
    with pytest.raises(ExtractionFailed, match="snowflake"):
        _get_storage("snowflake")


@patch("extract.main.config.load_config", side_effect=config.ConfigError("GCP_PROJECT missing"))
def test_main_returns_1_on_config_error(mock_load_config: MagicMock) -> None:
    assert main() == 1


@patch("extract.main.bigquery_io")
@patch(
    "extract.main.run",
    side_effect=ExtractionFailed("Zero OHLCV rows fetched across all tickers"),
)
@patch("extract.main.config.load_config", return_value=_cfg())
def test_main_returns_1_on_extraction_failed(
    mock_load_config: MagicMock, mock_run: MagicMock, mock_bigquery_io: MagicMock
) -> None:
    assert main() == 1


@patch("extract.main.bigquery_io")
@patch("extract.main.run")
@patch("extract.main.config.load_config", return_value=_cfg())
def test_main_returns_0_on_success(
    mock_load_config: MagicMock, mock_run: MagicMock, mock_bigquery_io: MagicMock
) -> None:
    assert main() == 0
