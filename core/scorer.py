"""Rule-based relevance scorer. No API key needed.

Scores jobs 0-100 based on title, description, and skill/requirement match.
Also detects work type (remote / hybrid / on-site) and location fit against
the active profile's preferred locations and exclusions.

All preferences come from the active profile (see core.profile). Callers can
pass `profile=` to use a specific profile for a batch.
"""

from core.profile import get_active_profile


# Linguistic patterns for work-type detection — not user preferences.
_HYBRID_KW = [
    "hybrid", "days in office", "partially remote", "part remote",
    "office + remote", "remote + office", "2-3 days", "3 days in office",
]
_REMOTE_KW = [
    "remote", "work from home", "wfh", "work from anywhere",
    "distributed team", "fully remote", "100% remote", "remote-first",
    "remote first", "location independent",
]
_ONSITE_KW = [
    "on-site", "onsite", "on site", "in-office", "in office",
    "office-based", "office based", "on premise", "on-premise",
    "on premises", "must be located", "come into the office",
]


def extract_skills(text: str, profile: dict = None) -> list[str]:
    """Extract matching skill/requirement keywords from text."""
    profile = profile or get_active_profile()
    skill_list = profile["search"].get("relevant_skills") or []
    text_lower = text.lower()
    return [s for s in skill_list if s.lower() in text_lower]


def estimate_experience_level(text: str) -> str:
    """Guess experience level from description.

    These keyword lists are linguistic patterns — not user preferences — so
    they stay hardcoded. The profile decides how the detected level is
    *scored* via experience_bonuses, not how it's detected.
    """
    text_lower = text.lower()
    if any(w in text_lower for w in [
        "intern", "internship", "trainee", "entry level", "entry-level",
        "0-1 year", "0-2 years", "fresher", "new grad", "graduate",
        "campus", "freshers",
    ]):
        return "fresher"
    if any(w in text_lower for w in [
        "senior", "sr.", "lead", "principal", "staff",
        "8+ years", "10+ years", "15+ years",
    ]):
        return "senior"
    if any(w in text_lower for w in [
        "junior", "jr.", "1+ year", "1-2 years",
    ]):
        return "junior"
    if any(w in text_lower for w in [
        "mid", "middle", "3+ years", "2+ years", "4+ years", "5+ years",
        "3-5 years", "2-4 years", "4-6 years",
    ]):
        return "mid"
    return "mid"


def detect_work_type(location: str = "", description: str = "",
                     title: str = "") -> str:
    """Detect work arrangement: remote | hybrid | onsite | unknown.

    Priority: hybrid > remote > onsite (hybrid phrases often also say remote).
    """
    full = f"{title} {location} {description}".lower()
    if any(kw in full for kw in _HYBRID_KW):
        return "hybrid"
    if any(kw in full for kw in _REMOTE_KW):
        return "remote"
    if any(kw in full for kw in _ONSITE_KW):
        return "onsite"
    # Bare location string often just says "Remote"
    loc = (location or "").lower().strip()
    if loc in ("remote", "anywhere", "worldwide", "global"):
        return "remote"
    return "unknown"


def check_location_fit(location: str, description: str,
                       profile: dict = None) -> dict:
    """Match a job against the profile's preferred/excluded locations.

    Returns:
        result: 'yes' | 'no' | 'maybe'
        note: explanation string
    """
    profile = profile or get_active_profile()
    loc_cfg = profile.get("location") or {}
    preferred = [kw.lower() for kw in (loc_cfg.get("preferred_locations") or []) if kw]
    excluded = [kw.lower() for kw in (loc_cfg.get("excluded_locations") or []) if kw]
    tz_good_list = [kw.lower() for kw in (loc_cfg.get("timezone_compatible") or []) if kw]
    tz_bad_list = [kw.lower() for kw in (loc_cfg.get("timezone_incompatible") or []) if kw]

    full_text = f"{location} {description}".lower()
    loc_lower = (location or "").lower()

    positive_hits = [kw for kw in preferred if kw in full_text]
    negative_hits = [kw for kw in excluded if kw in full_text]
    tz_good = [kw for kw in tz_good_list if kw in full_text]
    tz_bad = [kw for kw in tz_bad_list if kw in full_text]

    if negative_hits:
        return {
            "result": "no",
            "note": f"Excluded: {', '.join(negative_hits[:3])}",
        }
    if tz_bad:
        return {
            "result": "no",
            "note": f"Timezone mismatch: {', '.join(tz_bad[:2])}",
        }

    # No location preference configured → don't gate
    if not preferred and not excluded and not tz_good_list and not tz_bad_list:
        return {
            "result": "yes",
            "note": "No location preference set",
        }

    if positive_hits:
        return {
            "result": "yes",
            "note": f"Location match: {', '.join(positive_hits[:3])}",
        }

    if tz_good:
        return {
            "result": "maybe",
            "note": f"Compatible timezone: {', '.join(tz_good[:2])}",
        }

    # Remote with no region called out when user prefers remote-friendly places
    if "remote" in loc_lower and preferred:
        global_ish = any(
            g in preferred for g in (
                "worldwide", "anywhere", "global", "remote",
                "work from anywhere", "location independent",
            )
        )
        if global_ish:
            return {
                "result": "maybe",
                "note": "Remote — region not specified",
            }

    if preferred:
        return {
            "result": "maybe",
            "note": "No clear location match for preferred places",
        }

    return {
        "result": "maybe",
        "note": "No clear location signal",
    }


