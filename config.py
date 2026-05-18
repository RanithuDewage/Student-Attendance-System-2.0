from pathlib import Path
import csv
import json

# ============================================================
# Base paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
ATTENDANCE_DIR = DATA_DIR / "attendance"
FACES_DIR = DATA_DIR / "faces"

BACKUP_DIR = BASE_DIR / "backups"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
QR_DIR = DATA_DIR / "qr"
LOGS_DIR = BASE_DIR / "logs"

# ============================================================
# Main files
# ============================================================

DB_PATH = DATA_DIR / "attendance.db"
SETTINGS_FILE = DATA_DIR / "settings.json"
ROSTER_FILE = DATA_DIR / "roster.csv"

FACE_MODEL_FILE = MODELS_DIR / "face_model.yml"
LABELS_FILE = MODELS_DIR / "labels.json"

# ============================================================
# App title
# ============================================================

APP_TITLE = "Student Attendance System 2.0"

# ============================================================
# CSV column layouts
# ============================================================

# Attendance CSV columns used by attendance_manager.py
ATTENDANCE_COLUMNS = [
    "timestamp",
    "date",
    "time",
    "student_id",
    "name",
    "status",
    "distance",
]

# Roster CSV columns
ROSTER_COLUMNS = [
    "student_id",
    "name",
    "email",
    "department",
    "batch",
    "parent_phone",
    "parent_email",
    "photo_path",
    "active",
    "photo_count",
]

# ============================================================
# Default settings
# ============================================================

DEFAULT_SETTINGS = {
    # UI / session
    "theme": "dark",
    "class_start_time": "09:00",
    "grace_minutes": 10,
    "current_session": "Morning",
    "camera_index": 0,

    # Face recognition
    "face_threshold": 62.0,
    "beep_unknown": True,
    "enable_liveness": True,
    "enable_qr_fallback": True,

    # Parent notifications on mark
    "notify_parent_sms_on_mark": True,
    "notify_parent_email_on_mark": False,

    # After session auto notifications
    "auto_sms_after_session": True,
    "auto_email_after_session": False,

    # Telegram (optional)
    "telegram_bot_token": "your_token_here",
    "telegram_chat_id": "your_chat_id_here",

    # Email / SMTP settings
    "smtp_host": "your_smtp_host",
    "smtp_port": 587,
    "smtp_use_tls": True,
    "smtp_use_ssl": False,
    "sender_email": "your_email@example.com",
    "sender_password": "your_email_password",
    "receiver_email": "your_receiver@example.com",

    # SMS settings (optional)
    "sms_mode": "console",   # console / twilio
    "twilio_account_sid": "your_twilio_account_sid",
    "twilio_auth_token": "your_twilio_auth_token",
    "twilio_from_number": "your_twilio_from_number",
}

# ============================================================
# Folder / file helpers
# ============================================================

def ensure_dirs():
    """Create all required folders if they do not exist."""
    for p in [
        DATA_DIR,
        ATTENDANCE_DIR,
        FACES_DIR,
        BACKUP_DIR,
        MODELS_DIR,
        REPORTS_DIR,
        QR_DIR,
        LOGS_DIR,
    ]:
        p.mkdir(parents=True, exist_ok=True)


def _create_roster_file_if_missing():
    """Create empty roster.csv with headers if it doesn't exist."""
    if not ROSTER_FILE.exists():
        ROSTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ROSTER_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(ROSTER_COLUMNS)


def _create_settings_file_if_missing():
    """Create settings.json with default settings if missing."""
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)


def ensure_base_files():
    """Create required folders and base files."""
    ensure_dirs()
    _create_roster_file_if_missing()
    _create_settings_file_if_missing()


# ============================================================
# JSON helpers
# ============================================================

def load_settings():
    """
    Load settings from settings.json.
    If file is missing or broken, return DEFAULT_SETTINGS.
    """
    ensure_base_files()

    settings = DEFAULT_SETTINGS.copy()

    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    settings.update(loaded)
    except Exception:
        pass

    return settings


def save_settings(settings: dict):
    """Save the full settings dictionary to settings.json."""
    ensure_base_files()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def save_json(path, data):
    """Save any dictionary/list object to JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path, default=None):
    """Load JSON from a file, return default on failure."""
    p = Path(path)
    if not p.exists():
        return default

    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default