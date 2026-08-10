"""Strict location / work-type filters (PR3)."""

from core.profile import validate_config, default_config
from core.scorer import fails_strict_filters, score_job
from core.collector import _score_and_store
from core.models import Job


def _profile(**loc_overrides):
    cfg = default_config()
    cfg["location"].update(loc_overrides)
    # Keep min store low so score doesn't mask strict filter tests
    cfg["scoring"]["min_score_to_store"] = 0
    cfg["search"]["title_keywords_positive"] = ["engineer"]
    cfg["search"]["relevant_skills"] = ["python"]
    return validate_config(cfg)


def test_defaults_strict_flags_off():
    cfg = default_config()
    assert cfg["location"]["strict_location_fit"] is False
    assert cfg["location"]["strict_work_type"] is False


def test_validate_coerces_strict_bools():
    cfg = validate_config({
        "location": {
            "strict_location_fit": "true",
            "strict_work_type": "yes",
        }
    })
    assert cfg["location"]["strict_location_fit"] is True
    assert cfg["location"]["strict_work_type"] is True

    cfg2 = validate_config({
        "location": {
            "strict_location_fit": "false",
            "strict_work_type": 0,
        }
    })
    assert cfg2["location"]["strict_location_fit"] is False
    assert cfg2["location"]["strict_work_type"] is False


def test_fails_strict_location_fit():
    profile = _profile(
        preferred_locations=["austin"],
        excluded_locations=["india only"],
        strict_location_fit=True,
    )
    # Excluded phrase → location_fit=no
    result = score_job(
        "Python Engineer",
        "Great role. India only.",
        "Remote",
        profile=profile,
    )
    assert result["location_fit"] == "no"
    assert fails_strict_filters(result, profile=profile) == "strict_location_fit"


def test_strict_location_off_does_not_fail():
    profile = _profile(
        preferred_locations=["austin"],
        excluded_locations=["india only"],
        strict_location_fit=False,
    )
    result = score_job(
        "Python Engineer",
        "Great role. India only.",
        "Remote",
        profile=profile,
    )
    assert result["location_fit"] == "no"
    assert fails_strict_filters(result, profile=profile) is None


def test_fails_strict_work_type_onsite_only_remote_job():
    profile = _profile(
        work_types=["onsite"],
        strict_work_type=True,
    )
    result = score_job(
        "Python Engineer",
        "Fully remote python engineer role.",
        "Remote",
        profile=profile,
    )
    assert result["work_type"] == "remote"
    assert fails_strict_filters(result, profile=profile) == "strict_work_type"


def test_strict_work_type_keeps_matching_and_unknown():
    profile = _profile(
        work_types=["onsite", "hybrid"],
        strict_work_type=True,
    )
    onsite = score_job(
        "Python Engineer",
        "Join us in the office.",
        "Austin, TX",
        profile=profile,
    )
    assert onsite["work_type"] == "onsite"
    assert fails_strict_filters(onsite, profile=profile) is None

    # Empty/unknown location with no remote/hybrid/onsite language
    unknown = score_job(
        "Python Engineer",
        "Build great software with Python.",
        "",
        profile=profile,
    )
    assert unknown["work_type"] == "unknown"
    assert fails_strict_filters(unknown, profile=profile) is None


def test_strict_work_type_noop_when_no_preferred():
    """Empty work_types = accept any; strict flag alone does not drop."""
    profile = _profile(work_types=[], strict_work_type=True)
    result = score_job(
        "Python Engineer",
        "Fully remote.",
        "Remote",
        profile=profile,
    )
    assert result["work_type"] == "remote"
    assert fails_strict_filters(result, profile=profile) is None


def test_score_and_store_drops_strict_location(monkeypatch):
    """Strict location + excluded job → not stored."""
    stored = []

    def fake_insert(job_dict):
        stored.append(job_dict)
        return "new"

    monkeypatch.setattr("core.collector.insert_job", fake_insert)

    profile = _profile(
        preferred_locations=["austin"],
        excluded_locations=["india only"],
        strict_location_fit=True,
    )
    jobs = [
        Job(
            title="Python Engineer",
            company="Acme",
            location="Remote",
            description="India only hiring. Python engineer.",
            url="https://example.com/1",
            source="test",
        )
    ]
    stats = {"new": 0, "updated": 0, "filtered_out": 0}
    _score_and_store(jobs, stats, profile=profile)
    assert stats["filtered_out"] == 1
    assert stats["new"] == 0
    assert stored == []


def test_score_and_store_drops_strict_work_type(monkeypatch):
    """Strict work_type + onsite-only + remote job → not stored."""
    stored = []

    def fake_insert(job_dict):
        stored.append(job_dict)
        return "new"

    monkeypatch.setattr("core.collector.insert_job", fake_insert)

    profile = _profile(work_types=["onsite"], strict_work_type=True)
    jobs = [
        Job(
            title="Python Engineer",
            company="Acme",
            location="Remote",
            description="Fully remote python engineer. Work from home.",
            url="https://example.com/2",
            source="test",
        )
    ]
    stats = {"new": 0, "updated": 0, "filtered_out": 0}
    _score_and_store(jobs, stats, profile=profile)
    assert stats["filtered_out"] == 1
    assert stored == []


def test_score_and_store_flags_off_identical(monkeypatch):
    """Flags off → job is stored (same path as today)."""
    stored = []

    def fake_insert(job_dict):
        stored.append(job_dict)
        return "new"

    monkeypatch.setattr("core.collector.insert_job", fake_insert)

    profile = _profile(
        preferred_locations=["austin"],
        excluded_locations=["india only"],
        work_types=["onsite"],
        strict_location_fit=False,
        strict_work_type=False,
    )
    jobs = [
        Job(
            title="Python Engineer",
            company="Acme",
            location="Remote",
            description="India only. Fully remote python engineer.",
            url="https://example.com/3",
            source="test",
        )
    ]
    stats = {"new": 0, "updated": 0, "filtered_out": 0}
    _score_and_store(jobs, stats, profile=profile)
    assert stats["filtered_out"] == 0
    assert stats["new"] == 1
    assert len(stored) == 1
    assert stored[0]["location_fit"] == "no"
    assert stored[0]["work_type"] == "remote"
