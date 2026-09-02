"""Unit tests for extract.diff — pure hash/diff functions, no I/O."""
from __future__ import annotations

import pandas as pd

from extract.diff import (
    add_row_hashes,
    add_symbol_row_hashes,
    compute_row_hash,
    compute_symbol_row_hash,
    diff_against_latest,
    diff_symbols_against_latest,
)


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


def _symbol_row(**overrides: object) -> pd.Series:
    base = {
        "symbol": "ENGRO",
        "name": "Engro Corporation",
        "sector_name": "Chemical",
        "is_etf": False,
        "is_debt": False,
        "is_gem": False,
        "is_margin_eligible": True,
    }
    base.update(overrides)
    return pd.Series(base)


def test_compute_symbol_row_hash_deterministic() -> None:
    row = _symbol_row()
    assert compute_symbol_row_hash(row) == compute_symbol_row_hash(row)


def test_compute_symbol_row_hash_changes_when_sector_changes() -> None:
    row_a = _symbol_row(sector_name="Chemical")
    row_b = _symbol_row(sector_name="Fertilizer")
    assert compute_symbol_row_hash(row_a) != compute_symbol_row_hash(row_b)


def test_add_symbol_row_hashes_empty_df() -> None:
    empty = pd.DataFrame(
        columns=[
            "symbol",
            "name",
            "sector_name",
            "is_etf",
            "is_debt",
            "is_gem",
            "is_margin_eligible",
        ]
    )
    result = add_symbol_row_hashes(empty)
    assert result.empty
    assert "row_hash" in result.columns


def test_diff_symbols_against_latest_new_symbol() -> None:
    fresh = add_symbol_row_hashes(pd.DataFrame([_symbol_row().to_dict()]))

    to_insert, changed, delisted = diff_symbols_against_latest(fresh, existing={})

    assert list(to_insert["symbol"]) == ["ENGRO"]
    assert changed == []
    assert delisted == []


def test_diff_symbols_against_latest_changed_symbol() -> None:
    fresh = add_symbol_row_hashes(
        pd.DataFrame([_symbol_row(sector_name="Fertilizer").to_dict()])
    )
    old_hash = compute_symbol_row_hash(_symbol_row(sector_name="Chemical"))

    to_insert, changed, delisted = diff_symbols_against_latest(
        fresh, existing={"ENGRO": old_hash}
    )

    assert list(to_insert["symbol"]) == ["ENGRO"]
    assert changed == ["ENGRO"]
    assert delisted == []


def test_diff_symbols_against_latest_unchanged_symbol() -> None:
    row = _symbol_row()
    fresh = add_symbol_row_hashes(pd.DataFrame([row.to_dict()]))
    same_hash = compute_symbol_row_hash(row)

    to_insert, changed, delisted = diff_symbols_against_latest(
        fresh, existing={"ENGRO": same_hash}
    )

    assert to_insert.empty
    assert changed == []
    assert delisted == []


def test_diff_symbols_against_latest_delisted_symbol() -> None:
    fresh = add_symbol_row_hashes(pd.DataFrame([_symbol_row().to_dict()]))
    old_hash = compute_symbol_row_hash(_symbol_row())

    to_insert, changed, delisted = diff_symbols_against_latest(
        fresh, existing={"ENGRO": old_hash, "DELISTEDCO": "some-other-hash"}
    )

    assert to_insert.empty
    assert changed == []
    assert delisted == ["DELISTEDCO"]


def test_diff_symbols_against_latest_empty_fresh_returns_all_as_delisted() -> None:
    empty = pd.DataFrame(columns=["symbol", "row_hash"])

    to_insert, changed, delisted = diff_symbols_against_latest(
        empty, existing={"ENGRO": "h1", "LUCK": "h2"}
    )

    assert to_insert.empty
    assert changed == []
    assert sorted(delisted) == ["ENGRO", "LUCK"]
