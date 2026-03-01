"""
Face memory feature using OpenCV.
Allows the assistant to learn named faces from the webcam and later recognise
them using the LBPH (Local Binary Pattern Histogram) face recogniser – fully
offline, no external API required.

Directory layout
----------------
data/faces/
    labels.json          – mapping of label_id → name
    trainer.yml          – trained LBPH model
    <name>/
        001.jpg
        002.jpg  …       – captured face images for training
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

from config import FACES_DIR, DATA_DIR

logger = logging.getLogger(__name__)

os.makedirs(FACES_DIR, exist_ok=True)

_LABELS_FILE = os.path.join(FACES_DIR, "labels.json")
_TRAINER_FILE = os.path.join(FACES_DIR, "trainer.yml")
_CASCADE_PATH: Optional[str] = None  # resolved lazily


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def learn_face(text: str) -> str:
    """Capture face images from the webcam and train the recogniser.

    Expects a name to be embedded in *text*, e.g. "learn face Alice".
    Captures 30 sample images, trains the LBPH model and saves it.
    """
    name = _extract_name(text, prefix_patterns=[
        r"(?:learn face|remember face|add face|save face)\s+(.+)$"
    ])
    if not name:
        return "Please provide a name, e.g. 'learn face Alice'."

    try:
        import cv2  # type: ignore
    except ImportError:
        return "opencv-python is required for face memory. Install it with: pip install opencv-python"

    cascade = _get_cascade(cv2)
    if cascade is None:
        return "Could not load face detection cascade. Ensure opencv-python is installed correctly."

    person_dir = os.path.join(FACES_DIR, name)
    os.makedirs(person_dir, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Could not access the webcam. Please check your camera connection."

    print(f"Capturing face images for '{name}'. Look at the camera…")
    count = 0
    try:
        while count < 30:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
            for (x, y, w, h) in faces:
                count += 1
                face_img = gray[y : y + h, x : x + w]
                img_path = os.path.join(person_dir, f"{count:03d}.jpg")
                cv2.imwrite(img_path, face_img)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(
                    frame,
                    f"{name} [{count}/30]",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2,
                )
            cv2.imshow("Learning face – press Q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if count == 0:
        return "No face detected. Please ensure your face is visible to the camera."

    # Retrain the model with all known faces
    _train_model(cv2)
    return f"Learned {count} face samples for '{name}'. Face memory updated."


def recognize_face() -> str:
    """Open the webcam and attempt to identify a face in real time.

    Displays a live window with the predicted name (or 'Unknown') overlaid.
    Press Q to quit.
    """
    try:
        import cv2  # type: ignore
    except ImportError:
        return "opencv-python is required. Install it with: pip install opencv-python"

    if not os.path.exists(_TRAINER_FILE):
        return "No face data found. Use 'learn face <name>' first."

    labels = _load_labels()
    if not labels:
        return "No labelled faces found. Use 'learn face <name>' to register faces."

    cascade = _get_cascade(cv2)
    if cascade is None:
        return "Could not load face detection cascade."

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(_TRAINER_FILE)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Could not access the webcam."

    print("Face recognition active – press Q to quit.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
            for (x, y, w, h) in faces:
                face_img = gray[y : y + h, x : x + w]
                label_id, confidence = recognizer.predict(face_img)
                name = labels.get(str(label_id), "Unknown")
                # confidence < 60 is a good match for LBPH
                display = name if confidence < 60 else "Unknown"
                color = (0, 255, 0) if confidence < 60 else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(
                    frame,
                    f"{display} ({confidence:.0f})",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )
            cv2.imshow("Face Recognition – press Q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return "Face recognition session ended."


def list_faces() -> str:
    """Return a list of all registered face names."""
    labels = _load_labels()
    if not labels:
        return "No faces registered yet. Use 'learn face <name>' to add one."
    names = sorted(set(labels.values()))
    return "Registered faces:\n" + "\n".join(f"  • {n}" for n in names)


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------

def _train_model(cv2) -> None:  # type: ignore[no-untyped-def]
    """Scan FACES_DIR, build training data and save the LBPH model."""
    import numpy as np  # type: ignore

    faces_data = []
    labels_data = []
    label_map: dict[str, int] = {}
    next_id = 0

    for person_name in sorted(os.listdir(FACES_DIR)):
        person_dir = os.path.join(FACES_DIR, person_name)
        if not os.path.isdir(person_dir):
            continue
        if person_name not in label_map:
            label_map[person_name] = next_id
            next_id += 1
        label_id = label_map[person_name]
        for img_file in sorted(os.listdir(person_dir)):
            img_path = os.path.join(person_dir, img_file)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            faces_data.append(img)
            labels_data.append(label_id)

    if not faces_data:
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces_data, np.array(labels_data))
    recognizer.save(_TRAINER_FILE)

    # Persist labels mapping (id → name)
    id_to_name = {str(v): k for k, v in label_map.items()}
    with open(_LABELS_FILE, "w", encoding="utf-8") as fh:
        json.dump(id_to_name, fh, indent=2)


def _load_labels() -> dict[str, str]:
    if not os.path.exists(_LABELS_FILE):
        return {}
    try:
        with open(_LABELS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def _get_cascade(cv2):  # type: ignore[no-untyped-def]
    global _CASCADE_PATH
    if _CASCADE_PATH is None:
        _CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(_CASCADE_PATH)
    if cascade.empty():
        return None
    return cascade


def _extract_name(text: str, prefix_patterns: list[str]) -> str:
    """Extract a person name from *text* using the given regex patterns."""
    for pattern in prefix_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""
