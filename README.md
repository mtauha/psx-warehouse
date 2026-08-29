# PSX Analytics Warehouse

dbt-core + BigQuery analytics layer on top of the [`psxdata`](https://github.com/mtauha/psxdata) SDK, turning raw PSX OHLCV data into tested, analysis-ready marts.

Serves two goals: a personal analytics warehouse on PSX/KSE-100 stocks, and a
data-engineering portfolio piece — pipelines, warehousing, orchestration,
testing, IaC, and CI/CD end to end.

**Status:** under construction. Repository scaffolding only — no extraction
code, dbt models, or infrastructure yet.

## Layout

- `extract/` — Python extraction from the `psxdata` SDK into BigQuery raw
- `dbt/` — dbt-core project (staging / intermediate / marts)
- `infra/` — Terraform
