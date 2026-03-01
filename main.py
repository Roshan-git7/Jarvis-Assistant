"""
JARVIS Desktop Voice Assistant – main entry point.

Usage
-----
Text mode (default):
    python main.py

Voice mode:
    python main.py --voice

Run a single command directly:
    python main.py --command "list notes"
"""

from __future__ import annotations

import argparse
import logging
import sys

# Configure logging before importing project modules
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="JARVIS – Python desktop voice assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice input (microphone) and speech output.",
    )
    parser.add_argument(
        "--command",
        metavar="CMD",
        default=None,
        help="Process a single command and exit.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    from core.assistant import Assistant

    assistant = Assistant(voice_mode=args.voice)

    if args.command:
        response = assistant.process(args.command)
        return 0

    assistant.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