def score_job(title: str, description: str, location: str = "",
              profile: dict = None) -> dict:
    """Score a job 0-100 against the active (or passed) profile."""
    profile = profile or get_active_profile()
    search = profile["search"]
    scoring = profile["scoring"]
    weights = scoring.get("weights") or {}
    w_title = int(weights.get("title", 35))
    w_skills = int(weights.get("skills", 35))
    w_exp = int(weights.get("experience", 15))
    w_signal = int(weights.get("signal", 15))

    pos_titles = search.get("title_keywords_positive") or []
    neg_titles = search.get("title_keywords_negative") or []
    core_skills_list = scoring.get("core_skills") or []
    signal_list = scoring.get("domain_signals") or []
    exp_bonuses = scoring.get("experience_bonuses") or {}
    exp_target = scoring.get("experience_target", "mid")
    preferred_work = [
        wt.lower() for wt in ((profile.get("location") or {}).get("work_types") or [])
        if wt
    ]

    score = 0
    reasons: list[str] = []
    red_flags: list[str] = []
    full_text = f"{title} {description}".lower()
    title_lower = title.lower()

    # Title relevance
    title_matches = [kw for kw in pos_titles if kw in title_lower]
    if title_matches:
        pts = min(len(title_matches) * 12, w_title)
        score += pts
        reasons.append(f"Title match: {', '.join(title_matches[:6])}")

    title_negatives = [kw for kw in neg_titles if kw in title_lower]
    if title_negatives:
        penalty = len(title_negatives) * 15
        score -= penalty
        red_flags.append(f"Title contains: {', '.join(title_negatives[:4])}")

    # Skills: split into core / secondary using profile-declared core_skills.
    # Budget split: ~70% of skills weight for core, ~30% for secondary.
    skills_found = extract_skills(full_text, profile=profile)
    core_skills = [t for t in skills_found if t in core_skills_list]
    secondary_skills = [t for t in skills_found if t not in core_skills]

    core_budget = max(0, int(round(w_skills * 0.71)))
    secondary_budget = max(0, w_skills - core_budget)

    if core_skills:
        score += min(len(core_skills) * 12, core_budget)
        reasons.append(f"Core skills: {', '.join(core_skills)}")
    if secondary_skills:
        score += min(len(secondary_skills) * 3, secondary_budget)
        reasons.append(f"Related skills: {', '.join(secondary_skills[:8])}")

    # Experience
    exp_level = estimate_experience_level(full_text)
    row = exp_bonuses.get(exp_target) or {}
    raw_bonus = int(row.get(exp_level, 0))
    scaled_bonus = int(round(raw_bonus * (w_exp / 15.0)))
    if scaled_bonus > 0:
        score += scaled_bonus
        reasons.append(f"Experience match: {exp_level} (target={exp_target}) +{scaled_bonus}")
    elif scaled_bonus < 0:
        score += scaled_bonus
        red_flags.append(f"Experience mismatch: {exp_level} (target={exp_target}) {scaled_bonus}")
    else:
        reasons.append(f"Experience: {exp_level} (target={exp_target})")

    # Domain signals
    signal_matches = [s for s in signal_list if s in full_text]
    if signal_matches:
        score += min(len(signal_matches) * 4, w_signal)
        reasons.append(f"Signals: {', '.join(signal_matches[:5])}")

    # Work type + location fit (attributes; light score nudge for work type)
    work_type = detect_work_type(location, description, title)
    location_check = check_location_fit(location, description, profile=profile)

    if preferred_work and work_type != "unknown":
        if work_type in preferred_work:
            score += 3
            reasons.append(f"Work type match: {work_type}")
        else:
            score -= 5
            red_flags.append(f"Work type {work_type} not in preferred ({', '.join(preferred_work)})")

    score = max(0, min(100, score))

    return {
        "score": score,
        "matched_skills": skills_found,
        "experience_level": exp_level,
        "reasons": reasons,
        "red_flags": red_flags,
        "location_fit": location_check["result"],
        "location_note": location_check["note"],
        "work_type": work_type,
    }
