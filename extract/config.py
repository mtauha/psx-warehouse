"""Environment-variable configuration for the extraction job.

Holds only backend-agnostic settings. Each storage backend module
(bigquery_io, motherduck_io, ...) owns its own config type and env-var
resolution — see extract/storage.py for why: this keeps adding a new
backend from ever requiring an edit here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Resolved, backend-agnostic extraction job configuration."""

    backend: str
    index_names: tuple[str, ...]


def load_config() -> Config:
    """Load backend-agnostic configuration from environment variables.

    Optional:
        BACKEND: which storage backend to use ("bigquery" or "motherduck").
            Defaults to "bigquery". Not validated against a known-backend
            list here — extract.main's backend registry is the single place
            that knows which backend names actually exist.
        INDEX_NAMES: Comma-separated PSX index names to snapshot each run.
            Defaults to "KSE100".

    Returns:
        A populated Config.

    Raises:
        ConfigError: If INDEX_NAMES resolves to no names at all.
    """
    backend = os.environ.get("BACKEND", "bigquery").strip() or "bigquery"

    index_names_raw = os.environ.get("INDEX_NAMES", "KSE100")
    index_names = tuple(
        name.strip() for name in index_names_raw.split(",") if name.strip()
    )
    if not index_names:
        raise ConfigError("INDEX_NAMES must contain at least one index name")

    return Config(backend=backend, index_names=index_names)
