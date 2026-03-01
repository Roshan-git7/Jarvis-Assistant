"""
Configuration for JARVIS Assistant.
Settings can be overridden via environment variables or a .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Speech
TTS_RATE: int = int(os.getenv("TTS_RATE", "175"))
TTS_VOLUME: float = float(os.getenv("TTS_VOLUME", "1.0"))
STT_TIMEOUT: int = int(os.getenv("STT_TIMEOUT", "5"))
STT_PHRASE_LIMIT: int = int(os.getenv("STT_PHRASE_LIMIT", "10"))

# Data storage paths
DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")
NOTES_FILE: str = os.path.join(DATA_DIR, "notes.json")
REMINDERS_FILE: str = os.path.join(DATA_DIR, "reminders.json")
HISTORY_FILE: str = os.path.join(DATA_DIR, "history.json")
FACES_DIR: str = os.path.join(DATA_DIR, "faces")

# Assistant behaviour
ASSISTANT_NAME: str = os.getenv("ASSISTANT_NAME", "Jarvis")
WAKE_WORD: str = os.getenv("WAKE_WORD", "jarvis")
MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "100"))
