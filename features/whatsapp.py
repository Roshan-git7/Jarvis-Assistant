"""
WhatsApp automation feature.
Uses pywhatkit to open WhatsApp Web and pre-fill a message.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def send_whatsapp(text: str) -> str:
    """Parse *text* and send (or schedule) a WhatsApp message.

    Supported patterns
    ------------------
    * "send whatsapp to +1234567890 saying Hello there"
    * "whatsapp +1234567890 message Hi"
    * "message on whatsapp +1234567890 Hi there"

    The message is opened in WhatsApp Web immediately (instant_send=False so
    the user can review before actually sending).
    """
    phone, message = _parse_whatsapp(text)
    if not phone:
        return (
            "Please specify a phone number, e.g. "
            "'send whatsapp to +1234567890 saying Hello'."
        )
    if not message:
        return "Please include a message, e.g. 'send whatsapp to +1234567890 saying Hello'."

    try:
        import pywhatkit as kit  # type: ignore

        # open_web=True opens WhatsApp Web with the message pre-filled.
        # We use sendwhatmsg_instantly which opens the browser immediately.
        kit.sendwhatmsg_instantly(phone, message, wait_time=10, tab_close=False)
        return f"WhatsApp message to {phone} opened in your browser. Review and send."
    except ImportError:
        logger.warning("pywhatkit is not installed.")
        return (
            f"pywhatkit is required for WhatsApp automation. "
            f"Install it with: pip install pywhatkit\n"
            f"Message prepared: '{message}' → {phone}"
        )
    except Exception as exc:
        logger.error("WhatsApp send failed: %s", exc)
        return f"Could not open WhatsApp: {exc}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_whatsapp(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (phone_number, message) from a WhatsApp command string."""
    # Pattern: "... +<phone> saying/message <text>"
    m = re.search(
        r"(\+?\d[\d\s\-]{6,}\d)\s+(?:saying|message|:)\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    if m:
        phone = re.sub(r"[\s\-]", "", m.group(1))
        return phone, m.group(2).strip()

    # Pattern: phone number + remaining text as message
    m = re.search(r"(\+?\d{7,15})\s+(.+)$", text)
    if m:
        return m.group(1), m.group(2).strip()

    # Phone only – no message found
    m = re.search(r"(\+?\d{7,15})", text)
    if m:
        return m.group(1), None

    return None, None
