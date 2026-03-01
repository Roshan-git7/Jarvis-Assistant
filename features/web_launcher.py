"""
Web and application launcher feature.
Opens URLs in the default browser and desktop applications via subprocess.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
import webbrowser
from typing import Optional

logger = logging.getLogger(__name__)

# Common desktop applications mapped to executable names per platform
_APP_MAP: dict[str, dict[str, str]] = {
    "calculator": {
        "windows": "calc",
        "darwin": "open -a Calculator",
        "linux": "gnome-calculator",
    },
    "notepad": {
        "windows": "notepad",
        "darwin": "open -a TextEdit",
        "linux": "gedit",
    },
    "file manager": {
        "windows": "explorer",
        "darwin": "open .",
        "linux": "nautilus",
    },
    "paint": {
        "windows": "mspaint",
        "darwin": "open -a Preview",
        "linux": "gimp",
    },
    "browser": {
        "windows": "start chrome",
        "darwin": "open -a 'Google Chrome'",
        "linux": "google-chrome",
    },
    "terminal": {
        "windows": "start cmd",
        "darwin": "open -a Terminal",
        "linux": "gnome-terminal",
    },
}

_PLATFORM = platform.system().lower()


def open_website(text: str) -> str:
    """Open a URL extracted from *text* in the default web browser.

    Patterns handled:
    * "open website youtube.com"
    * "go to github.com"
    * "visit https://example.com"
    * "browse google.com"
    """
    url = _extract_url(text)
    if not url:
        return "Sorry, I couldn't identify a URL in your request."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        webbrowser.open(url)
        return f"Opening {url} in your browser."
    except Exception as exc:
        logger.error("Failed to open URL %s: %s", url, exc)
        return f"Could not open {url}: {exc}"


def open_app(text: str) -> str:
    """Launch a desktop application named in *text*.

    Patterns handled:
    * "open app calculator"
    * "launch app notepad"
    * "open application terminal"
    """
    app_name = _extract_app_name(text)
    if not app_name:
        return "Please specify the application name, e.g. 'open app calculator'."

    # Check our known-apps map
    for key, platform_cmds in _APP_MAP.items():
        if key in app_name:
            cmd = platform_cmds.get(_PLATFORM)
            if cmd:
                return _run_command(cmd, key)
            break

    # Fall back to running the app name directly.
    # Validate against the safe-characters allowlist to prevent injection.
    if not _SAFE_APP_RE.match(app_name):
        logger.warning("Rejected unsafe app name: %r", app_name)
        return f"Application name '{app_name}' contains invalid characters."
    return _run_command(app_name, app_name)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_url(text: str) -> Optional[str]:
    """Pull a URL or domain name from *text*."""
    # Full URL
    m = re.search(r"https?://[^\s]+", text)
    if m:
        return m.group(0)
    # Domain-like word after keyword
    m = re.search(
        r"(?:open website|go to|visit|browse)\s+([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}[^\s]*)",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)
    # Last resort: any domain-looking word
    m = re.search(r"\b([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}[^\s]*)\b", text)
    if m:
        return m.group(1)
    return None


def _extract_app_name(text: str) -> Optional[str]:
    """Extract the application name from an open-app command."""
    m = re.search(
        r"(?:open app|launch app|start app|open application)\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    return m.group(1).strip().lower() if m else None


_SAFE_APP_RE = re.compile(r"^[a-zA-Z0-9_\-. ]+$")


def _run_command(cmd: str, label: str) -> str:
    """Run *cmd* as a subprocess and return a status message.

    Commands that come from ``_APP_MAP`` are fully trusted (hardcoded).
    Commands derived from user input are validated against a strict allowlist
    of safe characters before execution to prevent command injection.
    """
    # cmd values from _APP_MAP may contain spaces (e.g. "open -a Calculator"),
    # so we split them into a list and use shell=False.
    args_list = cmd.split()
    if not args_list:
        return f"No command configured for {label}."
    try:
        subprocess.Popen(args_list, shell=False)  # noqa: S603
        return f"Opening {label}…"
    except Exception as exc:
        logger.error("Failed to launch '%s': %s", label, exc)
        return f"Could not open {label}: {exc}"
