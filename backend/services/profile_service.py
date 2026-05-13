"""
Profile service — completeness scoring and profile field analysis.

Calculates a weighted completeness score based on the actual profile.json
structure and the PRD's missing_fields definition.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.config import settings

logger = logging.getLogger(__name__)

# --- Completeness Field Definitions ---
# Each entry: (field_path, weight, display_label)
# field_path uses dot notation; lists checked for non-empty.
# Total weights sum to 100.

COMPLETENESS_FIELDS: List[Tuple[str, float, str]] = [
    # Personal info — 30 points total
    ("personal_info.full_name", 5.0, "full_name"),
    ("personal_info.headline", 3.0, "headline"),
    ("personal_info.summary", 4.0, "summary"),
    ("personal_info.contact.email", 3.0, "email"),
    ("personal_info.contact.phone", 3.0, "phone"),
    ("personal_info.contact.linkedin", 2.0, "linkedin_url"),
    ("personal_info.contact.github", 2.0, "github_url"),
    ("personal_info.contact.portfolio", 2.0, "portfolio_url"),
    ("personal_info.location.city", 3.0, "location_city"),
    ("personal_info.languages", 3.0, "languages"),

    # Education — 12 points total
    ("education", 6.0, "education"),
    ("education[0].start_date", 3.0, "exact_education_dates"),
    ("education[0].grade", 3.0, "gpa"),

    # Work experience — 14 points
    ("work_experience", 14.0, "work_experience"),

    # Skills — 10 points
    ("skills", 10.0, "skills"),

    # Projects — 10 points
    ("projects", 10.0, "projects"),

    # Certifications — 6 points
    ("certifications", 6.0, "certifications"),

    # Personality & work style — 6 points
    ("personality_and_work_style", 6.0, "personality_and_work_style"),

    # Preferences & goals — 6 points
    ("preferences_and_goals", 6.0, "preferences_and_goals"),

    # CV generation hints — 6 points
    ("cv_generation_hints", 6.0, "cv_generation_hints"),
]


def _resolve_field(data: Dict[str, Any], path: str) -> Any:
    """
    Resolve a dot-notation field path from a nested dict.

    Supports special syntax:
      - 'key[0].subkey' → access first element of list, then subkey

    Args:
        data: The nested dictionary to traverse.
        path: Dot-notation path string.

    Returns:
        The resolved value, or None if the path doesn't exist.
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if current is None:
            return None

        # Handle array index syntax: "education[0]"
        if "[" in part and "]" in part:
            key = part[:part.index("[")]
            idx = int(part[part.index("[") + 1:part.index("]")])
            current = current.get(key) if isinstance(current, dict) else None
            if isinstance(current, list) and len(current) > idx:
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


def _is_field_filled(value: Any) -> bool:
    """
    Determine if a field value is considered "filled" (non-empty).

    Args:
        value: The value to check.

    Returns:
        True if the value contains meaningful data.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, (list, dict)):
        return len(value) > 0
    if isinstance(value, bool):
        return True
    return True


def calculate_completeness(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a weighted completeness score for the profile.

    Checks every field defined in COMPLETENESS_FIELDS against the profile data.
    Returns a score (0-100) and list of missing field labels.

    Args:
        profile: The raw profile dictionary from profile.json.

    Returns:
        dict with keys:
          - score (float): Completeness percentage 0-100
          - missing_fields (list[str]): Display labels of missing fields

    Raises:
        ValueError: If profile is None or not a dict.
    """
    if not profile or not isinstance(profile, dict):
        return {"score": 0.0, "missing_fields": [f[2] for f in COMPLETENESS_FIELDS]}

    total_weight = sum(f[1] for f in COMPLETENESS_FIELDS)
    earned_weight = 0.0
    missing_fields = []

    for field_path, weight, label in COMPLETENESS_FIELDS:
        value = _resolve_field(profile, field_path)
        if _is_field_filled(value):
            earned_weight += weight
        else:
            missing_fields.append(label)

    score = round((earned_weight / total_weight) * 100) if total_weight > 0 else 0.0

    # --- Log the decision ---
    _log_completeness_decision(score, missing_fields, earned_weight, total_weight)

    return {"score": score, "missing_fields": missing_fields}


def _log_completeness_decision(
    score: float,
    missing_fields: List[str],
    earned: float,
    total: float
) -> None:
    """
    Write a structured decision log entry for completeness calculation.

    Args:
        score: The calculated completeness score.
        missing_fields: List of missing field labels.
        earned: Total earned weight.
        total: Total possible weight.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (
        f"[{timestamp}] [DECISION] module=profile_service function=calculate_completeness\n"
        f"  score={score} earned_weight={earned}/{total}\n"
        f"  missing_fields={missing_fields}\n"
        f"  action=returned_to_caller\n"
        f"  reasoning=Weighted field check across 18 profile sections. "
        f"Fields weighted by importance to CV generation pipeline. "
        f"education[0].start_date and education[0].grade checked separately "
        f"because exact dates and GPA are commonly missing but valued by HR.\n"
    )
    try:
        log_path = Path(settings.DECISIONS_LOG)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to write decision log: {e}")
