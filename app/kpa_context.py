"""
KPA context loader.

Loads the skills matrix for the user's selected level and provides
the structured KPA categories and criteria to the AI prompt.
"""

import os
import sys

# ── KPA category constants ────────────────────────────────────────────────────
# These are the canonical category names used for folder filing.
KPA_CATEGORIES = [
    "Technical Mastery",
    "Engineering Operations",
    "Consultant Mindset & Delivery",
    "Communication & Collaboration",
    "Continuous Growth",
    "Leadership & Culture",
    "Team Management",
]

# Levels that have Team Management KPA
TEAM_LEAD_LEVELS = {"Tech Lead"}

# Map display level names → skills matrix filenames
_LEVEL_FILE_MAP = {
    "Intern":        "intern.txt",
    "Graduate":      "graduate.txt",
    "Junior":        "junior.txt",
    "Intermediate":  "intermediate.txt",
    "Senior":        "senior.txt",
    "Tech Lead":     "tech_lead.txt",
}

# All available levels in display order
ALL_LEVELS = list(_LEVEL_FILE_MAP.keys())


def _matrix_dir() -> str:
    """
    Resolve the skills_matrix directory whether running in dev or
    bundled as a PyInstaller EXE (where files live in sys._MEIPASS).
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "app", "skills_matrix")
    return os.path.join(os.path.dirname(__file__), "skills_matrix")


def load_skills_matrix(level: str) -> str:
    """
    Return the full text of the skills matrix for the given level.
    Falls back to an empty string with a warning if the file is missing.
    """
    filename = _LEVEL_FILE_MAP.get(level)
    if not filename:
        return f"No skills matrix found for level: {level}"

    path = os.path.join(_matrix_dir(), filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Skills matrix file not found: {path}"


def get_categories_for_level(level: str) -> list[str]:
    """Return the applicable KPA categories for the given level."""
    if level in TEAM_LEAD_LEVELS:
        return KPA_CATEGORIES  # includes Team Management
    return [c for c in KPA_CATEGORIES if c != "Team Management"]


def build_classification_prompt(level: str, user_context: str,
                                 custom_prompt: str = "") -> str:
    """
    Build a richly-contextualised AI classification prompt by injecting
    the full skills matrix for the user's level.

    The AI is given:
      - The developer's exact role profile and KPA criteria
      - The user's own context about the screenshot
      - Instructions to pick the single best-fitting KPA category
    """
    matrix   = load_skills_matrix(level)
    cats     = get_categories_for_level(level)
    cat_list = "\n".join(f"  - {c}" for c in cats)

    prompt = f"""You are a Performance Auditor analyzing a developer's Portfolio of Evidence (PoE) screenshot.

=== DEVELOPER LEVEL: {level.upper()} ===

{matrix}

=== YOUR TASK ===
Analyze the provided screenshot and the developer's context below.
Using the skills matrix above for a {level} developer, determine which single KPA category this evidence best demonstrates.

Available KPA categories for a {level} developer:
{cat_list}

Developer's context about this screenshot:
"{user_context if user_context.strip() else 'No context provided — analyze the screenshot content directly.'}"

{custom_prompt}

=== OUTPUT FORMAT (strictly follow this) ===
CATEGORY | STAR SUMMARY

Where:
- CATEGORY is exactly one of the KPA categories listed above
- STAR SUMMARY is a concise 2-3 sentence description using the STAR method (Situation, Task, Action, Result)
  written from the developer's perspective, referencing what is visible in the screenshot

Example output:
Technical Mastery | Situation: Working on a payment microservice. Task: Implement secure API endpoint. Action: Wrote input validation and JWT authentication as visible in the code review screenshot. Result: PR approved with no security concerns raised.
"""
    return prompt
