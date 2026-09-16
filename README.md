# PSX Analytics Warehouse

dbt-core + BigQuery analytics layer on top of the [`psxdata`](https://github.com/mtauha/psxdata) SDK, turning raw PSX OHLCV data into tested, analysis-ready marts.

A personal analytics warehouse on PSX/KSE-100 stocks.

**Status:** under construction. Raw-layer extraction and the dbt marts layer
are built and tested against MotherDuck; Terraform-managed GCP infrastructure
(BigQuery raw dataset, Cloud Run Job, Cloud Scheduler) is written and
`terraform validate`-clean, pending the GCP billing account before `apply`.

## Layout

- `extract/` — Python extraction from the `psxdata` SDK into raw tables
  (BigQuery and MotherDuck)
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

<!-- CI verification: phase 1 scaffolding -->
