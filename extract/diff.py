"""Hash-based change detection for the raw OHLCV layer.

Pure functions only — no BigQuery or psxdata dependency, so these are
directly unit-testable without mocks.
"""
from __future__ import annotations

import hashlib

import pandas as pd


def compute_row_hash(row: pd.Series) -> str:
    """Compute a SHA-256 fingerprint of one OHLCV row's content.

    Args:
        row: A pandas Series with at least the columns symbol, date, open,
            high, low, close, volume, is_anomaly.

    Returns:
        64-character lowercase hex SHA-256 digest over
        "symbol|date|open|high|low|close|volume|is_anomaly", in that order.
    """
    parts = [
        str(row["symbol"]),
        pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
        f"{float(row['open']):.4f}",
        f"{float(row['high']):.4f}",
        f"{float(row['low']):.4f}",
        f"{float(row['close']):.4f}",
        str(int(row["volume"])),
        str(bool(row["is_anomaly"])),
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_row_hashes(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with a row_hash column computed for every row."""
    result = df.copy()
    if result.empty:
        result["row_hash"] = pd.Series(dtype="object")
        return result
    result["row_hash"] = result.apply(compute_row_hash, axis=1)
    return result


def diff_against_latest(
    fresh_df: pd.DataFrame,
    existing: dict[tuple[str, str], str],
) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Diff freshly fetched+hashed rows against one ticker's current state.

    Args:
        fresh_df: Rows for ONE symbol, already carrying a row_hash column
            (see add_row_hashes).
        existing: Mapping of (symbol, "YYYY-MM-DD") -> row_hash for this
            symbol's current is_latest=True rows, as returned by
            bigquery_io.fetch_latest_hashes. Empty dict if the symbol (or
            the table itself) has no prior state.

    Returns:
        Tuple of:
        - rows_to_insert: subset of fresh_df that is new or changed vs.
          existing (still carries row_hash and every original column).
        - superseded_keys: (symbol, "YYYY-MM-DD") keys that these new rows
          replace — i.e. existed in `existing` with a different hash. Does
          NOT include brand-new keys.
    """
    if fresh_df.empty:
        return fresh_df, []

    date_strs = pd.to_datetime(fresh_df["date"]).dt.strftime("%Y-%m-%d")
    keys = list(zip(fresh_df["symbol"].astype(str), date_strs))
    old_hashes = [existing.get(key) for key in keys]

    is_new = [h is None for h in old_hashes]
    is_changed = [
        h is not None and h != row_hash
        for h, row_hash in zip(old_hashes, fresh_df["row_hash"])
    ]
    to_insert_mask = pd.Series(
        [n or c for n, c in zip(is_new, is_changed)], index=fresh_df.index
    )

    rows_to_insert = fresh_df[to_insert_mask].reset_index(drop=True)
    superseded_keys = [key for key, changed in zip(keys, is_changed) if changed]
    return rows_to_insert, superseded_keys
