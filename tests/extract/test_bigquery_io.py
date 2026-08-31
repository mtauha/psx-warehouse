"""Unit tests for extract.bigquery_io. All BigQuery calls are mocked —
no live GCP access."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
from google.api_core.exceptions import NotFound

from extract.bigquery_io import (
    ensure_dataset,
    fetch_latest_hashes,
    load_index_constituents,
    load_stock_history_rows,
    supersede_stock_history_keys,
)


def test_ensure_dataset_creates_with_exists_ok() -> None:
    client = MagicMock()

    ensure_dataset(client, "proj", "raw", "US")

    client.create_dataset.assert_called_once()
    args, kwargs = client.create_dataset.call_args
    assert kwargs.get("exists_ok") is True
    assert args[0].dataset_id == "raw"
    assert args[0].location == "US"


def test_fetch_latest_hashes_builds_dict_from_query_result() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = [
        {"symbol": "ENGRO", "date": date(2024, 1, 5), "row_hash": "abc123"},
        {"symbol": "ENGRO", "date": date(2024, 1, 4), "row_hash": "def456"},
    ]

    result = fetch_latest_hashes(client, "proj", "raw", "ENGRO")

    assert result == {
        ("ENGRO", "2024-01-05"): "abc123",
        ("ENGRO", "2024-01-04"): "def456",
    }
    query_arg = client.query.call_args[0][0]
    assert "raw.stock_history" in query_arg
    assert "is_latest = TRUE" in query_arg
    job_config = client.query.call_args[1]["job_config"]
    assert job_config.query_parameters[0].value == "ENGRO"


def test_fetch_latest_hashes_returns_empty_dict_when_table_missing() -> None:
    client = MagicMock()
    client.query.side_effect = NotFound("table not found")

    result = fetch_latest_hashes(client, "proj", "raw", "ENGRO")

    assert result == {}


def test_load_stock_history_rows_noop_on_empty_dataframe() -> None:
    client = MagicMock()

    load_stock_history_rows(client, "proj", "raw", pd.DataFrame())

    client.load_table_from_dataframe.assert_not_called()


def test_load_stock_history_rows_adds_required_columns_and_loads() -> None:
    client = MagicMock()
    rows_df = pd.DataFrame({
        "symbol": ["ENGRO"],
        "date": [pd.Timestamp("2024-01-05")],
        "open": [481.99], "high": [496.0], "low": [474.01], "close": [481.38],
        "volume": [4496408], "is_anomaly": [False], "row_hash": ["abc123"],
    })

    load_stock_history_rows(client, "proj", "raw", rows_df)

    client.load_table_from_dataframe.assert_called_once()
    payload, table_id = client.load_table_from_dataframe.call_args[0]
    assert table_id == "proj.raw.stock_history"
    assert payload["is_latest"].iloc[0] == True  # noqa: E712
    assert payload["superseded_at"].iloc[0] is None or pd.isna(payload["superseded_at"].iloc[0])
    assert isinstance(payload["history_id"].iloc[0], str) and len(payload["history_id"].iloc[0]) > 0
    assert payload["date"].iloc[0] == date(2024, 1, 5)
    job_config = client.load_table_from_dataframe.call_args[1]["job_config"]
    assert job_config.clustering_fields == ["symbol"]
    client.load_table_from_dataframe.return_value.result.assert_called_once()


def test_supersede_stock_history_keys_noop_on_empty_list() -> None:
    client = MagicMock()

    supersede_stock_history_keys(client, "proj", "raw", [])

    client.query.assert_not_called()


def test_supersede_stock_history_keys_builds_composite_key_update() -> None:
    client = MagicMock()

    supersede_stock_history_keys(client, "proj", "raw", [("ENGRO", "2024-01-04")])

    query_arg = client.query.call_args[0][0]
    assert "SET is_latest = FALSE" in query_arg
    assert "raw.stock_history" in query_arg
    job_config = client.query.call_args[1]["job_config"]
    assert job_config.query_parameters[0].values == ["ENGRO|2024-01-04"]
    client.query.return_value.result.assert_called_once()


def test_load_index_constituents_noop_on_empty_dataframe() -> None:
    client = MagicMock()

    load_index_constituents(client, "proj", "raw", pd.DataFrame(), "KSE100", date(2024, 1, 5))

    client.load_table_from_dataframe.assert_not_called()


def test_load_index_constituents_adds_index_and_snapshot_columns() -> None:
    client = MagicMock()
    df = pd.DataFrame({
        "symbol": ["ENGRO"], "current_index": [45000.0], "idx_weight": [5.2],
        "idx_point": [2000.0], "market_cap_m": [150000.0], "freefloat_m": [40.0],
    })

    load_index_constituents(client, "proj", "raw", df, "KSE100", date(2024, 1, 5))

    payload, table_id = client.load_table_from_dataframe.call_args[0]
    assert table_id == "proj.raw.index_constituents"
    assert payload["index_name"].iloc[0] == "KSE100"
    assert payload["snapshot_date"].iloc[0] == date(2024, 1, 5)
    assert pd.isna(payload["shares_m"].iloc[0])
