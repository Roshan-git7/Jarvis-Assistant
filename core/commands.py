"""
Command routing module for JARVIS.
Maps recognised intents to feature handlers and returns a response string.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent keywords
# ---------------------------------------------------------------------------
_INTENTS: list[Tuple[str, list[str]]] = [
    ("reminder_add",    ["remind me", "set reminder", "add reminder"]),
    ("reminder_list",   ["list reminders", "show reminders", "my reminders"]),
    ("reminder_delete", ["delete reminder", "remove reminder", "cancel reminder"]),
    ("note_add",        ["take a note", "add note", "make a note", "note that", "write down"]),
    ("note_list",       ["list notes", "show notes", "my notes", "read notes"]),
    ("note_delete",     ["delete note", "remove note"]),
    ("note_search",     ["search notes", "find note"]),
    ("open_website",    ["open website", "go to", "visit", "browse"]),
    ("open_app",        ["open app", "launch app", "start app", "open application"]),
    ("whatsapp_send",   ["whatsapp", "send whatsapp", "message on whatsapp"]),
    ("email_draft",     ["email", "send email", "draft email", "compose email", "mail to"]),
    ("face_learn",      ["learn face", "remember face", "add face", "save face"]),
    ("face_recognize",  ["recognize face", "identify face", "who is this", "face recognition"]),
    ("face_list",       ["list faces", "show faces", "known faces"]),
    ("history_show",    ["show history", "conversation history", "chat history"]),
    ("history_clear",   ["clear history", "delete history"]),
    ("help",            ["help", "what can you do", "commands", "features"]),
    ("greeting",        ["hello", "hi jarvis", "hey jarvis", "good morning", "good evening", "good afternoon"]),
    ("farewell",        ["bye", "goodbye", "exit", "quit", "stop", "shutdown"]),
    ("openai_query",    []),   # fallback – handled last
]


def detect_intent(text: str) -> str:
    """Return the intent label that best matches *text*."""
    lowered = text.lower()
    for intent, keywords in _INTENTS:
        if intent == "openai_query":
            continue
        for kw in keywords:
            if kw in lowered:
                return intent
    return "openai_query"


def handle(text: str) -> str:
    """Route *text* to the appropriate feature and return a response string.

    All feature imports are performed lazily so that missing optional
    dependencies do not crash the whole assistant.
    """
    intent = detect_intent(text)
    logger.debug("Intent detected: %s | text: %s", intent, text)

    try:
        if intent == "reminder_add":
            from features.reminders import add_reminder
            return add_reminder(text)

        elif intent == "reminder_list":
            from features.reminders import list_reminders
            return list_reminders()

        elif intent == "reminder_delete":
            from features.reminders import delete_reminder
            return delete_reminder(text)

        elif intent == "note_add":
            from features.notes import add_note
            return add_note(text)

        elif intent == "note_list":
            from features.notes import list_notes
            return list_notes()

        elif intent == "note_delete":
            from features.notes import delete_note
            return delete_note(text)

        elif intent == "note_search":
            from features.notes import search_notes
            return search_notes(text)

        elif intent == "open_website":
            from features.web_launcher import open_website
            return open_website(text)

        elif intent == "open_app":
            from features.web_launcher import open_app
            return open_app(text)

        elif intent == "whatsapp_send":
            from features.whatsapp import send_whatsapp
            return send_whatsapp(text)

        elif intent == "email_draft":
            from features.email_draft import draft_email
            return draft_email(text)

        elif intent == "face_learn":
            from features.face_memory import learn_face
            return learn_face(text)

        elif intent == "face_recognize":
            from features.face_memory import recognize_face
            return recognize_face()

        elif intent == "face_list":
            from features.face_memory import list_faces
            return list_faces()

        elif intent == "history_show":
            from core.history import get_history
            entries = get_history()
            if not entries:
                return "No conversation history yet."
            lines = [f"[{e['timestamp']}] {e['role'].capitalize()}: {e['message']}" for e in entries]
            return "\n".join(lines)

        elif intent == "history_clear":
            from core.history import clear_history
            clear_history()
            return "Conversation history cleared."

        elif intent == "help":
            return _help_text()

        elif intent == "greeting":
            return "Hello! I'm JARVIS, your personal assistant. How can I help you today?"

        elif intent == "farewell":
            return "FAREWELL"

        else:  # openai_query
            return _openai_fallback(text)

    except Exception as exc:
        logger.exception("Error handling intent '%s': %s", intent, exc)
        return f"Sorry, something went wrong: {exc}"


def _openai_fallback(text: str) -> str:
    """Use OpenAI to answer a query; fall back to a canned response if unavailable."""
    try:
        from config import OPENAI_API_KEY, OPENAI_MODEL
        if not OPENAI_API_KEY:
            raise ValueError("No API key configured.")
        import openai  # type: ignore
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": text}],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("OpenAI unavailable: %s", exc)
        return (
            "I'm not sure how to answer that. "
            "For smarter responses, set your OPENAI_API_KEY in the .env file."
        )


def _help_text() -> str:
    return (
        "Here is what I can do:\n"
        "  • Reminders  – 'remind me to call John at 5pm'\n"
        "  • Notes      – 'take a note: buy groceries'\n"
        "  • Web/Apps   – 'open website youtube.com' | 'open app calculator'\n"
        "  • WhatsApp   – 'send whatsapp to +1234567890 saying Hello'\n"
        "  • Email      – 'draft email to alice@example.com subject Hi body Hello'\n"
        "  • Faces      – 'learn face Alice' | 'recognize face' | 'list faces'\n"
        "  • History    – 'show history' | 'clear history'\n"
        "  • AI Chat    – any other question (requires OPENAI_API_KEY)\n"
        "  • 'help'     – show this message\n"
        "  • 'bye'      – exit"
    )
