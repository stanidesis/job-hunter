# Customization Guide

How to adapt the system for different candidates, roles, or markets.

---

## Change the Candidate Profile

The DM templates currently reference Parmanand's specific experience. To customize:

### Edit `core/hunter.py` → `generate_dm_template()`

Replace these hardcoded details:
- **"healthcare SaaS serving 5,000+ users with sub-200ms APIs"**
- **"DoctusTech"**
- **"multitenant SaaS + Stripe integrations"**

Example for a different candidate (say, an ML engineer):
```python
long = (
    f"{greeting},\n\n"
    f"Noticed {company} is hiring for {title}. The stack caught my eye — "
    f"I've been shipping {stack_phrase} ML pipelines for 3+ years.\n\n"
    f"Current role: Senior ML Engineer at CompanyX. I built a recommendation "
    f"system serving 100M+ daily users, achieving 15% CTR uplift.\n\n"
    # ... rest of template
)
```

### Update the candidate name
In `core/hunter.py`:
```python
def generate_dm_template(job: dict, contact: dict = None, candidate_name: str = "Parmanand") -> dict:
```

Change `"Parmanand"` to the actual first name. It's passed to the long DM's signature.

### Update the email greeting
In `core/emailer.py` → `build_email_html()`:
```python
def build_email_html(items: list[dict], candidate_name: str = "Parmanand") -> str:
```

---

## Change Target Role / Stack

The system is currently tuned for **Python/Django backend**. To target other roles, edit `config/settings.py`.

### For frontend developers:
```python
title_keywords_positive (profile) = [
    "frontend", "front-end", "react", "vue", "angular",
    "software engineer", "ui engineer", "full stack",
]

TITLE_KEYWORDS_NEGATIVE = [
    "backend", "devops", "data", "ml engineer", "mobile",
    "qa", "intern", "trainee", "junior",
]

relevant_skills (profile) = [
    "react", "vue", "angular", "typescript", "javascript",
    "nextjs", "redux", "tailwind", "css", "html",
    "graphql", "webpack", "vite", "jest",
]
```

### For data engineers:
```python
title_keywords_positive (profile) = [
    "data engineer", "data", "etl", "analytics engineer",
    "pipeline", "warehouse",
]

relevant_skills (profile) = [
    "python", "sql", "dbt", "airflow", "spark",
    "kafka", "snowflake", "bigquery", "redshift",
    "pandas", "databricks", "aws", "gcp",
]
```

### For ML engineers:
```python
title_keywords_positive (profile) = [
    "machine learning", "ml engineer", "ai engineer",
    "mlops", "data scientist",
]

relevant_skills (profile) = [
    "pytorch", "tensorflow", "transformers", "langchain",
    "huggingface", "numpy", "pandas", "sklearn",
    "mlflow", "kubeflow", "sagemaker",
]
```

---

## Change JSearch Queries

Use the **Profile → Search** tab (or the dashboard **Search Queries** modal) — no code changes needed.

Queries live on the active profile under `search.jsearch_default_queries`. Each row has:

| Field | Purpose |
|---|---|
| `query` | Free-text search terms |
| `country` | ISO 3166-1 alpha-2 market (see table below) |
| `date_posted` | `today` / `3days` / `week` / `month` / `all` |
| `remote_jobs_only` | Restrict JSearch to remote listings |

Optional **`search.jsearch_location_suffix`** (Profile → Search) is appended to every query string **at collect time**. Example: suffix `San Francisco` turns `python engineer` into `python engineer San Francisco`. If the query already contains the phrase, it is not doubled.

---

## Change Geography

### Location & work type (preferred path)

Edit the profile **Location** tab:

- **Preferred locations** — cities, regions, countries, or phrases like `worldwide` / `remote`
- **Excluded locations** — places you will not take
- **Work types** — Remote / Hybrid / On-site (empty = any)

Location fit is computed by `check_location_fit()`; work type by `detect_work_type()`. Both soft-score by default (nudge relevance / red flags).

### Target a different country (JSearch)

1. Set each JSearch query’s **country** to the 2-letter code for your market (UI dropdowns on Profile and Search Queries modal).
2. Optionally set **`jsearch_location_suffix`** to a city/region so every query is geo-qualified without editing each string.
3. Set preferred/excluded location phrases on the Location tab to match.

### Country codes (JSearch)

Codes are ISO 3166-1 alpha-2 (lowercase in config; uppercase in the UI). Full list in `core.profile.JSEARCH_COUNTRY_CODES`:

