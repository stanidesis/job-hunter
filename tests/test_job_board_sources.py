"""Profile-selectable job boards (PR2)."""

from unittest.mock import patch

from core.profile import validate_config, default_config, KNOWN_JOB_BOARD_SOURCES
from core.collector import _build_job_board_sources, _enabled_job_board_names


def test_default_job_board_sources_empty():
    cfg = default_config()
    assert cfg["search"]["job_board_sources"] == []


def test_validate_normalizes_and_dedupes_boards():
    cfg = validate_config({
        "search": {
            "job_board_sources": ["JSearch", "remotive", "remotive", "linkedin", "  ", "arbeitnow"],
        }
    })
    assert cfg["search"]["job_board_sources"] == ["jsearch", "remotive", "arbeitnow"]


def test_validate_rejects_non_list_boards():
    cfg = validate_config({"search": {"job_board_sources": "jsearch"}})
    assert cfg["search"]["job_board_sources"] == []


def test_enabled_empty_means_all():
    assert _enabled_job_board_names({"search": {}}) == set(KNOWN_JOB_BOARD_SOURCES)
    assert _enabled_job_board_names({"search": {"job_board_sources": []}}) == set(KNOWN_JOB_BOARD_SOURCES)


def test_enabled_filters_to_selection():
    names = _enabled_job_board_names({"search": {"job_board_sources": ["jsearch"]}})
    assert names == {"jsearch"}


def test_build_only_jsearch():
    """Profile with only jsearch → only jsearch in collect (when key + queries present)."""
    profile = {
        "search": {
            "job_board_sources": ["jsearch"],
            "jsearch_default_queries": [
                {"query": "python engineer", "country": "us", "date_posted": "week"},
            ],
        }
    }
    with patch("core.collector.RAPIDAPI_KEY", "test-key"):
        sources = _build_job_board_sources(profile)
    assert [s.name for s in sources] == ["jsearch"]


def test_build_empty_sources_all_four_when_jsearch_ready():
    """Empty sources → all four (today behavior), when JSearch is configured."""
    profile = {
        "search": {
            "job_board_sources": [],
            "jsearch_default_queries": [
                {"query": "python engineer", "country": "us", "date_posted": "week"},
            ],
        }
    }
    with patch("core.collector.RAPIDAPI_KEY", "test-key"):
        names = [s.name for s in _build_job_board_sources(profile)]
    assert names == ["remotive", "remoteok", "arbeitnow", "jsearch"]


def test_build_empty_sources_without_jsearch_key():
    """Without RAPIDAPI_KEY, free boards still all run when selection is empty."""
    profile = {"search": {"job_board_sources": [], "jsearch_default_queries": []}}
    with patch("core.collector.RAPIDAPI_KEY", ""):
        names = [s.name for s in _build_job_board_sources(profile)]
    assert names == ["remotive", "remoteok", "arbeitnow"]


def test_build_excludes_remote_boards():
    """Onsite-style profile: only jsearch (no remotive/remoteok/arbeitnow)."""
    profile = {
        "search": {
            "job_board_sources": ["jsearch"],
            "jsearch_default_queries": [
                {"query": "software engineer San Francisco", "country": "us"},
            ],
        }
    }
    with patch("core.collector.RAPIDAPI_KEY", "test-key"):
        names = [s.name for s in _build_job_board_sources(profile)]
    assert "remotive" not in names
    assert "remoteok" not in names
    assert "arbeitnow" not in names
    assert names == ["jsearch"]


def test_build_jsearch_selected_but_no_queries():
    """jsearch selected without queries → no jsearch source (same as before)."""
    profile = {
        "search": {
            "job_board_sources": ["jsearch"],
            "jsearch_default_queries": [],
        }
    }
    with patch("core.collector.RAPIDAPI_KEY", "test-key"):
        assert _build_job_board_sources(profile) == []
