# PSX Analytics Warehouse — Design

**Status**: Approved for implementation planning
**Date**: 2026-08-29

## Purpose

A dbt-core + BigQuery analytics layer on top of the `psxdata` SDK, turning raw PSX
OHLCV data into tested, analysis-ready marts. Serves two goals equally: a genuinely
useful personal analytics warehouse on PSX/KSE-100 stocks, and a portfolio-grade
demonstration of data engineering practice (pipelines, warehousing, orchestration,
testing, IaC, CI/CD).

Out of scope for this spec (deliberately deferred to their own future
brainstorm/spec cycles): a FastAPI serving layer over the marts, a dashboard, and
an SCD Type 2 fundamentals (EPS/market cap) snapshot. Marts are designed so the
FastAPI layer is easy to bolt on later (see "Marts" below), but it is not built now.

## Repo layout

New repo at `D:\Projects\psxdata\warehouse`, sibling to the existing `sdk`, `api`,
and `psxdata-docs` repos.

```
warehouse/
├── extract/               Python extraction script(s)
├── dbt/                   dbt-core project (staging / intermediate / marts)
├── infra/                 Terraform
├── Dockerfile              one image: extract + dbt project
├── .github/workflows/      CI: build+push image, dbt docs publish
└── README.md               pipeline explanation, DAG screenshot/link
```

## Architecture & data flow

```
Cloud Scheduler (daily, after PSX close)
        │ triggers
        ▼
Cloud Run Job (pulls public image from Docker Hub, e.g. mtauha/psx-warehouse:latest)
  1. extract/main.py
       for each current KSE100 constituent:
           psxdata.stocks(symbol, cache=False)        → full OHLCV history
       psxdata.indices("KSE100", cache=False)          → today's constituent snapshot
       → load into BigQuery raw dataset via MERGE, keyed on (symbol, date)
         and (symbol, snapshot_date) respectively
  2. dbt run  --target prod
  3. dbt test --target prod
        │
        ▼
BigQuery:  raw → staging → intermediate → marts
```

### Why SDK-direct, not the hosted psxdata-api

Calling the hosted API (`psxdata-api.fastapicloud.dev`) instead of the SDK would
reintroduce the exact problem this project avoids: it's a shared public service
rate-limited to 60 req/min/IP, and a ~100-ticker daily pull would consume most of
that shared budget. It also adds a network hop and an external-uptime dependency
with no cache-bypass control today. The SDK-direct path has one hop (Cloud Run →
PSX) and no shared-resource contention.

### Why extraction always re-fetches full history

`HistoricalScraper.fetch()` (in the `psxdata` SDK) always issues a single `POST
historical` request that returns **all** available history for a symbol — PSX has
no server-side date filtering. The SDK's `start`/`end` parameters only filter the
already-downloaded response in memory. Combined with the explicit requirement to
always call the SDK with `cache=False` (no reliance on the on-disk cache, which
wouldn't persist across ephemeral Cloud Run executions anyway), this means every
run refetches full history per ticker from PSX regardless of what's already loaded.

Incrementality therefore lives entirely on the **write** side and downstream:
- The raw-layer load is a `MERGE` keyed on `(symbol, date)`, so re-fetching full
  history is idempotent and cheap to load — no duplicate rows regardless of how
  many times a given trading day has already been seen.
- dbt's incremental model (see below) is what actually skips reprocessing old
  trading days in the transform layer.

### Constituent (SCD-style) tracking

KSE-100 membership changes over time. Rather than fixing the ticker universe once,
`psxdata.indices("KSE100", cache=False)` is called every run and the result is
appended as a dated snapshot into the raw layer (`(symbol, snapshot_date)` as the
merge key), so membership additions/removals over time are queryable directly from
raw data — no dbt snapshot mechanism needed for this one, since the source already
naturally provides point-in-time snapshots on every call.

## Layers

- **raw**: append-only via MERGE. One row per `(symbol, date)` for OHLCV history as
  returned by the SDK, and one row per `(symbol, snapshot_date)` for KSE-100
  constituent snapshots. Column/table naming and typing at this layer are minimal —
  detailed schema design is the user's own to finalize.
- **staging** (dbt): type casting, column renaming/standardization, null handling.
  One staging model per raw source.
- **intermediate** (dbt): daily returns, rolling moving averages (20/50/200-day),
  volatility. This is where the required incremental model lives.
- **marts** (dbt): `mart_stock_performance`, `mart_sector_rollups`,
  `mart_kse100_index_tracking`. Final, stable, flat-column tables — no nested
  structs, clear grain per table — so that a future FastAPI layer can query them
  directly with no further transformation.

## dbt tests

- `not_null` on key columns (symbol, date, close) in staging models.
- Custom test: no negative prices (open/high/low/close >= 0).
- Custom test: no future dates (date <= current_date()).
- `dbt_utils.unique_combination_of_columns` on `(symbol, date)` in staging and in
  the price-based marts.

## Incremental model

The intermediate daily-returns/rolling-MA/volatility model uses
`is_incremental()` to filter to trading dates newer than what's already
materialized, `unique_key=['symbol', 'date']`, and `incremental_strategy='merge'`
(natively supported by `dbt-bigquery`).

## Error handling

- Per-ticker fetch failures during extraction are logged and that ticker is
  skipped for the run — self-healing, since the next day's full-history refetch
  picks up any gap automatically.
- The Cloud Run Job only fails loudly (non-zero exit) if extraction yields zero
  rows across all tickers for the run, or if `dbt test` reports failures. Job
  failures are visible via Cloud Run's own execution history/logs in the GCP
  console; no separate alerting system is built for this spec.

## Deployment & infrastructure

- **Image**: one Docker image containing both the `extract/` script and the
  `dbt/` project. Built and pushed to a **public Docker Hub repo** (matching the
  existing `mtauha/psxdata-api` convention) by a GitHub Actions workflow on push
  to `main`. No Artifact Registry involved — Cloud Run Jobs can pull public images
  directly from Docker Hub, and Docker Hub doesn't charge for public repo storage.
  Because the image is public, no secrets are ever baked into it.
- **Secrets**: the BigQuery service account key lives in Secret Manager and is
  injected into the Cloud Run Job at runtime — never copied into the image.
- **Terraform** (`infra/`) manages: the BigQuery `raw` dataset, a service account
  with the minimum roles needed to write to BigQuery raw and run dbt against
  staging/intermediate/marts, the corresponding IAM bindings, the Secret Manager
  secret resource (value populated out-of-band, not stored in state), the Cloud
  Run Job definition, and the Cloud Scheduler job that triggers it daily. dbt
  itself auto-creates the staging/intermediate/marts datasets on first `dbt run`,
  so Terraform does not manage those.
- Chosen over plain `gcloud` scripts because the user wants Terraform experience
  they can point to, and the footprint (five resources) is small enough to stay
  readable end-to-end.

## Docs & lineage artifact

`dbt docs generate` runs in CI on push to `main`. The generated static site is
published (e.g. GitHub Pages) so the README can link to a live, browsable lineage
graph, plus a static screenshot embedded directly in the README for anyone who
doesn't click through.

## Explicitly out of scope (future sub-projects)

- FastAPI endpoint(s) over the marts (e.g. `/stocks/{ticker}/performance`).
- Dashboard.
- SCD Type 2 snapshot for fundamentals (EPS, market cap).

These were listed as stretch goals in the original project idea and are left for
their own brainstorm/spec cycles once the pipeline and warehouse are solid. The
marts layer is designed (flat columns, stable naming, clear grain) specifically so
plugging in a FastAPI layer later is straightforward.
