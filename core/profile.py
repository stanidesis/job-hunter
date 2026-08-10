"""Profile management — per-user-profile search/scoring/outreach config.

Each profile is a JSON blob stored in the `profiles` table. Exactly one profile
is active at a time, tracked via `app_settings.active_profile_id`.

Downstream consumers (scorer, hunter, emailer, collector) call
`get_active_profile()` to pick up current settings. Cache is invalidated
automatically on activate/update/delete.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.database import get_connection

SCHEMA_VERSION = 2
PROFILES_DIR = Path(__file__).parent.parent / "profiles"

_CACHE_LOCK = threading.Lock()
_ACTIVE_CACHE: dict = {"id": None, "name": None, "config": None}


# Known free/paid job-board source ids the collector understands.
# Empty search.job_board_sources = enable all (backward compatible).
KNOWN_JOB_BOARD_SOURCES = ("remotive", "remoteok", "arbeitnow", "jsearch")


# ── Defaults ──────────────────────────────────────────────────────────

def default_config() -> dict:
    """Return a valid, complete config dict."""
    return {
        "schema_version": SCHEMA_VERSION,
        "search": {
            "default_terms": [],
            "title_keywords_positive": [],
            "title_keywords_negative": [],
            "relevant_skills": [],
            "jsearch_default_queries": [],
            # Empty = all known boards (compat). Non-empty = only listed boards.
            "job_board_sources": [],
        },
        "scoring": {
            "experience_target": "mid",
            "min_relevance_score": 50,
            "min_score_to_store": 25,
            "weights": {"title": 35, "skills": 35, "experience": 15, "signal": 15},
            "core_skills": [],
            "domain_signals": [],
            "experience_bonuses": {
                "fresher": {"fresher": 15, "junior": 10, "mid": 0,   "senior": -5},
                "junior":  {"fresher": 5,  "junior": 15, "mid": 5,   "senior": -5},
                "mid":     {"fresher": -10,"junior": 0,  "mid": 15,  "senior": 10},
                "senior":  {"fresher": -15,"junior": -5, "mid": 10,  "senior": 15},
                "any":     {"fresher": 10, "junior": 10, "mid": 10,  "senior": 10},
            },
        },
        "location": {
            "preferred_locations": [],
            "excluded_locations": [],
            "work_types": [],  # remote | hybrid | onsite; empty = any
            "timezone_compatible": [],
            "timezone_incompatible": [],
            # When true, hard-drop mismatches at collect/store (and outreach).
            # Default false keeps soft-score behavior (identical to pre-PR3).
            "strict_location_fit": False,  # drop location_fit == "no"
            "strict_work_type": False,     # drop known work_type not in work_types
        },
        "outreach": {
            "candidate_name": "",
            "candidate_core_skills": [],
            "candidate_extra_skills": [],
            "linkedin_search_titles": [
                {"title": "Engineering Manager", "label": "Eng Manager", "category": "engineering"},
                {"title": "Tech Lead", "label": "Tech Lead", "category": "engineering"},
                {"title": "Head of Engineering", "label": "Head of Eng", "category": "executive"},
                {"title": "CTO", "label": "CTO", "category": "executive"},
                {"title": "CEO Founder", "label": "CEO / Founder", "category": "executive"},
                {"title": "Technical Recruiter", "label": "Tech Recruiter", "category": "hr"},
                {"title": "HR Manager", "label": "HR Manager", "category": "hr"},
                {"title": "Talent Acquisition", "label": "TA", "category": "hr"},
            ],
            "bio_short": "",
            "achievements": [],
            "dm_short_template": (
                "{greeting}, I noticed {company} is hiring for {title}. "
                "I have {bio_short}. Would love to connect."
            ),
            "dm_long_template": (
                "{greeting},\n\n"
                "Noticed {company} is hiring for {title}. "
                "I've been working with {skills} and thought there might be a fit.\n\n"
                "{achievements}\n\n"
                "Open to a short chat?\n\n"
                "Thanks,\n{candidate_name}"
            ),
            "email_digest_subject_role": "matching",
            "email_greeting": "Your Daily Job Digest",
            "recipient_email": "",
            "email_hour": 9,
            "email_minute": 0,
            "email_timezone": "UTC",
        },
    }


def validate_config(config: dict) -> dict:
    """Deep-merge submitted config onto defaults so every expected key exists."""
    base = default_config()
    merged = _deep_merge(base, config or {})

    target = merged["scoring"].get("experience_target", "mid")
    if target not in ("fresher", "junior", "mid", "senior", "any"):
        merged["scoring"]["experience_target"] = "mid"

    w = merged["scoring"].get("weights") or {}
    for k in ("title", "skills", "experience", "signal"):
        try:
            w[k] = max(0, int(w.get(k, base["scoring"]["weights"][k])))
        except (TypeError, ValueError):
            w[k] = base["scoring"]["weights"][k]
    merged["scoring"]["weights"] = w

    # Normalize work_types
    allowed_wt = {"remote", "hybrid", "onsite"}
    raw_wt = merged["location"].get("work_types") or []
    merged["location"]["work_types"] = [
        wt.lower().replace("on-site", "onsite").replace("on site", "onsite")
        for wt in raw_wt
        if str(wt).lower().replace("on-site", "onsite").replace("on site", "onsite") in allowed_wt
    ]

    # Strict filter flags (bool; accept common truthy strings from YAML/UI)
    loc = merged["location"]
    loc["strict_location_fit"] = _as_bool(loc.get("strict_location_fit"), False)
    loc["strict_work_type"] = _as_bool(loc.get("strict_work_type"), False)

    # Normalize job_board_sources (empty = all boards at collect time)
    allowed_boards = set(KNOWN_JOB_BOARD_SOURCES)
    raw_boards = merged["search"].get("job_board_sources") or []
    if not isinstance(raw_boards, list):
        raw_boards = []
    seen = set()
    cleaned_boards = []
    for name in raw_boards:
        key = str(name).strip().lower()
        if key in allowed_boards and key not in seen:
            seen.add(key)
            cleaned_boards.append(key)
    merged["search"]["job_board_sources"] = cleaned_boards

    # Email schedule
    out = merged["outreach"]
    try:
        out["email_hour"] = max(0, min(23, int(out.get("email_hour", 9))))
    except (TypeError, ValueError):
        out["email_hour"] = 9
    try:
        out["email_minute"] = max(0, min(59, int(out.get("email_minute", 0))))
    except (TypeError, ValueError):
        out["email_minute"] = 0
    tz = (out.get("email_timezone") or "UTC").strip()
    out["email_timezone"] = tz or "UTC"

    merged["schema_version"] = SCHEMA_VERSION
    return merged


def _as_bool(value, default: bool = False) -> bool:
    """Coerce config values to bool (YAML/JSON/UI-safe)."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ── Cache ─────────────────────────────────────────────────────────────

