"""MotherDuck (DuckDB) I/O for local development — mirrors bigquery_io.py's
function shapes so both satisfy extract.storage.RawStorage. Tests for the
read/write functions run against a real local DuckDB file, not live
MotherDuck — the SQL dialect is identical either way, only the connection
string differs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import duckdb

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
