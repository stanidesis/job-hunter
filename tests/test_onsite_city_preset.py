"""Tests for the onsite/city example profile preset."""

from pathlib import Path

import yaml

from core.profile import (
    KNOWN_JOB_BOARD_SOURCES,
    PROFILES_DIR,
    list_presets,
    validate_config,
)


PRESET_SLUG = "onsite_city_example"
PRESET_PATH = PROFILES_DIR / f"{PRESET_SLUG}.yaml"


def _load_preset_raw() -> dict:
    assert PRESET_PATH.exists(), f"missing preset: {PRESET_PATH}"
    with open(PRESET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def test_onsite_city_preset_listed():
    slugs = {p["slug"] for p in list_presets()}
    assert PRESET_SLUG in slugs


def test_onsite_city_preset_boards_exclude_remote_only():
    data = _load_preset_raw()
    config = {k: v for k, v in data.items() if k not in ("name", "description")}
    cfg = validate_config(config)

    boards = cfg["search"]["job_board_sources"]
    assert boards, "onsite preset should pin explicit boards (not empty=all)"
    assert "remotive" not in boards
    assert "remoteok" not in boards
    for b in boards:
        assert b in KNOWN_JOB_BOARD_SOURCES


def test_onsite_city_preset_location_and_work_types():
    data = _load_preset_raw()
    config = {k: v for k, v in data.items() if k not in ("name", "description")}
    cfg = validate_config(config)

    loc = cfg["location"]
    preferred = [p.lower() for p in loc["preferred_locations"]]
    assert any("san francisco" in p or "bay area" in p for p in preferred)

    work_types = set(loc["work_types"])
    assert work_types == {"onsite", "hybrid"}
    assert "remote" not in work_types

    # Strict flags live on the YAML; deep-merge keeps them even before PR3
    # normalizes defaults on every code path.
    assert loc.get("strict_location_fit") is True
    assert loc.get("strict_work_type") is True


def test_onsite_city_preset_jsearch_not_remote_only():
    data = _load_preset_raw()
    queries = (data.get("search") or {}).get("jsearch_default_queries") or []
    assert queries
    for q in queries:
        assert q.get("remote_jobs_only") is False
        text = str(q.get("query", "")).lower()
        assert any(
            token in text
            for token in ("san francisco", "bay area", "sf ", " sf")
        ), f"query should mention SF metro: {q.get('query')}"