def invalidate_cache() -> None:
    with _CACHE_LOCK:
        _ACTIVE_CACHE["id"] = None
        _ACTIVE_CACHE["name"] = None
        _ACTIVE_CACHE["config"] = None


def _cache_set(pid: int, name: str, config: dict) -> None:
    with _CACHE_LOCK:
        _ACTIVE_CACHE["id"] = pid
        _ACTIVE_CACHE["name"] = name
        _ACTIVE_CACHE["config"] = config


# ── Public API ────────────────────────────────────────────────────────

def get_active_profile() -> dict:
    """Returns the full active profile config, cached. Always returns a
    valid dict (falls back to default_config() if no profile is set)."""
    with _CACHE_LOCK:
        if _ACTIVE_CACHE["config"] is not None:
            cfg = dict(_ACTIVE_CACHE["config"])
            cfg["_id"] = _ACTIVE_CACHE["id"]
            cfg["_name"] = _ACTIVE_CACHE["name"]
            return cfg

    pid = _read_active_profile_id()
    if pid is None:
        cfg = default_config()
        cfg["_id"] = None
        cfg["_name"] = "(none)"
        return cfg

    row = _read_profile_row(pid)
    if not row:
        cfg = default_config()
        cfg["_id"] = None
        cfg["_name"] = "(none)"
        return cfg

    config = validate_config(json.loads(row["config_json"]))
    _cache_set(row["id"], row["name"], config)
    out = dict(config)
    out["_id"] = row["id"]
    out["_name"] = row["name"]
    return out


def get_email_schedule() -> dict:
    """Return hour/minute/timezone for the daily digest from active profile,
    falling back to env settings."""
    from config import settings as s
    profile = get_active_profile()
    out = profile.get("outreach") or {}
    return {
        "hour": int(out.get("email_hour", getattr(s, "DAILY_EMAIL_HOUR", 9))),
        "minute": int(out.get("email_minute", getattr(s, "DAILY_EMAIL_MINUTE", 0))),
        "timezone": (out.get("email_timezone") or getattr(s, "DAILY_EMAIL_TIMEZONE", "UTC")),
    }


def list_profiles() -> list[dict]:
    """Return summary rows (no config blob) + is_active flag."""
    active_id = _read_active_profile_id()
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, description, source, created_at, updated_at "
        "FROM profiles ORDER BY id"
    ).fetchall()
    conn.close()
    return [
        {**dict(r), "is_active": (r["id"] == active_id)}
        for r in rows
    ]


def get_profile(pid: int) -> Optional[dict]:
    row = _read_profile_row(pid)
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "source": row["source"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "config": validate_config(json.loads(row["config_json"])),
    }


