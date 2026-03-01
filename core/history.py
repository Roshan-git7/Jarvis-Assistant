"""
Conversation history module.
Stores and retrieves the assistant's conversation log in a local JSON file.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import List, Dict

from config import HISTORY_FILE, MAX_HISTORY, DATA_DIR

logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


def _load() -> List[Dict]:
    """Load conversation history from disk."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load history: %s", exc)
        return []


def _save(history: List[Dict]) -> None:
    """Persist conversation history to disk."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as fh:
            json.dump(history, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Could not save history: %s", exc)


def add_entry(role: str, message: str) -> None:
    """Append a new entry to the conversation history.

    Args:
        role: ``"user"`` or ``"assistant"``.
        message: The text of the message.
    """
    history = _load()
    history.append(
        {
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    # Trim to the configured maximum
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    _save(history)


def get_history(limit: int = 20) -> List[Dict]:
    """Return the most recent *limit* entries from the conversation history."""
    history = _load()
    return history[-limit:]


def clear_history() -> None:
    """Delete all conversation history."""
    _save([])
    logger.info("Conversation history cleared.")
