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