| Region | Codes |
|---|---|
| North America | `us`, `ca`, `mx` |
| UK & Ireland | `gb`, `ie` |
| Western Europe | `de`, `fr`, `nl`, `be`, `ch`, `at`, `es`, `it`, `pt` |
| Nordics | `se`, `no`, `dk`, `fi` |
| Central / Eastern Europe | `pl`, `cz`, `ro`, `hu`, `ua` |
| South Asia | `in`, `pk`, `bd` |
| APAC | `sg`, `au`, `nz`, `jp`, `kr`, `cn`, `hk`, `tw`, `my`, `id`, `th`, `ph`, `vn` |
| Middle East & Africa | `ae`, `sa`, `il`, `tr`, `eg`, `za`, `ng`, `ke` |
| Latin America | `br`, `ar`, `cl`, `co` |

### Recipe: onsite / fixed-city search (end-to-end)

Use this path when you want roles in a specific city (not remote-first):

1. **Job boards** — Profile → Search → Job Board Sources: enable **JSearch** (and optionally Arbeitnow). Leave **Remotive** / **RemoteOK** unchecked so remote-only boards do not dominate. Empty selection = all boards (remote-heavy).
2. **JSearch location suffix** — set to your city/region, e.g. `Austin, TX` or `Berlin`.
3. **JSearch queries** — role/stack terms without baking the city into every string (the suffix is applied at collect). Set `country` to the market (`us`, `de`, …). Leave **Remote** unchecked on queries (`remote_jobs_only: false`).
4. **Location tab** — preferred phrases for your metro; exclude regions you skip; set work types to **On-site** and/or **Hybrid**.
5. **Collect Jobs** — collector builds `query + " " + suffix` for each enabled JSearch row, then scores with location fit / work type.
6. **Company ATS** — still runs for active companies regardless of board selection; use Discover / seed tools for employers in your market (see PR6 for non-remote discovery paths).

YAML sketch:

```yaml
search:
  job_board_sources: [jsearch]
  jsearch_location_suffix: "Austin, TX"
  jsearch_default_queries:
    - { query: "software engineer", country: "us", date_posted: "week", remote_jobs_only: false }
    - { query: "backend engineer python", country: "us", date_posted: "3days", remote_jobs_only: false }
location:
  preferred_locations: ["austin", "texas", "tx", "remote us"]
  excluded_locations: ["europe only", "emea only"]
  work_types: [onsite, hybrid]
```

### Recipe: remote-first (default style)

- Leave `jsearch_location_suffix` empty.
- Enable all boards or include Remotive / RemoteOK.
- Mark some JSearch queries with **Remote** checked.
- Preferred locations can include `remote`, `worldwide`, `global`.

By default both only soft-score (nudge relevance / red flags). For hard filters, enable on the profile (or import the onsite city preset):

- **`location.strict_location_fit`** — drop jobs with `location_fit=no` at collect (and skip them for outreach). Use with preferred/excluded location phrases.
- **`location.strict_work_type`** — drop jobs whose known work type is not in `work_types` (unknown work type is still kept). Requires at least one work type selected.

Both default to `false` so existing profiles behave as before.

### Onsite / fixed-city search (example preset)

Import **`profiles/onsite_city_example.yaml`** (slug: `onsite_city_example`) from the Profile page. It models a San Francisco Bay Area onsite/hybrid searcher:

| Setting | Example value |
|---|---|
| `search.job_board_sources` | `arbeitnow`, `jsearch` only (no Remotive / RemoteOK) |
| `location.work_types` | `onsite`, `hybrid` |
| `location.strict_location_fit` / `strict_work_type` | `true` |
| Preferred phrases | SF / Bay Area city names |
| JSearch queries | City-qualified, `remote_jobs_only: false` |

**Retarget another city** (edit the imported profile or the YAML, then re-import with overwrite):

1. Replace `location.preferred_locations` with your metro phrases (e.g. `"austin"`, `"seattle"`, `"berlin"`).
2. Update `location.excluded_locations` for places you will not take.
3. Rewrite `search.default_terms` and `search.jsearch_default_queries` so every query includes the city/region.
4. Keep `work_types: [onsite, hybrid]` and the strict flags if you want hard drops for remote-only or wrong-city jobs.
5. Adjust `outreach.email_timezone` / digest copy if the metro’s timezone differs.

Company ATS collection still runs for all profiles; board selection only affects free/paid job boards.

---

## Change Score Threshold

### Store more jobs (lower bar)
`core/collector.py`:
```python
MIN_SCORE_TO_STORE = 15  # default: 25
```

