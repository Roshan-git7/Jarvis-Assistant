"""
Reminder management feature.
Reminders are stored locally in a JSON file with ISO-8601 timestamps.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict

from config import REMINDERS_FILE, DATA_DIR

logger = logging.getLogger(__name__)

os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _load() -> List[Dict]:
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load reminders: %s", exc)
        return []


def _save(reminders: List[Dict]) -> None:
    try:
        with open(REMINDERS_FILE, "w", encoding="utf-8") as fh:
            json.dump(reminders, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Could not save reminders: %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_reminder(text: str) -> str:
    """Parse *text* and store a new reminder.

    Supported patterns
    ------------------
    * "remind me to <task> at <time>"
    * "remind me to <task> on <date>"
    * "set reminder: <text>"
    * "add reminder <text>"

    If no time/date is found the reminder is stored without a scheduled time.
    """
    task, when = _parse_reminder(text)
    reminders = _load()
    entry: Dict = {
        "id": _next_id(reminders),
        "task": task,
        "when": when,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "done": False,
    }
    reminders.append(entry)
    _save(reminders)
    when_str = f" at {when}" if when else ""
    return f"Reminder set: '{task}'{when_str}."


def list_reminders() -> str:
    """Return a formatted list of all pending reminders."""
    reminders = [r for r in _load() if not r.get("done")]
    if not reminders:
        return "You have no pending reminders."
    lines = [
        f"[{r['id']}] {r['task']}" + (f" — {r['when']}" if r.get("when") else "")
        for r in reminders
    ]
    return "Your reminders:\n" + "\n".join(lines)


def delete_reminder(text: str) -> str:
    """Delete the reminder whose ID appears in *text*."""
    match = re.search(r"\b(\d+)\b", text)
    if not match:
        return "Please specify the reminder ID to delete, e.g. 'delete reminder 3'."
    rid = int(match.group(1))
    reminders = _load()
    for r in reminders:
        if r["id"] == rid:
            r["done"] = True
            _save(reminders)
            return f"Reminder {rid} deleted."
    return f"No reminder found with ID {rid}."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_reminder(text: str) -> tuple[str, str]:
    """Extract (task, when_string) from a reminder command.

    Searches case-insensitively but returns substrings from the original
    *text* so that capitalisation is preserved.
    """
    # "remind me to X at/on Y"
    m = re.search(
        r"remind(?:\s+me)?\s+to\s+(.+?)\s+(?:at|on)\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # "remind me to X" (no time)
    m = re.search(r"remind(?:\s+me)?\s+to\s+(.+)$", text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), ""

    # Strip known prefixes and use the remainder as the task
    lowered = text.lower()
    for prefix in ("set reminder:", "add reminder", "set reminder", "remind me"):
        if lowered.startswith(prefix):
            return text[len(prefix):].strip(), ""

    return text.strip(), ""


def _next_id(reminders: List[Dict]) -> int:
    return max((r["id"] for r in reminders), default=0) + 1
