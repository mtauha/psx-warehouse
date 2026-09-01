"""MotherDuck (DuckDB) I/O for local development — mirrors bigquery_io.py's
function shapes so both satisfy extract.storage.RawStorage. Tests for the
read/write functions run against a real local DuckDB file, not live
MotherDuck — the SQL dialect is identical either way, only the connection
string differs.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb
import pandas as pd

from extract.config import ConfigError

STOCK_HISTORY_TABLE = "stock_history"
INDEX_CONSTITUENTS_TABLE = "index_constituents"

_CREATE_STOCK_HISTORY_SQL = f"""
    CREATE TABLE IF NOT EXISTS {STOCK_HISTORY_TABLE} (
        history_id VARCHAR NOT NULL,
        symbol VARCHAR NOT NULL,
        date DATE NOT NULL,
        open DOUBLE NOT NULL,
        high DOUBLE NOT NULL,
        low DOUBLE NOT NULL,
        close DOUBLE NOT NULL,
        volume BIGINT NOT NULL,
        is_anomaly BOOLEAN NOT NULL,
        row_hash VARCHAR NOT NULL,
        is_latest BOOLEAN NOT NULL,
        loaded_at TIMESTAMP NOT NULL,
        superseded_at TIMESTAMP
    )
"""

_CREATE_INDEX_CONSTITUENTS_SQL = f"""
    CREATE TABLE IF NOT EXISTS {INDEX_CONSTITUENTS_TABLE} (
        index_name VARCHAR NOT NULL,
        symbol VARCHAR NOT NULL,
        snapshot_date DATE NOT NULL,
        current_index DOUBLE,
        idx_weight DOUBLE,
        idx_point DOUBLE,
        market_cap_m DOUBLE,
        freefloat_m DOUBLE,
        shares_m DOUBLE,
        loaded_at TIMESTAMP NOT NULL
    )
"""


@dataclass(frozen=True)
class MotherDuckConfig:
    """Resolved MotherDuck-backend configuration."""

    motherduck_token: str
    md_database: str


def load_config() -> MotherDuckConfig:
    """Load MotherDuck-backend configuration from environment variables.

    Required:
        MOTHERDUCK_TOKEN: MotherDuck service token.
        MD_DATABASE: MotherDuck database name (e.g. "raw_dev").

    Raises:
        ConfigError: If a required variable is missing.
    """
    motherduck_token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not motherduck_token:
        raise ConfigError("MOTHERDUCK_TOKEN environment variable is required")

    md_database = os.environ.get("MD_DATABASE", "").strip()
    if not md_database:
        raise ConfigError("MD_DATABASE environment variable is required")

    return MotherDuckConfig(motherduck_token=motherduck_token, md_database=md_database)


def get_client(cfg: MotherDuckConfig) -> duckdb.DuckDBPyConnection:
    """Connect to the configured MotherDuck database."""
    return duckdb.connect(f"md:{cfg.md_database}?motherduck_token={cfg.motherduck_token}")


def ensure_dataset(client: duckdb.DuckDBPyConnection, cfg: MotherDuckConfig) -> None:
    """Create both raw tables if they don't already exist.

    cfg is unused here (the database is already selected by the connection
    string in get_client()) — kept in the signature for RawStorage shape
    parity with bigquery_io.ensure_dataset. Unlike BigQuery's lazy
    CREATE_IF_NEEDED on first load, both tables are created eagerly here, so
    fetch_latest_hashes never needs to handle a missing-table case.
    """
    client.execute(_CREATE_STOCK_HISTORY_SQL)
    client.execute(_CREATE_INDEX_CONSTITUENTS_SQL)


def fetch_latest_hashes(
    client: duckdb.DuckDBPyConnection, cfg: MotherDuckConfig, symbol: str
) -> dict[tuple[str, str], str]:
    """Fetch (symbol, date) -> row_hash for one symbol's is_latest rows.

    No missing-table handling needed here (unlike bigquery_io's NotFound
    catch) — ensure_dataset() always creates both tables eagerly before
    this is ever called.
    """
    rows = client.execute(
        f"SELECT symbol, date, row_hash FROM {STOCK_HISTORY_TABLE} "
        "WHERE symbol = ? AND is_latest = TRUE",
        [symbol],
    ).fetchall()
    return {(row[0], row[1].strftime("%Y-%m-%d")): row[2] for row in rows}


def load_stock_history_rows(
    client: duckdb.DuckDBPyConnection, cfg: MotherDuckConfig, rows_df: pd.DataFrame
) -> None:
    """Insert new/changed OHLCV rows into stock_history.

    rows_df must already carry symbol/date/open/high/low/close/volume/
    is_anomaly/row_hash columns (see diff.diff_against_latest). Adds
    history_id, is_latest=True, loaded_at=now, superseded_at=NULL — same
    shape as bigquery_io.load_stock_history_rows.
    """
    if rows_df.empty:
        return
    now = datetime.now(timezone.utc)

    payload = rows_df.copy()
    payload["date"] = pd.to_datetime(payload["date"]).dt.date
    payload["history_id"] = [str(uuid.uuid4()) for _ in range(len(payload))]
    payload["is_latest"] = True
    payload["loaded_at"] = now
    payload["superseded_at"] = None
    payload = payload[[
        "history_id", "symbol", "date", "open", "high", "low", "close",
        "volume", "is_anomaly", "row_hash", "is_latest", "loaded_at", "superseded_at",
    ]]

    client.register("stock_history_payload", payload)
    try:
        client.execute(
            f"INSERT INTO {STOCK_HISTORY_TABLE} SELECT * FROM stock_history_payload"
        )
    finally:
        client.unregister("stock_history_payload")


def supersede_stock_history_keys(
    client: duckdb.DuckDBPyConnection,
    cfg: MotherDuckConfig,
    keys: list[tuple[str, str]],
    run_started_at: datetime,
) -> None:
    """Flip is_latest=FALSE and set superseded_at for the given keys.

    keys are (symbol, "YYYY-MM-DD") tuples, as returned by
    diff.diff_against_latest. run_started_at must be captured (UTC) before
    this run's ticker loop started. Without the loaded_at < ? guard, a
    changed key's just-inserted replacement row (loaded_at >= run_started_at)
    would also match is_latest=TRUE for the same key and get flipped
    alongside the genuinely-prior row — the exact Critical bug the
    BigQuery write path had until the 2026-08-31 review caught it. The
    guard excludes it by construction: the replacement is always written
    during this same run (loaded_at >= run_started_at), while any
    pre-existing row from a prior run has loaded_at < run_started_at.
    """
    if not keys:
        return
    composite_keys = [f"{symbol}|{date_str}" for symbol, date_str in keys]
    placeholders = ", ".join(["?"] * len(composite_keys))
    client.execute(
        f"""
        UPDATE {STOCK_HISTORY_TABLE}
        SET is_latest = FALSE, superseded_at = CURRENT_TIMESTAMP
        WHERE is_latest = TRUE
          AND (symbol || '|' || CAST(date AS VARCHAR)) IN ({placeholders})
          AND loaded_at < ?
        """,
        [*composite_keys, run_started_at],
    )
