"""
Tests for the JARVIS Assistant.
These tests avoid any external network calls, hardware (mic/camera), or TTS.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_data_dir(tmp_dir: str):
    """Return a context-manager stack that redirects data files to *tmp_dir*."""
    import config

    return patch.multiple(
        config,
        DATA_DIR=tmp_dir,
        NOTES_FILE=os.path.join(tmp_dir, "notes.json"),
        REMINDERS_FILE=os.path.join(tmp_dir, "reminders.json"),
        HISTORY_FILE=os.path.join(tmp_dir, "history.json"),
        FACES_DIR=os.path.join(tmp_dir, "faces"),
    )


# ---------------------------------------------------------------------------
# Notes tests
# ---------------------------------------------------------------------------

class TestNotes(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._patches = _patch_data_dir(self.tmp)
        self._patches.start()
        import importlib
        import features.notes as notes_mod
        importlib.reload(notes_mod)
        self.notes = notes_mod

    def tearDown(self):
        self._patches.stop()

    def _notes_file(self):
        return os.path.join(self.tmp, "notes.json")

    def test_add_note(self):
        result = self.notes.add_note("take a note: buy milk")
        self.assertIn("buy milk", result)
        with open(self._notes_file()) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertIn("buy milk", data[0]["content"])

    def test_list_notes_empty(self):
        result = self.notes.list_notes()
        self.assertIn("no saved notes", result.lower())

    def test_list_notes(self):
        self.notes.add_note("take a note: item one")
        self.notes.add_note("take a note: item two")
        result = self.notes.list_notes()
        self.assertIn("item one", result)
        self.assertIn("item two", result)

    def test_delete_note(self):
        self.notes.add_note("take a note: to be deleted")
        result = self.notes.delete_note("delete note 1")
        self.assertIn("deleted", result.lower())
        self.assertEqual(self.notes.list_notes().lower().find("to be deleted"), -1)

    def test_search_notes(self):
        self.notes.add_note("take a note: remember the milk")
        self.notes.add_note("take a note: call the dentist")
        result = self.notes.search_notes("search notes milk")
        self.assertIn("milk", result)
        self.assertNotIn("dentist", result)

    def test_add_note_multiple_patterns(self):
        for cmd, expected in [
            ("add note pick up kids", "pick up kids"),
            ("note that the meeting is at 3pm", "the meeting is at 3pm"),
            ("write down dentist appointment friday", "dentist appointment friday"),
            ("make a note: car service due", "car service due"),
        ]:
            with self.subTest(cmd=cmd):
                result = self.notes.add_note(cmd)
                self.assertIn(expected, result)


# ---------------------------------------------------------------------------
# Reminders tests
# ---------------------------------------------------------------------------

class TestReminders(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._patches = _patch_data_dir(self.tmp)
        self._patches.start()
        import importlib
        import features.reminders as rem_mod
        importlib.reload(rem_mod)
        self.rem = rem_mod

    def tearDown(self):
        self._patches.stop()

    def test_add_reminder(self):
        result = self.rem.add_reminder("remind me to call John at 5pm")
        self.assertIn("call John", result)
        self.assertIn("5pm", result)

    def test_add_reminder_no_time(self):
        result = self.rem.add_reminder("remind me to buy groceries")
        self.assertIn("buy groceries", result)

    def test_list_reminders_empty(self):
        result = self.rem.list_reminders()
        self.assertIn("no pending reminders", result.lower())

    def test_list_reminders(self):
        self.rem.add_reminder("remind me to exercise at 7am")
        result = self.rem.list_reminders()
        self.assertIn("exercise", result)

    def test_delete_reminder(self):
        self.rem.add_reminder("remind me to water the plants")
        result = self.rem.delete_reminder("delete reminder 1")
        self.assertIn("deleted", result.lower())
        self.assertIn("no pending", self.rem.list_reminders().lower())


# ---------------------------------------------------------------------------
# History tests
# ---------------------------------------------------------------------------

class TestHistory(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._patches = _patch_data_dir(self.tmp)
        self._patches.start()
        import importlib
        import core.history as hist_mod
        importlib.reload(hist_mod)
        self.hist = hist_mod

    def tearDown(self):
        self._patches.stop()

    def test_add_and_get(self):
        self.hist.add_entry("user", "hello jarvis")
        self.hist.add_entry("assistant", "Hello!")
        entries = self.hist.get_history()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["role"], "user")
        self.assertEqual(entries[1]["role"], "assistant")

    def test_clear_history(self):
        self.hist.add_entry("user", "test")
        self.hist.clear_history()
        self.assertEqual(self.hist.get_history(), [])

    def test_limit(self):
        for i in range(10):
            self.hist.add_entry("user", f"msg {i}")
        entries = self.hist.get_history(limit=5)
        self.assertEqual(len(entries), 5)
        self.assertEqual(entries[-1]["message"], "msg 9")


# ---------------------------------------------------------------------------
# Command intent detection tests
# ---------------------------------------------------------------------------

class TestCommandIntents(unittest.TestCase):

    def setUp(self):
        import importlib
        import core.commands as cmd_mod
        importlib.reload(cmd_mod)
        self.cmd = cmd_mod

    def test_detect_greeting(self):
        self.assertEqual(self.cmd.detect_intent("hello"), "greeting")

    def test_detect_farewell(self):
        self.assertEqual(self.cmd.detect_intent("bye"), "farewell")

    def test_detect_note_add(self):
        self.assertEqual(self.cmd.detect_intent("take a note buy milk"), "note_add")

    def test_detect_reminder_add(self):
        self.assertEqual(self.cmd.detect_intent("remind me to call bob"), "reminder_add")

    def test_detect_open_website(self):
        self.assertEqual(self.cmd.detect_intent("open website youtube.com"), "open_website")

    def test_detect_open_app(self):
        self.assertEqual(self.cmd.detect_intent("open app calculator"), "open_app")

    def test_detect_whatsapp(self):
        self.assertEqual(self.cmd.detect_intent("send whatsapp to +123"), "whatsapp_send")

    def test_detect_email(self):
        self.assertEqual(self.cmd.detect_intent("draft email to alice@example.com"), "email_draft")

    def test_detect_face_learn(self):
        self.assertEqual(self.cmd.detect_intent("learn face Alice"), "face_learn")

    def test_detect_face_recognize(self):
        self.assertEqual(self.cmd.detect_intent("recognize face"), "face_recognize")

    def test_fallback_to_openai(self):
        self.assertEqual(self.cmd.detect_intent("what is the capital of france"), "openai_query")

    def test_help(self):
        self.assertEqual(self.cmd.detect_intent("help"), "help")


# ---------------------------------------------------------------------------
# WhatsApp parsing tests
# ---------------------------------------------------------------------------

class TestWhatsAppParsing(unittest.TestCase):

    def setUp(self):
        import importlib
        import features.whatsapp as wa_mod
        importlib.reload(wa_mod)
        self.wa = wa_mod

    def test_parse_full(self):
        phone, msg = self.wa._parse_whatsapp(
            "send whatsapp to +1234567890 saying Hello there"
        )
        self.assertEqual(phone, "+1234567890")
        self.assertEqual(msg, "Hello there")

    def test_parse_message_keyword(self):
        phone, msg = self.wa._parse_whatsapp(
            "whatsapp +9876543210 message Good morning"
        )
        self.assertEqual(phone, "+9876543210")
        self.assertEqual(msg, "Good morning")

    def test_parse_no_message(self):
        phone, msg = self.wa._parse_whatsapp("whatsapp +1234567890")
        self.assertEqual(phone, "+1234567890")
        self.assertIsNone(msg)

    def test_parse_no_phone(self):
        phone, msg = self.wa._parse_whatsapp("send whatsapp hello")
        self.assertIsNone(phone)


# ---------------------------------------------------------------------------
# Email parsing tests
# ---------------------------------------------------------------------------

class TestEmailDraft(unittest.TestCase):

    def setUp(self):
        import importlib
        import features.email_draft as em_mod
        importlib.reload(em_mod)
        self.em = em_mod

    def test_parse_full(self):
        to, sub, body = self.em._parse_email(
            "draft email to alice@example.com subject Meeting body See you at 3pm"
        )
        self.assertEqual(to, "alice@example.com")
        self.assertEqual(sub, "Meeting")
        self.assertEqual(body, "See you at 3pm")

    def test_parse_no_subject(self):
        to, sub, body = self.em._parse_email(
            "email bob@example.com how are you?"
        )
        self.assertEqual(to, "bob@example.com")
        self.assertIn("how are you", body)

    def test_parse_no_recipient(self):
        to, sub, body = self.em._parse_email("draft email subject Hello")
        self.assertIsNone(to)

    def test_build_mailto(self):
        mailto = self.em._build_mailto(
            "alice@example.com", "Hello", "Hi there"
        )
        self.assertTrue(mailto.startswith("mailto:alice@example.com"))
        self.assertIn("subject", mailto)
        self.assertIn("body", mailto)

    def test_mailto_no_params(self):
        mailto = self.em._build_mailto("alice@example.com", "", "")
        self.assertEqual(mailto, "mailto:alice@example.com")


# ---------------------------------------------------------------------------
# Web launcher tests
# ---------------------------------------------------------------------------

class TestWebLauncher(unittest.TestCase):

    def setUp(self):
        import importlib
        import features.web_launcher as wl_mod
        importlib.reload(wl_mod)
        self.wl = wl_mod

    def test_extract_url_full(self):
        url = self.wl._extract_url("open website https://github.com/user/repo")
        self.assertEqual(url, "https://github.com/user/repo")

    def test_extract_url_domain(self):
        url = self.wl._extract_url("go to youtube.com")
        self.assertIn("youtube.com", url)

    def test_extract_url_none(self):
        url = self.wl._extract_url("hello world nothing here")
        self.assertIsNone(url)

    def test_extract_app_name(self):
        name = self.wl._extract_app_name("open app calculator")
        self.assertEqual(name, "calculator")

    def test_extract_app_name_none(self):
        name = self.wl._extract_app_name("open website google.com")
        self.assertIsNone(name)

    @patch("features.web_launcher.webbrowser.open")
    def test_open_website(self, mock_open):
        result = self.wl.open_website("open website github.com")
        mock_open.assert_called_once()
        self.assertIn("github.com", result)

    @patch("features.web_launcher.webbrowser.open")
    def test_open_website_adds_https(self, mock_open):
        self.wl.open_website("go to example.com")
        call_url = mock_open.call_args[0][0]
        self.assertTrue(call_url.startswith("https://"))


# ---------------------------------------------------------------------------
# Assistant integration tests
# ---------------------------------------------------------------------------

class TestAssistantProcess(unittest.TestCase):
    """Integration tests for the Assistant.process() method."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._patches = _patch_data_dir(self.tmp)
        self._patches.start()
        import importlib
        import features.notes
        import features.reminders
        import core.history
        import core.commands
        for mod in (features.notes, features.reminders, core.history, core.commands):
            importlib.reload(mod)

        from core.assistant import Assistant
        self.assistant = Assistant(voice_mode=False)

    def tearDown(self):
        self._patches.stop()

    def test_greeting_response(self):
        response = self.assistant.process("hello")
        self.assertIsNotNone(response)
        self.assertIn("JARVIS", response)

    def test_help_response(self):
        response = self.assistant.process("help")
        self.assertIn("Reminders", response)

    def test_farewell_returns_none(self):
        response = self.assistant.process("bye")
        self.assertIsNone(response)

    def test_add_and_list_note(self):
        self.assistant.process("take a note: test integration note")
        response = self.assistant.process("list notes")
        self.assertIn("test integration note", response)

    def test_add_and_list_reminder(self):
        self.assistant.process("remind me to test the system at noon")
        response = self.assistant.process("list reminders")
        self.assertIn("test the system", response)

    def test_history_is_saved(self):
        self.assistant.process("hello")
        from core.history import get_history
        entries = get_history()
        self.assertGreater(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