def create_profile(name: str, config: dict, description: str = "",
                   source: str = "custom") -> int:
    ts = datetime.utcnow().isoformat()
    cfg = validate_config(config)
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO profiles (name, description, config_json, created_at, updated_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, json.dumps(cfg), ts, ts, source),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_profile(pid: int, config: dict = None, name: str = None,
                   description: str = None) -> None:
    conn = get_connection()
    try:
        updates = []
        params: list = []
        if config is not None:
            updates.append("config_json = ?")
            params.append(json.dumps(validate_config(config)))
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if not updates:
            return
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(pid)
        conn.execute(f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()

    if _read_active_profile_id() == pid:
        invalidate_cache()


def activate_profile(pid: int) -> None:
    row = _read_profile_row(pid)
    if not row:
        raise ValueError(f"Profile {pid} not found")
    conn = get_connection()
    try:
        ts = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) "
            "VALUES ('active_profile_id', ?, ?)",
            (str(pid), ts),
        )
        conn.commit()
    finally:
        conn.close()
    invalidate_cache()


def delete_profile(pid: int) -> None:
    if _read_active_profile_id() == pid:
        raise ValueError("Cannot delete the active profile. Activate another first.")
    conn = get_connection()
    try:
        conn.execute("DELETE FROM profiles WHERE id = ?", (pid,))
        conn.commit()
    finally:
        conn.close()


def duplicate_profile(pid: int, new_name: str = None) -> int:
    row = _read_profile_row(pid)
    if not row:
        raise ValueError(f"Profile {pid} not found")
    name = new_name or f"{row['name']} (copy)"
    return create_profile(
        name=name,
        config=json.loads(row["config_json"]),
        description=row["description"],
        source="custom",
    )


# ── Preset import / export ────────────────────────────────────────────

def list_presets() -> list[dict]:
    """Scan the profiles/ directory for .yaml files."""
    if not PROFILES_DIR.exists():
        return []
    presets = []
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        meta = _read_preset_meta(path)
        if meta:
            presets.append(meta)
    return presets


def _read_preset_meta(path: Path) -> Optional[dict]:
    import yaml
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return None
    return {
        "slug": path.stem,
        "name": data.get("name", path.stem),
        "description": data.get("description", ""),
    }


def import_preset(slug: str, activate: bool = False,
                  overwrite: bool = False) -> int:
    """Load profiles/<slug>.yaml into the profiles table."""
    import yaml
    path = PROFILES_DIR / f"{slug}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Preset not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    name = data.get("name") or slug
    description = data.get("description", "")
    config = {k: v for k, v in data.items() if k not in ("name", "description")}
    cfg = validate_config(config)

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM profiles WHERE name = ?", (name,)
        ).fetchone()
        ts = datetime.utcnow().isoformat()
        if existing and overwrite:
            pid = existing["id"]
            conn.execute(
                "UPDATE profiles SET description = ?, config_json = ?, "
                "updated_at = ?, source = ? WHERE id = ?",
                (description, json.dumps(cfg), ts, f"preset:{slug}", pid),
            )
        elif existing:
            name = f"{name} (imported {ts[:10]})"
            cur = conn.execute(
                "INSERT INTO profiles (name, description, config_json, "
                "created_at, updated_at, source) VALUES (?, ?, ?, ?, ?, ?)",
                (name, description, json.dumps(cfg), ts, ts, f"preset:{slug}"),
            )
            pid = cur.lastrowid
        else:
            cur = conn.execute(
                "INSERT INTO profiles (name, description, config_json, "
                "created_at, updated_at, source) VALUES (?, ?, ?, ?, ?, ?)",
                (name, description, json.dumps(cfg), ts, ts, f"preset:{slug}"),
            )
            pid = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    if activate:
        activate_profile(pid)
    return pid


def export_profile(pid: int) -> str:
    """Serialize a profile back to YAML."""
    import yaml
    row = _read_profile_row(pid)
    if not row:
        raise ValueError(f"Profile {pid} not found")
    config = validate_config(json.loads(row["config_json"]))
    out = {
        "name": row["name"],
        "description": row["description"],
        **config,
    }
    return yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=100)


# ── Search-query seeding (on preset import) ──────────────────────────

