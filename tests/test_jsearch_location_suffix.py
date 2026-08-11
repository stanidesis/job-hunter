"""JSearch location suffix + country helpers (PR5 / job-hunter-uo5)."""

from unittest.mock import patch

from core.profile import validate_config, default_config, JSEARCH_COUNTRY_CODES
from core.collector import (
    apply_jsearch_location_suffix,
    _build_job_board_sources,
)


def test_default_suffix_empty():
    cfg = default_config()
    assert cfg["search"]["jsearch_location_suffix"] == ""


def test_validate_strips_suffix():
    cfg = validate_config({"search": {"jsearch_location_suffix": "  Austin, TX  "}})
    assert cfg["search"]["jsearch_location_suffix"] == "Austin, TX"


def test_validate_non_string_suffix_coerced():
    cfg = validate_config({"search": {"jsearch_location_suffix": 123}})
    assert cfg["search"]["jsearch_location_suffix"] == "123"


def test_apply_suffix_appends():
    assert apply_jsearch_location_suffix("python engineer", "San Francisco") == (
        "python engineer San Francisco"
    )


def test_apply_suffix_empty_noop():
    assert apply_jsearch_location_suffix("python engineer", "") == "python engineer"
    assert apply_jsearch_location_suffix("python engineer", "   ") == "python engineer"


def test_apply_suffix_skips_when_already_present():
    assert apply_jsearch_location_suffix(
        "python engineer San Francisco", "San Francisco"
    ) == "python engineer San Francisco"
    assert apply_jsearch_location_suffix(
        "python engineer san francisco bay", "San Francisco"
    ) == "python engineer san francisco bay"


def test_apply_suffix_only():
    assert apply_jsearch_location_suffix("", "Berlin") == "Berlin"


def test_build_appends_suffix_at_collect():
    profile = {
        "search": {
            "job_board_sources": ["jsearch"],
            "jsearch_location_suffix": "Austin, TX",
            "jsearch_default_queries": [
                {"query": "python engineer", "country": "US", "date_posted": "week"},
                {
                    "query": "backend engineer Austin, TX",
                    "country": "us",
                    "date_posted": "week",
                },
            ],
        }
    }
    with patch("core.collector.RAPIDAPI_KEY", "test-key"):
        sources = _build_job_board_sources(profile)
    assert len(sources) == 1
    qs = sources[0].queries
    assert qs[0]["query"] == "python engineer Austin, TX"
    assert qs[0]["country"] == "us"  # normalized lower
    # Already contains city → not doubled
    assert qs[1]["query"] == "backend engineer Austin, TX"


def test_build_no_suffix_unchanged():
    profile = {
        "search": {
            "job_board_sources": ["jsearch"],
            "jsearch_location_suffix": "",
            "jsearch_default_queries": [
                {"query": "python engineer remote", "country": "gb", "date_posted": "week"},
            ],
        }
    }
    with patch("core.collector.RAPIDAPI_KEY", "test-key"):
        sources = _build_job_board_sources(profile)
    assert sources[0].queries[0]["query"] == "python engineer remote"
    assert sources[0].queries[0]["country"] == "gb"


def test_jsearch_country_codes_expanded():
    """Dropdown list covers common markets beyond the original 6–8 codes."""
    assert "us" in JSEARCH_COUNTRY_CODES
    assert "in" in JSEARCH_COUNTRY_CODES
    assert "de" in JSEARCH_COUNTRY_CODES
    assert "jp" in JSEARCH_COUNTRY_CODES
    assert "br" in JSEARCH_COUNTRY_CODES
    assert "ae" in JSEARCH_COUNTRY_CODES
    assert len(JSEARCH_COUNTRY_CODES) >= 40
    # all lowercase ISO-style 2-letter
    assert all(len(c) == 2 and c == c.lower() for c in JSEARCH_COUNTRY_CODES)
