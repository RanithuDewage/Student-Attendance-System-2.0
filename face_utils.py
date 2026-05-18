from pathlib import Path
import re
import time
import json
import math
import shutil
import cv2
import numpy as np

from config import FACES_DIR, MODELS_DIR, FACE_MODEL_FILE, LABELS_FILE, ensure_dirs
from db import save_student, get_student

# Face image resolution used for training and recognition
FACE_SIZE = (200, 200)

# Basic quality thresholds
MIN_BLUR = 80.0
MIN_BRIGHTNESS = 50.0
MAX_BRIGHTNESS = 220.0

def sanitize_text(text: str) -> str:
    """
    Clean text so it can safely be used in folder/file names.
    """
    text = str(text).strip()
    text = re.sub(r'[\\/*?:"<>|]', "_", text)
    text = re.sub(r"\s+", " ", text)
    return text if text else "unknown"

def get_face_cascade():
    """Load OpenCV Haar cascade for face detection."""
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def get_eye_cascade():
    """Load OpenCV Haar cascade for eye detection."""
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

def face_quality(gray_face):
    """
    Check whether a face image is good enough for training.
    Returns:
        ok (bool), metrics (dict)
    """
    blur = float(cv2.Laplacian(gray_face, cv2.CV_64F).var())
    brightness = float(np.mean(gray_face))
    ok = blur >= MIN_BLUR and MIN_BRIGHTNESS <= brightness <= MAX_BRIGHTNESS
    return ok, {"blur": blur, "brightness": brightness}

def align_face(gray_face):
    """
    Try to align the face based on the eye positions.
    This is a simple alignment method, not a full landmark pipeline.
    """
    eye_cascade = get_eye_cascade()
    eyes = eye_cascade.detectMultiScale(gray_face, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))

    if len(eyes) < 2:
        return gray_face

    # Pick the two eyes with the smallest x values
    eyes = sorted(eyes, key=lambda e: e[0])[:2]
    (x1, y1, w1, h1), (x2, y2, w2, h2) = eyes

    p1 = (x1 + w1 / 2.0, y1 + h1 / 2.0)
    p2 = (x2 + w2 / 2.0, y2 + h2 / 2.0)

    if p1[0] == p2[0]:
        return gray_face

    angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
    if abs(angle) < 2:
        return gray_face

    h, w = gray_face.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(gray_face, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def extract_largest_face(gray):
    """Detect faces and return the largest face box."""
    face_cascade = get_face_cascade()
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(100, 100)
    )
    if len(faces) == 0:
        return None
    return max(faces, key=lambda r: r[2] * r[3])

def prepare_face(gray, box):
    """Crop, resize, and align one face region."""
    x, y, w, h = box
    roi = gray[y:y+h, x:x+w]
    roi = cv2.resize(roi, FACE_SIZE)
    roi = align_face(roi)
    return roi

def ensure_student_folder(student_id, name):
    """Create and return a folder for one student."""
    student_id = sanitize_text(student_id)
    name = sanitize_text(name)
    folder = FACES_DIR / f"{student_id}__{name}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def count_student_images(student_id, name):
    """Count all face images saved for one student."""
    folder = ensure_student_folder(student_id, name)
    return len(list(folder.glob("*.jpg"))) + len(list(folder.glob("*.png")))

def remove_student_faces(student_id):
    """
    Remove all face folders belonging to a student ID.
    Useful when deleting a student.
    """
    student_id = sanitize_text(student_id)
    removed = []
    if not FACES_DIR.exists():
        return removed

    for item in FACES_DIR.iterdir():
        if item.is_dir() and item.name.startswith(f"{student_id}__"):
            shutil.rmtree(item, ignore_errors=True)
            removed.append(str(item))
    return removed

def _preserve_student(student_id, name, photo_count=None):
    """
    Keep student row in DB updated after photo capture.
    This ensures student metadata does not get lost.
    """
    existing = get_student(student_id) or {}
    save_student(
        student_id=student_id,
        name=name or existing.get("name", ""),
        email=existing.get("email", ""),
        department=existing.get("department", ""),
        batch=existing.get("batch", ""),
        photo_path=existing.get("photo_path", ""),
        active=existing.get("active", 1),
        photo_count=photo_count if photo_count is not None else existing.get("photo_count", 0)
    )

