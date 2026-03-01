"""
Speech module: Text-to-Speech (TTS) and Speech-to-Text (STT) for JARVIS.
TTS uses pyttsx3 (offline).
STT uses the SpeechRecognition library with Google Web Speech API.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_tts_engine():
    """Lazily import and initialise pyttsx3 to avoid import errors on headless systems."""
    try:
        import pyttsx3  # type: ignore
        from config import TTS_RATE, TTS_VOLUME

        engine = pyttsx3.init()
        engine.setProperty("rate", TTS_RATE)
        engine.setProperty("volume", TTS_VOLUME)
        return engine
    except Exception as exc:
        logger.warning("TTS engine unavailable: %s", exc)
        return None


def speak(text: str) -> None:
    """Convert *text* to speech and play it aloud.

    Falls back to a plain ``print`` when the TTS engine is unavailable
    (e.g. on a headless CI server).
    """
    print(f"JARVIS: {text}")
    engine = _get_tts_engine()
    if engine is None:
        return
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as exc:
        logger.warning("TTS playback failed: %s", exc)


def listen(timeout: Optional[int] = None, phrase_time_limit: Optional[int] = None) -> Optional[str]:
    """Listen for a voice command and return the recognised text.

    Returns ``None`` if nothing was heard or recognition failed.
    """
    try:
        import speech_recognition as sr  # type: ignore
        from config import STT_TIMEOUT, STT_PHRASE_LIMIT
    except ImportError as exc:
        logger.warning("SpeechRecognition not available: %s", exc)
        return None

    timeout = timeout or STT_TIMEOUT
    phrase_time_limit = phrase_time_limit or STT_PHRASE_LIMIT

    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8

    try:
        with sr.Microphone() as source:
            print("Listening…")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError:
        logger.debug("Listening timed out.")
        return None
    except Exception as exc:
        logger.warning("Microphone error: %s", exc)
        return None

    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text.lower().strip()
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that.")
        return None
    except sr.RequestError as exc:
        logger.warning("Speech recognition service error: %s", exc)
        speak("Speech recognition service is unavailable right now.")
        return None
