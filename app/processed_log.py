"""
Persistent registry of processed screenshots.

Stored at %APPDATA%/KPI-assistant/processed_log.json as:
  {
    "screenshot.png": {"timestamp": "2026-05-05T18:30:00", "category": "Technical Mastery"},
    ...
  }

Using a dict keyed by filename means lookups are O(1) and the file never
grows duplicate entries even if the watcher fires twice for the same file.
"""

import json
import os
from datetime import datetime


def _load(log_file: str) -> dict:
    if not os.path.exists(log_file):
        return {}
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(log_file: str, data: dict) -> None:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def is_already_processed(filename: str, log_file: str) -> bool:
    return filename in _load(log_file)


def mark_as_processed(filename: str, log_file: str, category: str = "") -> None:
    data = _load(log_file)
    data[filename] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "category":  category,
    }
    _save(log_file, data)


def get_all(log_file: str) -> dict:
    """Returns the full registry — used by the dashboard stats on startup."""
    return _load(log_file)
