"""Unit tests for extract.config."""
from __future__ import annotations

import pytest

from extract.config import Config, ConfigError, load_config


def test_load_config_reads_required_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT", "psx-warehouse-prod")
    monkeypatch.setenv("BQ_DATASET", "raw")
    monkeypatch.delenv("INDEX_NAMES", raising=False)
    monkeypatch.delenv("BQ_LOCATION", raising=False)

    cfg = load_config()

    assert cfg == Config(
        gcp_project="psx-warehouse-prod",
        bq_dataset="raw",
        index_names=("KSE100",),
        bq_location="US",
    )


def test_load_config_parses_custom_index_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT", "p")
    monkeypatch.setenv("BQ_DATASET", "raw")
    monkeypatch.setenv("INDEX_NAMES", "KSE100, KSE30 ,ALLSHR")
    monkeypatch.delenv("BQ_LOCATION", raising=False)

    cfg = load_config()

    assert cfg.index_names == ("KSE100", "KSE30", "ALLSHR")


def test_load_config_reads_custom_location(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT", "p")
    monkeypatch.setenv("BQ_DATASET", "raw")
    monkeypatch.setenv("BQ_LOCATION", "asia-south1")

    cfg = load_config()

    assert cfg.bq_location == "asia-south1"


def test_load_config_raises_when_gcp_project_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.setenv("BQ_DATASET", "raw")

    with pytest.raises(ConfigError, match="GCP_PROJECT"):
        load_config()


def test_load_config_raises_when_bq_dataset_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT", "p")
    monkeypatch.delenv("BQ_DATASET", raising=False)

    with pytest.raises(ConfigError, match="BQ_DATASET"):
        load_config()


def test_load_config_raises_when_index_names_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT", "p")
    monkeypatch.setenv("BQ_DATASET", "raw")
    monkeypatch.setenv("INDEX_NAMES", "  , ,")

    with pytest.raises(ConfigError, match="INDEX_NAMES"):
        load_config()
