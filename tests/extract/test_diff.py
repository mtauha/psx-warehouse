"""Unit tests for extract.diff — pure hash/diff functions, no I/O."""
from __future__ import annotations

import pandas as pd

from extract.diff import add_row_hashes, compute_row_hash, diff_against_latest


def _row(symbol: str = "ENGRO", close: float = 481.38) -> pd.Series:
    return pd.Series({
        "symbol": symbol,
        "date": pd.Timestamp("2024-01-05"),
        "open": 481.99,
        "high": 496.0,
        "low": 474.01,
        "close": close,
        "volume": 4496408,
        "is_anomaly": False,
    })


def test_compute_row_hash_is_deterministic() -> None:
    assert compute_row_hash(_row()) == compute_row_hash(_row())


def test_compute_row_hash_changes_with_close_price() -> None:
    assert compute_row_hash(_row(close=481.38)) != compute_row_hash(_row(close=999.99))


def test_compute_row_hash_is_64_char_hex() -> None:
    digest = compute_row_hash(_row())
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_add_row_hashes_adds_column_for_every_row() -> None:
    df = pd.DataFrame([_row(), _row(close=999.99)])
    result = add_row_hashes(df)
    assert "row_hash" in result.columns
    assert len(result) == 2
    assert result["row_hash"].iloc[0] != result["row_hash"].iloc[1]


def test_add_row_hashes_handles_empty_dataframe() -> None:
    columns = ["symbol", "date", "open", "high", "low", "close", "volume", "is_anomaly"]
    df = pd.DataFrame(columns=columns)
    result = add_row_hashes(df)
    assert result.empty
    assert "row_hash" in result.columns


def test_diff_against_latest_new_key_is_inserted_not_superseded() -> None:
    fresh = add_row_hashes(pd.DataFrame([_row()]))
    to_insert, superseded = diff_against_latest(fresh, existing={})
    assert len(to_insert) == 1
    assert superseded == []


def test_diff_against_latest_unchanged_key_is_skipped() -> None:
    fresh = add_row_hashes(pd.DataFrame([_row()]))
    existing_hash = fresh["row_hash"].iloc[0]
    to_insert, superseded = diff_against_latest(
        fresh, existing={("ENGRO", "2024-01-05"): existing_hash}
    )
    assert to_insert.empty
    assert superseded == []


def test_diff_against_latest_changed_key_is_inserted_and_superseded() -> None:
    fresh = add_row_hashes(pd.DataFrame([_row(close=500.0)]))
    to_insert, superseded = diff_against_latest(
        fresh, existing={("ENGRO", "2024-01-05"): "stale-hash-value"}
    )
    assert len(to_insert) == 1
    assert superseded == [("ENGRO", "2024-01-05")]


def test_diff_against_latest_mixed_batch() -> None:
    unchanged_row = _row(symbol="ENGRO")
    changed_row = _row(symbol="LUCK", close=500.0)
    new_row = _row(symbol="OGDC")
    fresh = add_row_hashes(pd.DataFrame([unchanged_row, changed_row, new_row]))
    unchanged_hash = fresh.loc[fresh["symbol"] == "ENGRO", "row_hash"].iloc[0]

    to_insert, superseded = diff_against_latest(
        fresh,
        existing={
            ("ENGRO", "2024-01-05"): unchanged_hash,
            ("LUCK", "2024-01-05"): "stale-hash",
        },
    )

    assert sorted(to_insert["symbol"].tolist()) == ["LUCK", "OGDC"]
    assert superseded == [("LUCK", "2024-01-05")]


def test_diff_against_latest_handles_empty_fresh_df() -> None:
    columns = ["symbol", "date", "open", "high", "low", "close", "volume", "is_anomaly"]
    fresh = add_row_hashes(pd.DataFrame(columns=columns))
    to_insert, superseded = diff_against_latest(fresh, existing={})
    assert to_insert.empty
    assert superseded == []
