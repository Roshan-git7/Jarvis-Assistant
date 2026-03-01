"""
Main JARVIS Assistant class.
Orchestrates voice/text input, command handling, history logging and speech output.
"""

from __future__ import annotations

import logging
from typing import Optional

from config import ASSISTANT_NAME
from core import speech, history, commands

logger = logging.getLogger(__name__)


class Assistant:
    """The JARVIS personal assistant."""

    def __init__(self, voice_mode: bool = False) -> None:
        """Initialise the assistant.

        Args:
            voice_mode: When ``True`` JARVIS listens for voice input in
                        addition to responding with synthesised speech.
                        When ``False`` it operates purely via text (stdin/stdout).
        """
        self.voice_mode = voice_mode
        self.running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def greet(self) -> None:
        """Speak / print a welcome message."""
        msg = (
            f"Hello! I am {ASSISTANT_NAME}, your personal desktop assistant. "
            "Type 'help' to see what I can do, or 'bye' to exit."
        )
        self._respond(msg)

    def process(self, user_input: str) -> Optional[str]:
        """Process a single *user_input* string and return the response.

        Side-effects: adds entries to conversation history and speaks the
        response if voice mode is active.

        Returns:
            The response string, or ``None`` if the assistant should shut down.
        """
        user_input = user_input.strip()
        if not user_input:
            return ""

        history.add_entry("user", user_input)
        response = commands.handle(user_input)

        if response == "FAREWELL":
            farewell = f"Goodbye! Have a great day. {ASSISTANT_NAME} signing off."
            history.add_entry("assistant", farewell)
            self._respond(farewell)
            return None  # Signal to stop the loop

        history.add_entry("assistant", response)
        self._respond(response)
        return response

    def run(self) -> None:
        """Start the main interaction loop (blocking)."""
        self.running = True
        self.greet()

        while self.running:
            try:
                user_input = self._get_input()
                if user_input is None:
                    continue
                result = self.process(user_input)
                if result is None:
                    self.running = False
            except KeyboardInterrupt:
                self._respond(f"{ASSISTANT_NAME} interrupted. Goodbye!")
                self.running = False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_input(self) -> Optional[str]:
        """Obtain input from the user (voice or text)."""
        if self.voice_mode:
            text = speech.listen()
            return text
        try:
            return input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

    def _respond(self, message: str) -> None:
        """Output a response (speech + print)."""
        if self.voice_mode:
            speech.speak(message)
        else:
            print(f"{ASSISTANT_NAME}: {message}")