def capture_faces(student_id: str, name: str, samples: int = 20, camera_index: int = 0):
    """
    Capture multiple face images from webcam.
    Each image is saved into the student's folder.
    """
    ensure_dirs()
    student_id = sanitize_text(student_id)
    name = sanitize_text(name)

    folder = ensure_student_folder(student_id, name)
    existing = count_student_images(student_id, name)
    target_total = existing + int(samples)
    saved = existing

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Camera open karanna ba")

    last_save = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        face_box = extract_largest_face(gray)

        if face_box is not None:
            x, y, w, h = face_box
            roi = prepare_face(gray, face_box)
            ok, q = face_quality(roi)

            # Show detection box with quality feedback
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0) if ok else (0, 0, 255), 2)
            cv2.putText(frame, f"blur:{q['blur']:.0f} bright:{q['brightness']:.0f}",
                        (x, max(25, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

            now = time.time()
            if ok and saved < target_total and (now - last_save) > 0.35:
                saved += 1
                img_path = folder / f"{student_id}_{name}_{saved:03d}.jpg"
                cv2.imwrite(str(img_path), roi)
                last_save = now

        cv2.putText(frame, f"{student_id} | {name}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"Captured: {saved - existing}/{samples}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(frame, "Press q to quit", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Capture Faces", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        if saved >= target_total:
            break

    cap.release()
    cv2.destroyAllWindows()

    photo_count = count_student_images(student_id, name)
    _preserve_student(student_id, name, photo_count=photo_count)

    return {"student_id": student_id, "name": name, "captured": saved - existing, "photo_count": photo_count}

def add_face_photo_from_file(student_id: str, name: str, image_path: str):
    """
    Add one face image from a file instead of webcam capture.
    """
    ensure_dirs()
    student_id = sanitize_text(student_id)
    name = sanitize_text(name)

    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError("Image is not loading. Check the file path and format.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    face_box = extract_largest_face(gray)
    if face_box is None:
        raise RuntimeError("Face is not detected. Please take a clear photo.")

    roi = prepare_face(gray, face_box)
    ok, q = face_quality(roi)
    if not ok:
        raise RuntimeError(f"Bad quality photo. blur={q['blur']:.0f}, brightness={q['brightness']:.0f}")

    folder = ensure_student_folder(student_id, name)
    idx = len(list(folder.glob("*.jpg"))) + 1
    save_path = folder / f"{student_id}_{name}_{idx:03d}.jpg"
    cv2.imwrite(str(save_path), roi)

    photo_count = count_student_images(student_id, name)
    _preserve_student(student_id, name, photo_count=photo_count)

    return str(save_path)

def train_face_model():
    """
    Train LBPH face recognizer using all student face images.
    """
    ensure_dirs()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    face_samples = []
    labels = []
    label_map = {}
    label_id = 0

    if not FACES_DIR.exists():
        raise RuntimeError("No faces folder found")

    # Load all student folders
    for person_dir in sorted(FACES_DIR.iterdir()):
        if not person_dir.is_dir() or "__" not in person_dir.name:
            continue

        student_id, name = person_dir.name.split("__", 1)
        images = list(person_dir.glob("*.jpg")) + list(person_dir.glob("*.png"))
        if not images:
            continue

        for img_path in images:
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            img = cv2.resize(img, FACE_SIZE)
            face_samples.append(img)
            labels.append(label_id)

        label_map[str(label_id)] = {"student_id": student_id, "name": name}
        label_id += 1

    if not face_samples:
        raise RuntimeError("Training failed: No face images found. Please capture faces for students first.")

    recognizer.train(face_samples, np.array(labels))
    recognizer.save(str(FACE_MODEL_FILE))

    with open(LABELS_FILE, "w", encoding="utf-8") as f:
        json.dump(label_map, f, indent=4, ensure_ascii=False)

    return {"students": len(label_map), "images": len(face_samples)}

def load_labels():
    """Load saved label map from labels.json."""
    if not LABELS_FILE.exists():
        return {}
    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)