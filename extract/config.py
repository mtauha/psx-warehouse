"""Environment-variable configuration for the extraction job."""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Resolved extraction job configuration."""

    gcp_project: str
    bq_dataset: str
    index_names: tuple[str, ...]
    bq_location: str


def load_config() -> Config:
    """Load configuration from environment variables.

    Required:
        GCP_PROJECT: GCP project ID.
        BQ_DATASET: BigQuery dataset name (e.g. "raw").

    Optional:
        INDEX_NAMES: Comma-separated PSX index names to snapshot each run.
            Defaults to "KSE100".
        BQ_LOCATION: BigQuery dataset location, used only if the dataset
            doesn't exist yet and needs to be created. Defaults to "US".

    Returns:
        A populated Config.

    Raises:
        ConfigError: If a required variable is missing, or INDEX_NAMES
            resolves to no names at all.
    """
    gcp_project = os.environ.get("GCP_PROJECT", "").strip()
    if not gcp_project:
        raise ConfigError("GCP_PROJECT environment variable is required")

    bq_dataset = os.environ.get("BQ_DATASET", "").strip()
    if not bq_dataset:
        raise ConfigError("BQ_DATASET environment variable is required")

    index_names_raw = os.environ.get("INDEX_NAMES", "KSE100")
    index_names = tuple(
        name.strip() for name in index_names_raw.split(",") if name.strip()
    )
    if not index_names:
        raise ConfigError("INDEX_NAMES must contain at least one index name")

    bq_location = os.environ.get("BQ_LOCATION", "US").strip() or "US"

    return Config(
        gcp_project=gcp_project,
        bq_dataset=bq_dataset,
        index_names=index_names,
        bq_location=bq_location,
    )
