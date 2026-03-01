# JARVIS MVP (Python)

A local desktop assistant with:
- Text mode and optional voice mode
- Speech output (TTS)
- Website/app launcher
- WhatsApp and email draft automation
- Reminders and notes
- Conversation history log
- OpenCV face memory (learn + recognize)
- Optional AI answers via OpenAI API key

## 1) Setup

```bash
cd jarvis-assistant
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If `PyAudio` fails on Windows, install this first:
```bash
pip install pipwin
pipwin install pyaudio
```

If OpenCV install fails, try:
```bash
pip install --upgrade pip
pip install opencv-contrib-python numpy
```

## 2) Configure API (optional)

```bash
copy .env.example .env
```

Then add your key in `.env`:

```env
OPENAI_API_KEY=your_key_here
```

## 3) Run

```bash
python jarvis.py
```

Choose `text` mode first for quick testing.

## 4) Commands

- `help`
- `time`
- `date`
- `open youtube`
- `open app notepad`
- `search latest ai news`
- `note buy groceries`
- `show notes`
- `remind me in 10 minutes to drink water`
- `ask explain black holes simply`
- `history`
- `whatsapp to +911234567890 hello from jarvis`
- `email to abc@example.com subject project update body build completed`
- `learn face Tony`
- `recognize face`
- `who am i`
- `hotword on`
- `hotword off`
- `exit`

## Intelligence Mode (Natural Language)

You can now speak or type more natural requests. Jarvis will try to:
- detect intent (open/search/reminder/note/email/WhatsApp/face)
- use recent history + notes + reminders as memory context
- answer directly with AI when no fixed command matches

Examples:
- `open my coding playlist on youtube`
- `search best way to learn dsa in 2026`
- `remind me after 45 minutes to stretch`
- `note that i finished module 2 today`
- `send whatsapp to +911234567890 i will join in 10 minutes`
- `draft an email to abc@example.com about meeting delay`
- `what did i ask you earlier about reminders?`
- `summarize my pending tasks from memory`

Tip: If the request is ambiguous, Jarvis may ask one short follow-up question.

## Data Storage

Runtime data is stored in:
- `data/history.jsonl`
- `data/notes.txt`
- `data/reminders.json`