### Show only top-quality jobs in email
`core/emailer.py` → `run_daily_pipeline()`:
```python
top_jobs = get_jobs(min_score=60, ...)  # default: 40
```

---

## Change Email Schedule

### Different time of day
Edit `.env`:
```
DAILY_EMAIL_HOUR=7   # env fallback; prefer Profile → Outreach → Daily Digest Schedule
```

### Different timezone
Edit `config/settings.py`:
```python
DAILY_EMAIL_TIMEZONE = "America/New_York"  # or any valid TZ
```

### Multiple emails per day
Edit `main.py` startup — add more scheduler jobs:
```python
scheduler.add_job(run_daily_pipeline, CronTrigger(hour=9), id="morning_digest")
scheduler.add_job(run_daily_pipeline, CronTrigger(hour=17), id="evening_digest")
```

### Change number of jobs in email
Edit `.env`:
```
DAILY_JOBS_COUNT=20   # default: 15
```

---

## Add a New Job Source

### Example: Add LinkedIn Jobs via their RSS feed

Create `sources/linkedin_rss.py`:

```python
import httpx
from sources.base import BaseSource
from core.models import Job
from xml.etree import ElementTree as ET

class LinkedInRSSSource(BaseSource):
    name = "linkedin"
    
    async def fetch(self) -> list[Job]:
        # LinkedIn's public RSS URL per saved search
        url = "https://www.linkedin.com/jobs/python-developer-jobs-india/rss"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        
        root = ET.fromstring(resp.text)
        jobs = []
        for item in root.findall(".//item"):
            job = Job(
                title=item.findtext("title", ""),
                company="LinkedIn Listing",  # parse from description
                location="",
                description=item.findtext("description", ""),
                url=item.findtext("link", ""),
                source=self.name,
                posted_date=item.findtext("pubDate", ""),
            )
            jobs.append(job)
        return jobs
```

Register in `core/collector.py` (and add the source id to
`KNOWN_JOB_BOARD_SOURCES` in `core/profile.py` so profiles can enable it via
`search.job_board_sources`):

```python
from sources.linkedin_rss import LinkedInRSSSource

def _build_job_board_sources(profile=None):
    sources = [
        RemotiveSource(),
        RemoteOKSource(),
        ArbeitnowSource(),
        LinkedInRSSSource(),   # ADD HERE
    ]
    ...
```

That's it. All scoring, dedup, filtering still applies.

---

## Multi-Candidate Support

To run for multiple candidates, easiest approach is **separate instances**:

### Option A: Multiple databases

```bash
# Candidate 1
DB_PATH=candidate1.db python -m uvicorn main:app --port 8000

# Candidate 2
DB_PATH=candidate2.db python -m uvicorn main:app --port 8001
```

But `DB_PATH` is currently hardcoded in `config/settings.py`. Make it env-driven:

```python
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "jobs.db"))
```

Then run multiple with different ports + DBs.

### Option B: Multi-tenant (bigger rewrite)

Add `candidate_id` to all tables. Switch context via URL or login. Not currently built.

---

## Disable Features

### Disable daily email
Leave `RESEND_API_KEY=` or `RESEND_FROM=` empty in `.env`. Scheduler skips.

### Disable company crawling
Comment out in `core/collector.py`:
```python
# if include_companies:
#     log("\n--- Company Crawl ---")
#     company_stats = await run_company_crawl()
```

### Disable JSearch
Remove `RAPIDAPI_KEY` from `.env`. Only free sources run.

---

## Change DM Tone

Current templates are professional but casual. For different tones, edit `core/hunter.py` → `generate_dm_template()`.

### Formal:
```python
short = (
    f"Dear {first_name if first_name else 'Sir/Madam'},\n"
    f"I am writing regarding the {title} role at {company}. "
    f"With 3+ years of experience in {stack_phrase}, I would like to..."
)
```

### Bold / Confident:
```python
short = (
    f"{greeting} — {title} at {company} looks like a perfect fit. "
    f"I've shipped {stack_phrase} systems at scale. "
    f"Can we talk?"
)
```

---

## Integrate with n8n / Zapier

Use the Google Sheets export endpoint:
```
POST /api/export/sheets?min_score=50&location_fit=yes&work_type=remote
```

Then in n8n:
1. Google Sheets trigger (new row)
2. Hunter.io node (find email)
3. Resend (or HTTP) node to send cold email

See [02-setup.md](02-setup.md) for Google Sheets config.
