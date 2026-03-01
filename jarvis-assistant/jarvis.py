import json
import os
import re
import subprocess
import threading
import time
import webbrowser
import importlib
from importlib.util import find_spec
import urllib.parse
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

pyttsx3 = importlib.import_module("pyttsx3") if find_spec("pyttsx3") else None
sr = importlib.import_module("speech_recognition") if find_spec("speech_recognition") else None
dotenv_module = importlib.import_module("dotenv") if find_spec("dotenv") else None
load_dotenv = getattr(dotenv_module, "load_dotenv", None) if dotenv_module else None
cv2 = importlib.import_module("cv2") if find_spec("cv2") else None
np = importlib.import_module("numpy") if find_spec("numpy") else None


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Reminder:
    text: str
    due_iso: str
    done: bool = False


class JarvisAssistant:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.faces_dir = self.data_dir / "faces"
        self.faces_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.data_dir / "history.jsonl"
        self.notes_file = self.data_dir / "notes.txt"
        self.reminders_file = self.data_dir / "reminders.json"
        self.face_model_file = self.faces_dir / "face_model.yml"
        self.face_labels_file = self.faces_dir / "labels.json"

        self.wake_word = "jarvis"
        self.running = True
        self.voice_enabled = sr is not None
        self.hotword_always_on = True
        self.mode = "text"

        if load_dotenv:
            load_dotenv(self.base_dir / ".env")

        self.tts_engine = self._init_tts()
        self.reminders = self._load_reminders()

        self.web_shortcuts = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "github": "https://github.com",
            "gmail": "https://mail.google.com",
            "chatgpt": "https://chat.openai.com",
        }

        self.app_shortcuts = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "cmd": ["cmd.exe"],
            "paint": ["mspaint.exe"],
            "vscode": ["code"],
        }

    def _create_face_recognizer(self):
        if cv2 is None:
            return None
        try:
            return cv2.face.LBPHFaceRecognizer_create()
        except Exception:
            return None

    def _get_face_cascade(self):
        if cv2 is None:
            return None
        try:
            return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        except Exception:
            return None

    def _load_face_labels(self) -> dict:
        if not self.face_labels_file.exists():
            return {}
        try:
            raw = json.loads(self.face_labels_file.read_text(encoding="utf-8"))
            return {int(key): value for key, value in raw.items()}
        except Exception:
            return {}

    def _save_face_labels(self, labels: dict) -> None:
        serializable = {str(key): value for key, value in labels.items()}
        self.face_labels_file.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

    def _next_face_label_id(self, labels: dict) -> int:
        if not labels:
            return 0
        return max(labels.keys()) + 1

    def _capture_face_samples(self, name: str, sample_count: int = 25):
        if cv2 is None or np is None:
            return False, "OpenCV/Numpy not available. Install requirements first."

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            return False, "Could not access camera."

        face_cascade = self._get_face_cascade()
        if face_cascade is None:
            camera.release()
            return False, "Could not load Haar cascade for face detection."

        self._speak(f"Capturing {sample_count} samples for {name}. Look at the camera.")
        samples = []

        while len(samples) < sample_count:
            ok, frame = camera.read()
            if not ok:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))

            for (x, y, w, h) in faces:
                face_region = gray[y:y + h, x:x + w]
                face_region = cv2.resize(face_region, (200, 200))
                samples.append(face_region)

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"Samples: {len(samples)}/{sample_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )

                if len(samples) >= sample_count:
                    break

            cv2.imshow("Jarvis Face Enrollment (press q to cancel)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        camera.release()
        cv2.destroyAllWindows()

        if len(samples) < max(8, sample_count // 3):
            return False, "Not enough face samples captured. Try again with better lighting."

        return True, samples

    def _learn_face(self, name: str) -> str:
        name = name.strip()
        if not name:
            return "Use: learn face <name>"

        recognizer = self._create_face_recognizer()
        if recognizer is None:
            return "LBPH recognizer unavailable. Install opencv-contrib-python."

        success, result = self._capture_face_samples(name=name, sample_count=25)
        if not success:
            return str(result)

        samples = result
        labels_map = self._load_face_labels()

        existing_id = None
        for key, value in labels_map.items():
            if value.lower() == name.lower():
                existing_id = key
                break

        person_id = existing_id if existing_id is not None else self._next_face_label_id(labels_map)
        labels_map[person_id] = name

        train_images = []
        train_labels = []

        if self.face_model_file.exists():
            try:
                recognizer.read(str(self.face_model_file))
            except Exception:
                pass

        for face_image in samples:
            train_images.append(face_image)
            train_labels.append(person_id)

        try:
            recognizer.update(train_images, np.array(train_labels))
        except Exception:
            recognizer.train(train_images, np.array(train_labels))

        recognizer.write(str(self.face_model_file))
        self._save_face_labels(labels_map)
        return f"Face learned for {name}."

    def _recognize_face(self) -> str:
        if cv2 is None:
            return "OpenCV not available. Install requirements first."
        recognizer = self._create_face_recognizer()
        if recognizer is None:
            return "LBPH recognizer unavailable. Install opencv-contrib-python."
        if not self.face_model_file.exists():
            return "No known faces yet. Use: learn face <name>"

        labels_map = self._load_face_labels()
        if not labels_map:
            return "Face labels are missing. Re-learn at least one face."

        try:
            recognizer.read(str(self.face_model_file))
        except Exception:
            return "Could not load trained face model."

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            return "Could not access camera."

        face_cascade = self._get_face_cascade()
        if face_cascade is None:
            camera.release()
            return "Could not load Haar cascade for face detection."

        self._speak("Scanning face. Please look at the camera.")
        detected_name = None
        best_confidence = 9999.0
        start_time = time.time()

        while time.time() - start_time < 10:
            ok, frame = camera.read()
            if not ok:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))

            for (x, y, w, h) in faces:
                face_region = gray[y:y + h, x:x + w]
                face_region = cv2.resize(face_region, (200, 200))

                predicted_id, confidence = recognizer.predict(face_region)
                label = labels_map.get(predicted_id, "Unknown")

                display_name = label if confidence < 70 else "Unknown"
                if confidence < best_confidence:
                    best_confidence = confidence
                    detected_name = display_name

                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 100, 0), 2)
                cv2.putText(
                    frame,
                    f"{display_name} ({confidence:.1f})",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 100, 0),
                    2,
                )

            cv2.imshow("Jarvis Face Recognition (press q to stop)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            if detected_name and detected_name != "Unknown" and best_confidence < 70:
                break

        camera.release()
        cv2.destroyAllWindows()

        if detected_name and detected_name != "Unknown" and best_confidence < 70:
            return f"I recognize you as {detected_name}."
        return "I could not confidently recognize this face."

    def _send_whatsapp(self, command: str) -> str:
        pattern = r"^whatsapp to ([+\d]{8,20})\s+(.+)$"
        match = re.match(pattern, command, flags=re.IGNORECASE)
        if not match:
            return "Use: whatsapp to +911234567890 hello from jarvis"

        phone = match.group(1)
        message = match.group(2).strip()
        encoded = urllib.parse.quote(message)
        url = f"https://wa.me/{phone}?text={encoded}"
        webbrowser.open(url)
        return f"Opening WhatsApp chat for {phone}."

    def _send_email(self, command: str) -> str:
        pattern = r"^email to ([^\s]+@[^\s]+) subject (.+?) body (.+)$"
        match = re.match(pattern, command, flags=re.IGNORECASE)
        if not match:
            return "Use: email to abc@example.com subject hello body this is jarvis"

        recipient = match.group(1).strip()
        subject = urllib.parse.quote(match.group(2).strip())
        body = urllib.parse.quote(match.group(3).strip())
        url = f"mailto:{recipient}?subject={subject}&body={body}"
        webbrowser.open(url)
        return f"Opening email draft to {recipient}."

    def _init_tts(self):
        if pyttsx3 is None:
            return None
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 180)
            return engine
        except Exception:
            return None

    def _speak(self, text: str) -> None:
        print(f"JARVIS: {text}")
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                pass

    def _listen_once(self, timeout: int = 6, phrase_time_limit: int = 8) -> Optional[str]:
        if sr is None:
            return None

        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("Listening...")
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = recognizer.recognize_google(audio)
                return text.strip().lower()
        except Exception:
            return None

    def _append_history(self, source: str, user_text: str, reply: str) -> None:
        record = {
            "timestamp": now_str(),
            "source": source,
            "user": user_text,
            "jarvis": reply,
        }
        with self.history_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_recent_history(self, limit: int = 8) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            lines = self.history_file.read_text(encoding="utf-8").splitlines()
            records = []
            for line in lines[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
            return records
        except Exception:
            return []

    def _load_latest_notes(self, limit: int = 5) -> List[str]:
        if not self.notes_file.exists():
            return []
        try:
            lines = [line for line in self.notes_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            return lines[-limit:]
        except Exception:
            return []

    def _pending_reminders_snapshot(self, limit: int = 5) -> List[str]:
        upcoming = []
        current = datetime.now()
        for reminder in self.reminders:
            if reminder.done:
                continue
            try:
                due_time = datetime.fromisoformat(reminder.due_iso)
            except Exception:
                continue
            if due_time >= current:
                upcoming.append((due_time, reminder.text))

        upcoming.sort(key=lambda item: item[0])
        return [f"{due.strftime('%Y-%m-%d %I:%M %p')} - {text}" for due, text in upcoming[:limit]]

    def _build_memory_context(self) -> str:
        history = self._load_recent_history(limit=8)
        notes = self._load_latest_notes(limit=5)
        reminders = self._pending_reminders_snapshot(limit=5)

        history_lines = []
        for item in history:
            user_text = item.get("user", "")
            jarvis_text = item.get("jarvis", "")
            timestamp = item.get("timestamp", "")
            history_lines.append(f"- [{timestamp}] User: {user_text} | Jarvis: {jarvis_text}")

        history_text = "\n".join(history_lines) if history_lines else "- none"
        notes_text = "\n".join(f"- {line}" for line in notes) if notes else "- none"
        reminders_text = "\n".join(f"- {line}" for line in reminders) if reminders else "- none"

        return (
            "Recent conversation:\n"
            f"{history_text}\n\n"
            "Latest notes:\n"
            f"{notes_text}\n\n"
            "Pending reminders:\n"
            f"{reminders_text}"
        )

    def _save_reminders(self) -> None:
        with self.reminders_file.open("w", encoding="utf-8") as file:
            json.dump([asdict(item) for item in self.reminders], file, indent=2)

    def _load_reminders(self) -> List[Reminder]:
        if not self.reminders_file.exists():
            return []
        try:
            data = json.loads(self.reminders_file.read_text(encoding="utf-8"))
            return [Reminder(**item) for item in data]
        except Exception:
            return []

    def _check_reminders_loop(self) -> None:
        while self.running:
            updated = False
            current = datetime.now()
            for reminder in self.reminders:
                if reminder.done:
                    continue
                due_time = datetime.fromisoformat(reminder.due_iso)
                if current >= due_time:
                    reminder.done = True
                    self._speak(f"Reminder: {reminder.text}")
                    updated = True
            if updated:
                self._save_reminders()
            time.sleep(2)

    def _set_reminder(self, command: str) -> str:
        pattern = r"remind me in (\d+) (second|seconds|minute|minutes|hour|hours) to (.+)"
        match = re.search(pattern, command)
        if not match:
            return "Use: remind me in 10 minutes to drink water"

        amount = int(match.group(1))
        unit = match.group(2)
        text = match.group(3).strip()

        if "second" in unit:
            delta = timedelta(seconds=amount)
        elif "minute" in unit:
            delta = timedelta(minutes=amount)
        else:
            delta = timedelta(hours=amount)

        due = datetime.now() + delta
        self.reminders.append(Reminder(text=text, due_iso=due.isoformat(), done=False))
        self._save_reminders()
        return f"Reminder set for {due.strftime('%I:%M %p')}: {text}"

    def _add_note(self, text: str) -> str:
        if not text:
            return "Say or type: note buy milk"
        with self.notes_file.open("a", encoding="utf-8") as file:
            file.write(f"[{now_str()}] {text}\n")
        return "Note saved."

    def _show_notes(self) -> str:
        if not self.notes_file.exists():
            return "No notes yet."
        lines = self.notes_file.read_text(encoding="utf-8").strip().splitlines()
        if not lines or lines == [""]:
            return "No notes yet."
        return "Your latest notes:\n" + "\n".join(lines[-5:])

    def _open_website(self, target: str) -> str:
        target = target.strip().lower()
        if target in self.web_shortcuts:
            url = self.web_shortcuts[target]
        elif target.startswith("http://") or target.startswith("https://"):
            url = target
        else:
            url = f"https://www.google.com/search?q={target.replace(' ', '+')}"
        webbrowser.open(url)
        return f"Opening {target}."

    def _open_app(self, app_name: str) -> str:
        app_name = app_name.strip().lower()
        if app_name not in self.app_shortcuts:
            return f"I don't have a shortcut for {app_name} yet."
        try:
            subprocess.Popen(self.app_shortcuts[app_name])
            return f"Opening {app_name}."
        except Exception as error:
            return f"Could not open {app_name}: {error}"

    def _ai_answer(self, prompt: str, use_memory: bool = True) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "No API key found. Add OPENAI_API_KEY in .env, or use 'search <topic>' for browser search."

        try:
            openai_module = importlib.import_module("openai")
            OpenAI = getattr(openai_module, "OpenAI")
            client = OpenAI(api_key=api_key)

            system_prompt = (
                "You are Jarvis, a concise and helpful desktop AI assistant. "
                "Use provided memory context to personalize responses. "
                "If a request is ambiguous, ask one short clarifying question."
            )
            memory_context = self._build_memory_context() if use_memory else ""
            composed_input = (
                f"System behavior:\n{system_prompt}\n\n"
                f"Memory context:\n{memory_context}\n\n"
                f"User request:\n{prompt}"
            )

            response = client.responses.create(
                model="gpt-4.1-mini",
                input=composed_input,
            )
            text = response.output_text.strip()
            return text if text else "I couldn't generate a response right now."
        except Exception as error:
            return f"AI request failed: {error}"

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except Exception:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start:end + 1])
        except Exception:
            return None

    def _ai_route_command(self, raw_command: str) -> Optional[str]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            openai_module = importlib.import_module("openai")
            OpenAI = getattr(openai_module, "OpenAI")
            client = OpenAI(api_key=api_key)
        except Exception:
            return None

        memory_context = self._build_memory_context()
        routing_prompt = (
            "Route the user command into one intent and arguments. "
            "Return ONLY valid JSON, no markdown, no extra text.\n\n"
            "Allowed intents:\n"
            "- open_website: {\"target\": string}\n"
            "- open_app: {\"app_name\": string}\n"
            "- search_web: {\"query\": string}\n"
            "- add_note: {\"text\": string}\n"
            "- show_notes: {}\n"
            "- set_reminder: {\"amount\": number, \"unit\": \"seconds|minutes|hours\", \"task\": string}\n"
            "- send_whatsapp: {\"phone\": string, \"message\": string}\n"
            "- send_email: {\"recipient\": string, \"subject\": string, \"body\": string}\n"
            "- face_learn: {\"name\": string}\n"
            "- face_recognize: {}\n"
            "- ai_answer: {\"prompt\": string}\n"
            "- unknown: {}\n\n"
            "JSON schema:\n"
            "{\"intent\": string, \"args\": object}\n\n"
            f"Memory context:\n{memory_context}\n\n"
            f"User command: {raw_command}"
        )

        try:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=routing_prompt,
            )
            payload = self._extract_json_object(response.output_text)
            if not payload or not isinstance(payload, dict):
                return None

            intent = str(payload.get("intent", "")).strip().lower()
            args = payload.get("args", {})
            if not isinstance(args, dict):
                args = {}

            if intent == "open_website":
                target = str(args.get("target", "")).strip()
                if target:
                    return self._open_website(target)

            if intent == "open_app":
                app_name = str(args.get("app_name", "")).strip()
                if app_name:
                    return self._open_app(app_name)

            if intent == "search_web":
                query = str(args.get("query", "")).strip()
                if query:
                    webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
                    return f"Searching for {query}."

            if intent == "add_note":
                note_text = str(args.get("text", "")).strip()
                if note_text:
                    return self._add_note(note_text)

            if intent == "show_notes":
                return self._show_notes()

            if intent == "set_reminder":
                amount = args.get("amount", 0)
                unit = str(args.get("unit", "")).strip().lower()
                task = str(args.get("task", "")).strip()
                try:
                    amount = int(amount)
                except Exception:
                    amount = 0
                if amount > 0 and unit in {"seconds", "minutes", "hours"} and task:
                    return self._set_reminder(f"remind me in {amount} {unit} to {task}")

            if intent == "send_whatsapp":
                phone = str(args.get("phone", "")).strip()
                message = str(args.get("message", "")).strip()
                if phone and message:
                    return self._send_whatsapp(f"whatsapp to {phone} {message}")

            if intent == "send_email":
                recipient = str(args.get("recipient", "")).strip()
                subject = str(args.get("subject", "")).strip()
                body = str(args.get("body", "")).strip()
                if recipient and subject and body:
                    return self._send_email(f"email to {recipient} subject {subject} body {body}")

            if intent == "face_learn":
                name = str(args.get("name", "")).strip()
                if name:
                    return self._learn_face(name)

            if intent == "face_recognize":
                return self._recognize_face()

            if intent == "ai_answer":
                prompt = str(args.get("prompt", "")).strip() or raw_command
                return self._ai_answer(prompt, use_memory=True)

            return None
        except Exception:
            return None

    def handle_command(self, command: str, source: str = "text") -> str:
        raw_command = command.strip()
        command = raw_command.lower()
        if not raw_command:
            return ""

        if command in {"exit", "quit", "bye", "stop"}:
            self.running = False
            return "Goodbye, boss."

        if command in {"help", "commands"}:
            return (
                "Commands: time, date, open <site>, open app <name>, search <topic>, "
                "remind me in 10 minutes to <task>, note <text>, show notes, "
                "ask <question>, history, whatsapp to <phone> <msg>, "
                "email to <mail> subject <s> body <b>, learn face <name>, recognize face, "
                "hotword on/off, switch to voice mode, switch to text mode"
            )

        if command in {"switch to voice", "switch to voice mode", "voice mode", "mode voice"}:
            if sr is None:
                return "Voice mode is unavailable. Install SpeechRecognition and PyAudio first."
            self.mode = "voice"
            return "Switching to voice mode."

        if command in {"switch to text", "switch to text mode", "text mode", "mode text"}:
            self.mode = "text"
            return "Switching to text mode."

        if command == "time":
            return f"Current time is {datetime.now().strftime('%I:%M %p')}"

        if command == "date":
            return f"Today's date is {datetime.now().strftime('%A, %d %B %Y')}"

        if command.startswith("open app "):
            return self._open_app(command.replace("open app ", "", 1))

        if command.startswith("open "):
            return self._open_website(command.replace("open ", "", 1))

        if command.startswith("search "):
            query = command.replace("search ", "", 1)
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            return f"Searching for {query}."

        if command.startswith("note "):
            return self._add_note(raw_command[5:].strip())

        if command == "show notes":
            return self._show_notes()

        if command.startswith("remind me in "):
            return self._set_reminder(command)

        if command == "history":
            return f"History file: {self.history_file}"

        if command.startswith("whatsapp to "):
            return self._send_whatsapp(raw_command)

        if command.startswith("email to "):
            return self._send_email(raw_command)

        if command == "hotword on":
            self.hotword_always_on = True
            return "Always-on hotword mode enabled."

        if command == "hotword off":
            self.hotword_always_on = False
            return "Always-on hotword mode disabled."

        if command.startswith("learn face "):
            return self._learn_face(raw_command[11:].strip())

        if command in {"recognize face", "who am i"}:
            return self._recognize_face()

        if command.startswith("ask "):
            prompt = raw_command[4:].strip()
            return self._ai_answer(prompt, use_memory=True)
        routed_reply = self._ai_route_command(raw_command)
        if routed_reply:
            return routed_reply

        ai_fallback = self._ai_answer(raw_command, use_memory=True)
        if ai_fallback.startswith("No API key found"):
            return "I didn't understand that. Type 'help' to view commands."
        return ai_fallback

    def run_text_mode(self) -> None:
        self._speak("JARVIS online. Type help to see commands.")
        while self.running and self.mode == "text":
            user_text = input("You: ").strip()
            reply = self.handle_command(user_text, source="text")
            if reply:
                self._append_history("text", user_text, reply)
                self._speak(reply)

    def run_voice_mode(self) -> None:
        if sr is None:
            self._speak("Speech recognition package not found. Falling back to text mode.")
            self.mode = "text"
            self.run_text_mode()
            return

        self._speak("Voice mode online. Say Jarvis followed by your command.")
        while self.running and self.mode == "voice":
            heard = self._listen_once()
            if not heard:
                continue
            print(f"Heard: {heard}")

            if self.hotword_always_on:
                if self.wake_word not in heard:
                    print("Wake word not detected. Say 'jarvis' first.")
                    continue
                command = heard.split(self.wake_word, 1)[1].strip()
                if not command:
                    self._speak("Yes, boss?")
                    follow_up = self._listen_once(timeout=5, phrase_time_limit=8)
                    if not follow_up:
                        self._speak("I didn't catch that.")
                        continue
                    print(f"Follow-up heard: {follow_up}")
                    command = follow_up.strip()
            else:
                command = heard.strip()

            reply = self.handle_command(command, source="voice")
            self._append_history("voice", command, reply)
            self._speak(reply)

    def run(self) -> None:
        reminder_thread = threading.Thread(target=self._check_reminders_loop, daemon=True)
        reminder_thread.start()

        chosen_mode = input("Choose mode (voice/text): ").strip().lower()
        self.mode = "voice" if chosen_mode == "voice" else "text"

        while self.running:
            if self.mode == "voice":
                self.run_voice_mode()
            else:
                self.run_text_mode()


def main() -> None:
    assistant = JarvisAssistant()
    assistant.run()


if __name__ == "__main__":
    main()
