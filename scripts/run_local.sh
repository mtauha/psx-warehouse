#!/bin/sh
# Local "daily sync" -- the same two steps the production Cloud Run Job runs
# (see entrypoint.sh), but against your local DuckDB file or MotherDuck
# instead of BigQuery. Schedule this with cron; see DEPLOYMENT.md's "Local
# cron scheduling" section for the crontab line and log-rotation notes.
#
# Env vars (see extract/motherduck_io.py's load_config() for the full
# contract):
#   DUCKDB_PATH               -- local .duckdb file path (default:
#                                 ./warehouse.duckdb). Leave MOTHERDUCK_TOKEN
#                                 unset to use this mode.
#   MOTHERDUCK_TOKEN,
#   MD_DATABASE                -- set both instead of DUCKDB_PATH to sync to
#                                 MotherDuck (cloud) rather than a local file.
#   DBT_TARGET                 -- which dbt profiles.yml target to build
#                                 against (default: dev; use dev_motherduck
#                                 for the MotherDuck mode above).
set -eu

cd "$(dirname "$0")/.."

export BACKEND=motherduck

uv run python -m extract.main

cd dbt
uv run --project .. dbt build --target "${DBT_TARGET:-dev}"
