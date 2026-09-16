# PSX Analytics Warehouse

[![CI](https://github.com/mtauha/psx-warehouse/actions/workflows/ci.yml/badge.svg)](https://github.com/mtauha/psx-warehouse/actions/workflows/ci.yml)
[![Docker Publish](https://github.com/mtauha/psx-warehouse/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/mtauha/psx-warehouse/actions/workflows/docker-publish.yml)
[![dbt docs](https://github.com/mtauha/psx-warehouse/actions/workflows/dbt-docs.yml/badge.svg)](https://github.com/mtauha/psx-warehouse/actions/workflows/dbt-docs.yml)
[![Docker Hub](https://img.shields.io/badge/docker-mtauha%2Fpsx--warehouse-blue?logo=docker)](https://hub.docker.com/r/mtauha/psx-warehouse)
[![License: MIT](https://img.shields.io/github/license/mtauha/psx-warehouse)](LICENSE.md)

dbt-core + BigQuery analytics layer on top of the [`psxdata`](https://github.com/mtauha/psxdata) SDK, turning raw PSX OHLCV data into tested, analysis-ready marts.

A personal analytics warehouse on PSX/KSE-100 stocks.

**Status:** under construction. Raw-layer extraction and the dbt marts layer
are built and tested against MotherDuck. In production GCP: the service
account, its BigQuery IAM bindings, and the `raw` dataset are live; the
Cloud Run Job and Cloud Scheduler job are defined and `terraform
validate`-clean but not yet created, pending full GCP billing activation.
See `DEPLOYMENT.md` for the full setup and current state.

## Layout

- `extract/` — Python extraction from the `psxdata` SDK into raw tables
  (BigQuery and MotherDuck; see `CONTRIBUTING.md` for adding another backend)
- `dbt/` — dbt-core project (staging / intermediate / marts), built on
  MotherDuck/DuckDB for dev and targeting BigQuery for prod:
  - `models/staging/` — one staging model per raw source (`stg_stock_history`,
    `stg_symbols`, `stg_sectors`, `stg_index_constituents`, `stg_screener`)
  - `snapshots/` — `dim_tickers`, a Type-2 snapshot of ticker attributes
    (with delisting handling)
  - `models/marts/` — three Type-1 dimensions (`dim_sectors`, `dim_indices`,
    `dim_date`) and five fact tables (`fact_ohlcv`, `fact_restatement_history`,
    `fact_index_membership`, `fact_sector_daily`, `fact_valuation_daily`)
- `infra/` — Terraform: one service account (`psx-warehouse-runner`) with
  project-level BigQuery `dataEditor`/`jobUser` roles plus a resource-scoped
  `run.invoker` binding, a BigQuery `raw` dataset, a Cloud Run Job pulling
  the Docker Hub image published by `docker-publish.yml` (merges once PR #23
  lands), and a Cloud Scheduler job triggering it daily at 6 PM PKT
  (`Asia/Karachi`).

## CI/CD

- `ci.yml` — lint, test, and `dbt parse` validation on every push/PR to `main`.
- `docker-publish.yml` — builds and pushes `mtauha/psx-warehouse:latest` (and a
  short-sha tag) to Docker Hub on every push to `main`.
- `dbt-docs.yml` — publishes dbt docs to GitHub Pages on every `dbt/` change:
  https://mtauha.github.io/psx-warehouse/ (generated against the MotherDuck dev
  target until BigQuery/Terraform is live).

## Guides

- `DEPLOYMENT.md` — architecture, prerequisites, GCP bootstrap, deploying/
  verifying the infrastructure, and known limitations.
- `CONTRIBUTING.md` — adding a new raw-storage backend (with a working
  template at `extract/example_backend.py`).

<!-- CI verification: phase 1 scaffolding -->