def seed_search_queries_from_profile(pid: int, replace: bool = False) -> int:
    """Push a profile's jsearch_default_queries into the search_queries table.

    Note: live JSearch list is stored on the profile itself; this remains for
    any residual table consumers.
    """
    from core.database import (
        get_search_queries, add_search_query, delete_search_query,
    )
    row = _read_profile_row(pid)
    if not row:
        return 0
    config = validate_config(json.loads(row["config_json"]))
    queries = config["search"].get("jsearch_default_queries") or []

    if replace:
        existing = get_search_queries()
        for q in existing:
            delete_search_query(q["id"])

    if not queries:
        return 0

    existing_keys = set()
    if not replace:
        for q in get_search_queries():
            existing_keys.add((q["query"].strip().lower(), q["country"]))

    added = 0
    for q in queries:
        key = (str(q.get("query", "")).strip().lower(), q.get("country", "us"))
        if not key[0]:
            continue
        if key in existing_keys:
            continue
        add_search_query(
            query=q.get("query", ""),
            country=q.get("country", "us"),
            date_posted=q.get("date_posted", "3days"),
            remote_jobs_only=bool(q.get("remote_jobs_only", False)),
        )
        added += 1
    return added


def ensure_first_run_seed() -> Optional[int]:
    """Idempotent: if profiles table is empty, import a neutral blank profile
    and set it active. Returns the new profile id, or None if not needed."""
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        if count > 0:
            return None
        ts = datetime.utcnow().isoformat()
        cfg = default_config()
        cfg["outreach"]["dm_short_template"] = (
            "{greeting}, I noticed {company} is hiring for {title}. "
            "I have {bio_short}. Would love to connect."
        )
        cur = conn.execute(
            "INSERT INTO profiles (name, description, config_json, created_at, updated_at, source) "
            "VALUES (?, ?, ?, ?, ?, 'seed')",
            ("Default",
             "Blank starter profile. Import a preset or edit to match your role.",
             json.dumps(cfg), ts, ts),
        )
        pid = cur.lastrowid
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) "
            "VALUES ('active_profile_id', ?, ?)",
            (str(pid), ts),
        )
        conn.commit()
        return pid
    finally:
        conn.close()


# ── Private helpers ───────────────────────────────────────────────────

def _read_active_profile_id() -> Optional[int]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'active_profile_id'"
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if not row:
        return None
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return None


def _read_profile_row(pid: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM profiles WHERE id = ?", (pid,)
        ).fetchone()
    finally:
        conn.close()


# ── JSearch-query CRUD against the active profile ─────────────────────

def _load_active_profile_config() -> tuple[Optional[int], dict]:
    pid = _read_active_profile_id()
    if pid is None:
        return None, default_config()
    row = _read_profile_row(pid)
    if not row:
        return None, default_config()
    return pid, validate_config(json.loads(row["config_json"]))


def get_active_profile_queries() -> list[dict]:
    """Return the active profile's jsearch queries with synthetic ids."""
    _, cfg = _load_active_profile_config()
    raw = (cfg.get("search") or {}).get("jsearch_default_queries") or []
    out = []
    for idx, q in enumerate(raw):
        out.append({
            "id": idx,
            "query": q.get("query", ""),
            "country": q.get("country", "us"),
            "date_posted": q.get("date_posted", "3days"),
            "remote_jobs_only": bool(q.get("remote_jobs_only", False)),
            "enabled": bool(q.get("enabled", True)),
        })
    return out


def add_active_profile_query(query: str, country: str = "us",
                             date_posted: str = "3days",
                             remote_jobs_only: bool = False) -> int:
    """Append a query to the active profile. Returns its new index."""
    pid, cfg = _load_active_profile_config()
    if pid is None:
        raise ValueError("No active profile")
    queries = list((cfg.get("search") or {}).get("jsearch_default_queries") or [])
    queries.append({
        "query": query,
        "country": country,
        "date_posted": date_posted,
        "remote_jobs_only": bool(remote_jobs_only),
        "enabled": True,
    })
    cfg["search"]["jsearch_default_queries"] = queries
    update_profile(pid, config=cfg)
    return len(queries) - 1


def update_active_profile_query(qid: int, **fields) -> None:
    pid, cfg = _load_active_profile_config()
    if pid is None:
        raise ValueError("No active profile")
    queries = list((cfg.get("search") or {}).get("jsearch_default_queries") or [])
    if qid < 0 or qid >= len(queries):
        raise ValueError(f"Query index {qid} out of range")
    allowed = {"query", "country", "date_posted", "remote_jobs_only", "enabled"}
    for k, v in fields.items():
        if k in allowed and v is not None:
            queries[qid][k] = v
    cfg["search"]["jsearch_default_queries"] = queries
    update_profile(pid, config=cfg)


def delete_active_profile_query(qid: int) -> None:
    pid, cfg = _load_active_profile_config()
    if pid is None:
        raise ValueError("No active profile")
    queries = list((cfg.get("search") or {}).get("jsearch_default_queries") or [])
    if qid < 0 or qid >= len(queries):
        raise ValueError(f"Query index {qid} out of range")
    queries.pop(qid)
    cfg["search"]["jsearch_default_queries"] = queries
    update_profile(pid, config=cfg)
