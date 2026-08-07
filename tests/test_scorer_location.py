"""Location honesty + work-type detection (PR1)."""

from core.models import Job
from core.scorer import detect_work_type
from sources.jsearch import JSearchSource


def test_job_default_location_is_unknown():
    job = Job(title="Engineer", company="Acme")
    assert job.location == "Unknown"


def test_bare_city_is_onsite():
    assert detect_work_type(location="Austin, TX") == "onsite"
    assert detect_work_type(location="San Francisco, CA") == "onsite"
    assert detect_work_type(location="London, UK") == "onsite"


def test_remote_location_is_remote():
    assert detect_work_type(location="Remote") == "remote"
    assert detect_work_type(location="Remote · US") == "remote"
    assert detect_work_type(location="Anywhere") == "remote"
    assert detect_work_type(location="worldwide") == "remote"


def test_hybrid_beats_remote_and_city():
    assert detect_work_type(
        location="New York, NY",
        description="Hybrid - 3 days in office",
    ) == "hybrid"
    assert detect_work_type(
        title="Engineer",
        location="NYC",
        description="partially remote, 2-3 days office",
    ) == "hybrid"


def test_unknown_when_empty_or_placeholder():
    assert detect_work_type(location="") == "unknown"
    assert detect_work_type(location="Unknown") == "unknown"
    assert detect_work_type(location="n/a") == "unknown"
    assert detect_work_type() == "unknown"


def test_explicit_onsite_keywords():
    assert detect_work_type(
        location="Berlin",
        description="This is an on-site role; come into the office",
    ) == "onsite"


def test_description_remote_overrides_city():
    assert detect_work_type(
        location="Seattle, WA",
        description="Fully remote, work from home",
    ) == "remote"


def test_jsearch_empty_location_unknown_not_remote():
    src = JSearchSource(queries=[])
    job = src._map_job({
        "job_title": "Backend Engineer",
        "employer_name": "Acme",
        "job_city": "",
        "job_state": "",
        "job_country": "",
        "job_is_remote": False,
        "job_description": "Build APIs",
        "job_apply_link": "https://example.com/job",
        "job_employment_type": "FULLTIME",
    })
    assert job.location == "Unknown"


def test_jsearch_remote_flag():
    src = JSearchSource(queries=[])
    job = src._map_job({
        "job_title": "Backend Engineer",
        "employer_name": "Acme",
        "job_city": "",
        "job_state": "",
        "job_country": "US",
        "job_is_remote": True,
        "job_description": "Build APIs",
        "job_apply_link": "https://example.com/job",
        "job_employment_type": "FULLTIME",
    })
    assert job.location.startswith("Remote")
