"""
Email draft automation feature.
Opens the user's default mail client with a pre-filled compose window using
the ``mailto:`` URI scheme, falling back to Gmail in the browser when the
system mail handler is not configured.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import webbrowser
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def draft_email(text: str) -> str:
    """Parse *text* and open a compose window with pre-filled fields.

    Supported patterns
    ------------------
    * "draft email to alice@example.com subject Meeting body See you at 3pm"
    * "compose email to bob@example.com Hi there"
    * "send email to carol@example.com subject Hello body How are you?"
    * "email alice@example.com"
    """
    to, subject, body = _parse_email(text)
    if not to:
        return (
            "Please specify a recipient, e.g. "
            "'draft email to alice@example.com subject Hello body Hi there'."
        )

    mailto = _build_mailto(to, subject, body)
    try:
        webbrowser.open(mailto)
        return f"Email compose window opened for {to}."
    except Exception as exc:
        logger.error("Failed to open email client: %s", exc)
        # Fallback: open Gmail compose
        return _open_gmail(to, subject, body)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_email(text: str) -> Tuple[Optional[str], str, str]:
    """Extract (to, subject, body) from an email command string."""
    to: Optional[str] = None
    subject: str = ""
    body: str = ""

    # Extract email address
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
    if email_match:
        to = email_match.group(0)

    # Extract subject
    sub_match = re.search(r"\bsubject\b\s+(.+?)(?:\bbody\b|$)", text, re.IGNORECASE)
    if sub_match:
        subject = sub_match.group(1).strip()

    # Extract body
    body_match = re.search(r"\bbody\b\s+(.+)$", text, re.IGNORECASE)
    if body_match:
        body = body_match.group(1).strip()

    # If no explicit subject/body, use remaining text after email address as body
    if to and not subject and not body:
        remainder = text[email_match.end():].strip()
        # Strip leading conjunctions
        remainder = re.sub(r"^(saying|message|:)\s*", "", remainder, flags=re.IGNORECASE)
        body = remainder

    return to, subject, body


def _build_mailto(to: str, subject: str, body: str) -> str:
    """Build a ``mailto:`` URI."""
    params: dict[str, str] = {}
    if subject:
        params["subject"] = subject
    if body:
        params["body"] = body
    query = urllib.parse.urlencode(params)
    return f"mailto:{to}{'?' + query if query else ''}"


def _open_gmail(to: str, subject: str, body: str) -> str:
    """Open Gmail compose as a fallback."""
    params = {
        "to": to,
        "su": subject,
        "body": body,
        "tf": "cm",
        "fs": "1",
    }
    url = "https://mail.google.com/mail/?" + urllib.parse.urlencode(params)
    try:
        webbrowser.open(url)
        return f"Opened Gmail compose for {to}."
    except Exception as exc:
        logger.error("Gmail fallback failed: %s", exc)
        return f"Could not open email client: {exc}"
