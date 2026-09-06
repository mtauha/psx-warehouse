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
- Technical/analytical indicators layer: `int_technical_indicators` (moving averages, RSI-14, MACD,
  Bollinger Bands, rolling volatility, trailing returns), `int_drawdown` (all-time-to-date max drawdown),
  and `fact_technical_indicators` (marts fact table with MA-crossover event detection).
- Cross-sectional/multi-comparison analytics layer: a point-in-time (`_pit`)
  foundation (`int_ohlcv_pit`, `int_index_constituents_pit`, `int_screener_pit`)
  fixing look-ahead bias from restated historical data; market and cap-weighted
  sector return series (`int_market_returns`, `int_sector_returns`); rolling
  252-trading-day beta (full/upside/downside) and correlation vs. index/sector
  (`int_ticker_relationships`, `fact_ticker_relationships`); sector-to-sector
  correlation (`int_sector_correlation`, `fact_sector_correlation`);
  sector-rotation scoring (`fact_sector_rotation`); and daily cross-sectional
  rankings for momentum, relative strength, value (P/E), and low-volatility,
  ranked over the point-in-time KSE-100 universe
  (`fact_cross_sectional_rankings`).
