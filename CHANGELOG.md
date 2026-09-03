# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Repository scaffolding: Python/dbt project structure, CI (lint + dbt
  parse), GitHub issue/PR templates, dependabot, branch protection on `main`.
- Raw-layer extraction for three new tables, on both BigQuery and
  MotherDuck backends: `raw.symbols` (ticker attributes, hash-diffed so
  unchanged rows aren't rewritten, with delisting detection when a
  symbol drops out of a fresh fetch), `raw.sectors` (daily sector
  summary), and `raw.screener` (daily valuation/fundamentals snapshot).
- dbt marts layer: staging models for all five raw sources
  (`stg_stock_history`, `stg_symbols`, `stg_sectors`, `stg_index_constituents`,
  `stg_screener`); a Type-2 `dim_tickers` snapshot over `stg_symbols`
  tracking ticker-attribute history with delisting handling; three
  Type-1 dimensions (`dim_sectors`, `dim_indices`, `dim_date`); five
  fact tables (`fact_ohlcv`, `fact_restatement_history`,
  `fact_index_membership`, `fact_sector_daily`, `fact_valuation_daily`)
  joined as-of to `dim_tickers` via a shared `as_of_ticker_join` macro;
  and full test coverage (not-null, uniqueness, referential-integrity,
  and accepted-range tests) across staging, the snapshot, and all marts.
