"""
Notes management feature.
Notes are stored locally in a JSON file.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict

from config import NOTES_FILE, DATA_DIR

logger = logging.getLogger(__name__)

os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _load() -> List[Dict]:
    if not os.path.exists(NOTES_FILE):
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load notes: %s", exc)
        return []


def _save(notes: List[Dict]) -> None:
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as fh:
            json.dump(notes, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Could not save notes: %s", exc)


def _next_id(notes: List[Dict]) -> int:
    return max((n["id"] for n in notes), default=0) + 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_note(text: str) -> str:
    """Parse *text* and store a new note.

    Supported patterns
    ------------------
    * "take a note: <content>"
    * "add note <content>"
    * "note that <content>"
    * "write down <content>"
    * "make a note: <content>"
    """
    content = _extract_content(text)
    if not content:
        return "What would you like me to note? Please say the note content."
    notes = _load()
    entry: Dict = {
        "id": _next_id(notes),
        "content": content,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    notes.append(entry)
    _save(notes)
    return f"Note saved: '{content}'."


def list_notes() -> str:
    """Return a formatted list of all notes."""
    notes = _load()
    if not notes:
        return "You have no saved notes."
    lines = [f"[{n['id']}] {n['content']}  ({n['created_at'][:10]})" for n in notes]
    return "Your notes:\n" + "\n".join(lines)


def delete_note(text: str) -> str:
    """Delete the note whose ID appears in *text*."""
    match = re.search(r"\b(\d+)\b", text)
    if not match:
        return "Please specify the note ID to delete, e.g. 'delete note 2'."
    nid = int(match.group(1))
    notes = _load()
    new_notes = [n for n in notes if n["id"] != nid]
    if len(new_notes) == len(notes):
        return f"No note found with ID {nid}."
    _save(new_notes)
    return f"Note {nid} deleted."


def search_notes(text: str) -> str:
    """Search notes whose content contains the keyword in *text*."""
    keyword = _extract_keyword(text)
    if not keyword:
        return "Please provide a keyword to search, e.g. 'search notes groceries'."
    notes = _load()
    matches = [n for n in notes if keyword.lower() in n["content"].lower()]
    if not matches:
        return f"No notes found matching '{keyword}'."
    lines = [f"[{n['id']}] {n['content']}" for n in matches]
    return f"Notes matching '{keyword}':\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_content(text: str) -> str:
    """Return the note body from a command string."""
    lowered = text.lower()
    for pattern in (
        r"(?:take a note|add note|make a note|note that|write down)\s*:?\s*(.+)$",
    ):
        m = re.search(pattern, lowered, re.IGNORECASE)
        if m:
            # Preserve original capitalisation
            start = m.start(1)
            return text[start:].strip()
    return text.strip()


def _extract_keyword(text: str) -> str:
    """Return the search keyword from a command string."""
    m = re.search(r"(?:search notes?|find note?)\s+(.+)$", text, re.IGNORECASE)
    return m.group(1).strip() if m else text.strip()
