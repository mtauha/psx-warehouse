"""Extraction job entrypoint: KSE-100 constituents + OHLCV history -> raw.

Run via `python -m extract.main`. Orchestrates:
  1. Fetch + load each configured index's constituent snapshot.
  2. Sequentially fetch OHLCV history per constituent symbol, diff it
     per-ticker against current raw state, accumulate changes.
  3. Flush accumulated changes once: one batch load + one targeted UPDATE.
"""
from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone

import pandas as pd
import psxdata
from psxdata.exceptions import PSXDataError

from extract import bigquery_io, config
from extract.diff import add_row_hashes, diff_against_latest

logger = logging.getLogger(__name__)


class ExtractionFailed(Exception):
    """Raised for conditions that should exit the job non-zero."""


def run(cfg: config.Config) -> None:
    """Execute one extraction run against the given configuration.

    Raises:
        ExtractionFailed: If a configured index's constituents can't be
            fetched or come back empty, or if zero OHLCV rows are fetched
            across every ticker in the run. BigQuery write failures are
            not caught here — they propagate as uncaught exceptions,
            which is the intended fail-loud behavior.
    """
    run_started_at = datetime.now(timezone.utc)
    client = bigquery_io.get_client(cfg.gcp_project)
    bigquery_io.ensure_dataset(client, cfg.gcp_project, cfg.bq_dataset, cfg.bq_location)

    today = date.today()
    all_symbols: set[str] = set()

    for index_name in cfg.index_names:
        try:
            constituents_df = psxdata.indices(index_name, cache=False)
        except PSXDataError as exc:
            raise ExtractionFailed(
                f"Failed to fetch constituents for index {index_name}: {exc}"
            ) from exc

        if constituents_df.empty:
            raise ExtractionFailed(f"Index {index_name} returned no constituents")

        bigquery_io.load_index_constituents(
            client, cfg.gcp_project, cfg.bq_dataset, constituents_df, index_name, today
        )
        all_symbols.update(constituents_df["symbol"].tolist())

    rows_to_insert_parts: list[pd.DataFrame] = []
    all_superseded_keys: list[tuple[str, str]] = []
    total_fetched_rows = 0

    for symbol in sorted(all_symbols):
        try:
            history_df = psxdata.stocks(symbol, cache=False)
        except PSXDataError as exc:
            logger.warning("Skipping %s: fetch failed (%s)", symbol, exc)
            continue

        if history_df.empty:
            logger.warning("Skipping %s: no history returned", symbol)
            continue

        total_fetched_rows += len(history_df)
        history_df = history_df.copy()
        history_df["symbol"] = symbol

        try:
            hashed_df = add_row_hashes(history_df)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Skipping %s: malformed row data (%s)", symbol, exc)
            continue

        existing = bigquery_io.fetch_latest_hashes(
            client, cfg.gcp_project, cfg.bq_dataset, symbol
        )
        rows_to_insert, superseded_keys = diff_against_latest(hashed_df, existing)

        if not rows_to_insert.empty:
            rows_to_insert_parts.append(rows_to_insert)
        all_superseded_keys.extend(superseded_keys)

    if total_fetched_rows == 0:
        raise ExtractionFailed("Zero OHLCV rows fetched across all tickers")

    if rows_to_insert_parts:
        all_rows_to_insert = pd.concat(rows_to_insert_parts, ignore_index=True)
        bigquery_io.load_stock_history_rows(
            client, cfg.gcp_project, cfg.bq_dataset, all_rows_to_insert
        )
        bigquery_io.supersede_stock_history_keys(
            client, cfg.gcp_project, cfg.bq_dataset, all_superseded_keys, run_started_at
        )
        logger.info("Extraction complete: %d rows written", len(all_rows_to_insert))
    else:
        logger.info("Extraction complete: no changes detected, nothing written")


def main() -> int:
    """Process entrypoint. Returns the process exit code."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        cfg = config.load_config()
        run(cfg)
    except (config.ConfigError, ExtractionFailed) as exc:
        logger.error(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
