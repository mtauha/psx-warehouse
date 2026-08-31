"""BigQuery I/O for the extraction pipeline — thin wrapper around
google-cloud-bigquery. All functions take a bigquery.Client as their first
argument (dependency injection) so callers construct it once via
get_client() and tests pass a mock instead of patching imports.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pandas as pd
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

STOCK_HISTORY_TABLE = "stock_history"
INDEX_CONSTITUENTS_TABLE = "index_constituents"

STOCK_HISTORY_SCHEMA = [
    bigquery.SchemaField("history_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("open", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("high", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("low", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("close", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("volume", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("is_anomaly", "BOOL", mode="REQUIRED"),
    bigquery.SchemaField("row_hash", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("is_latest", "BOOL", mode="REQUIRED"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("superseded_at", "TIMESTAMP", mode="NULLABLE"),
]

INDEX_CONSTITUENTS_SCHEMA = [
    bigquery.SchemaField("index_name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("snapshot_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("current_index", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("idx_weight", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("idx_point", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("market_cap_m", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("freefloat_m", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("shares_m", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
]


def get_client(project: str) -> bigquery.Client:
    """Create a BigQuery client using Application Default Credentials."""
    return bigquery.Client(project=project)


def ensure_dataset(client: bigquery.Client, project: str, dataset: str, location: str) -> None:
    """Create the raw dataset if it doesn't already exist."""
    dataset_ref = bigquery.DatasetReference(project, dataset)
    ds = bigquery.Dataset(dataset_ref)
    ds.location = location
    client.create_dataset(ds, exists_ok=True)


def fetch_latest_hashes(
    client: bigquery.Client, project: str, dataset: str, symbol: str
) -> dict[tuple[str, str], str]:
    """Fetch (symbol, date) -> row_hash for one symbol's is_latest rows.

    Scoped to a single symbol (not the whole table) so this stays cheap in
    both memory and BigQuery scan bytes as the warehouse grows — see the
    raw-layer spec's "BigQuery scan cost" section.

    Returns:
        Empty dict if raw.stock_history doesn't exist yet (first-ever run)
        or the symbol has no rows yet.
    """
    table_id = f"{project}.{dataset}.{STOCK_HISTORY_TABLE}"
    query = f"""
        SELECT symbol, date, row_hash
        FROM `{table_id}`
        WHERE symbol = @symbol AND is_latest = TRUE
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("symbol", "STRING", symbol)]
    )
    try:
        rows = client.query(query, job_config=job_config).result()
    except NotFound:
        return {}
    return {
        (row["symbol"], row["date"].strftime("%Y-%m-%d")): row["row_hash"]
        for row in rows
    }


def load_stock_history_rows(
    client: bigquery.Client, project: str, dataset: str, rows_df: pd.DataFrame
) -> None:
    """Batch-load new/changed OHLCV rows into raw.stock_history.

    rows_df must already carry symbol/date/open/high/low/close/volume/
    is_anomaly/row_hash columns (see diff.diff_against_latest). This adds
    history_id, is_latest=True, loaded_at=now, superseded_at=NULL and runs
    one load job (create-if-needed, append, partitioned on date, clustered
    on symbol).
    """
    if rows_df.empty:
        return
    table_id = f"{project}.{dataset}.{STOCK_HISTORY_TABLE}"
    now = datetime.now(timezone.utc)

    payload = rows_df.copy()
    payload["date"] = pd.to_datetime(payload["date"]).dt.date
    payload["history_id"] = [str(uuid.uuid4()) for _ in range(len(payload))]
    payload["is_latest"] = True
    payload["loaded_at"] = now
    payload["superseded_at"] = None
    payload = payload[[field.name for field in STOCK_HISTORY_SCHEMA]]

    job_config = bigquery.LoadJobConfig(
        schema=STOCK_HISTORY_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        time_partitioning=bigquery.TimePartitioning(field="date"),
        clustering_fields=["symbol"],
    )
    job = client.load_table_from_dataframe(payload, table_id, job_config=job_config)
    job.result()


def supersede_stock_history_keys(
    client: bigquery.Client, project: str, dataset: str, keys: list[tuple[str, str]]
) -> None:
    """Flip is_latest=FALSE and set superseded_at for the given keys.

    keys are (symbol, "YYYY-MM-DD") tuples, as returned by
    diff.diff_against_latest. Matched via a composite "SYMBOL|YYYY-MM-DD"
    string parameter — simpler and equally safe/parameterized compared to
    an array-of-structs query parameter.
    """
    if not keys:
        return
    table_id = f"{project}.{dataset}.{STOCK_HISTORY_TABLE}"
    composite_keys = [f"{symbol}|{date_str}" for symbol, date_str in keys]
    query = f"""
        UPDATE `{table_id}`
        SET is_latest = FALSE, superseded_at = CURRENT_TIMESTAMP()
        WHERE is_latest = TRUE
          AND CONCAT(symbol, '|', CAST(date AS STRING)) IN UNNEST(@keys)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("keys", "STRING", composite_keys)]
    )
    client.query(query, job_config=job_config).result()


def load_index_constituents(
    client: bigquery.Client,
    project: str,
    dataset: str,
    df: pd.DataFrame,
    index_name: str,
    snapshot_date: date,
) -> None:
    """Batch-load one index's constituent snapshot into raw.index_constituents.

    Always inserts (no dedup) — idx_weight/idx_point/market_cap_m move day
    to day even when membership doesn't, so every snapshot carries real
    information.
    """
    if df.empty:
        return
    table_id = f"{project}.{dataset}.{INDEX_CONSTITUENTS_TABLE}"
    now = datetime.now(timezone.utc)

    payload = df.copy()
    payload["index_name"] = index_name
    payload["snapshot_date"] = snapshot_date
    payload["loaded_at"] = now
    optional_cols = (
        "current_index", "idx_weight", "idx_point",
        "market_cap_m", "freefloat_m", "shares_m"
    )
    for optional_col in optional_cols:
        if optional_col not in payload.columns:
            payload[optional_col] = pd.NA
    payload = payload[[field.name for field in INDEX_CONSTITUENTS_SCHEMA]]

    job_config = bigquery.LoadJobConfig(
        schema=INDEX_CONSTITUENTS_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        time_partitioning=bigquery.TimePartitioning(field="snapshot_date"),
    )
    job = client.load_table_from_dataframe(payload, table_id, job_config=job_config)
    job.result()
