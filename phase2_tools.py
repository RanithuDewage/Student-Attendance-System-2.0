from pathlib import Path
import time
import cv2
import requests
import qrcode

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from config import QR_DIR


class TelegramNotifier:
    """Send Telegram messages from the attendance system."""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = str(bot_token).strip()
        self.chat_id = str(chat_id).strip()

    def is_configured(self):
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str):
        """Send a text message to Telegram."""
        if not self.is_configured():
            return False, "Telegram not configured"

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text
        }

        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        return True, "Message sent"

    def send_photo(self, caption: str, photo_path: str):
        """Send an image to Telegram."""
        if not self.is_configured():
            return False, "Telegram not configured"

        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {
                "chat_id": self.chat_id,
                "caption": caption
            }
            r = requests.post(url, data=data, files=files, timeout=20)
            r.raise_for_status()
        return True, "Photo sent"


def generate_student_qr(student_id: str, name: str, out_path: str = None):
    """Generate a QR image for a student."""
    QR_DIR.mkdir(parents=True, exist_ok=True)

    student_id = str(student_id).strip()
    name = str(name).strip()
    payload = f"{student_id}|{name}"

    if out_path is None:
        out_path = QR_DIR / f"{student_id}.png"
    else:
        out_path = Path(out_path)

    img = qrcode.make(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    return str(out_path)


def scan_qr_from_frame(frame):
    """Scan a QR code from the current frame."""
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(frame)

    if data and data.strip():
        return data.strip(), bbox

    return None, None


def parse_qr_payload(payload: str):
    """Parse QR payload in the format student_id|name."""
    parts = str(payload).split("|")
    student_id = parts[0].strip() if len(parts) > 0 else ""
    name = parts[1].strip() if len(parts) > 1 else ""
    return student_id, name


class BasicLivenessChecker:
    """
    Basic liveness detector using:
    - blink detection
    - small head motion

    This is a simple heuristic, not a full anti-spoofing model.
    """

    def __init__(self, min_blinks=1, min_motion=12.0, min_seconds=2.0):
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        self.min_blinks = min_blinks
        self.min_motion = min_motion
        self.min_seconds = min_seconds
        self.reset()

    def reset(self):
        """Reset liveness counters."""
        self.start_time = None
        self.prev_eye_open = None
        self.blink_count = 0
        self.closed_seen = False
        self.motion_score = 0.0
        self.prev_center = None

    def update(self, gray_face, face_box=None):
        """
        Update liveness state using the face crop and optional face box.
        Returns:
            passed (bool), stats (dict)
        """
        if self.start_time is None:
            self.start_time = time.time()

        eyes = self.eye_cascade.detectMultiScale(
            gray_face,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(18, 18)
        )
        eye_open = len(eyes) >= 2

        if self.prev_eye_open is True and not eye_open:
            self.closed_seen = True

        if self.prev_eye_open is False and eye_open and self.closed_seen:
            self.blink_count += 1
            self.closed_seen = False

        self.prev_eye_open = eye_open

        if face_box is not None:
            x, y, w, h = face_box
            cx = x + (w / 2.0)
            cy = y + (h / 2.0)

            if self.prev_center is not None:
                self.motion_score += abs(cx - self.prev_center[0]) + abs(cy - self.prev_center[1])

            self.prev_center = (cx, cy)

        elapsed = time.time() - self.start_time
        passed = elapsed >= self.min_seconds and (
            self.blink_count >= self.min_blinks or self.motion_score >= self.min_motion
        )

        stats = {
            "elapsed": round(elapsed, 1),
            "blink_count": self.blink_count,
            "motion_score": round(self.motion_score, 1),
            "eyes_open": eye_open,
            "passed": passed
        }
        return passed, stats


def export_monthly_pdf(month_str, summary_rows, total_sessions, out_path):
    """Export monthly attendance summary to a PDF file."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Monthly Attendance Report", styles["Title"]))
    story.append(Paragraph(f"Month: {month_str}", styles["Normal"]))
    story.append(Paragraph(f"Total Sessions: {total_sessions}", styles["Normal"]))
    story.append(Spacer(1, 12))

    total_present = sum(int(x.get("present", 0)) for x in summary_rows)
    total_late = sum(int(x.get("late", 0)) for x in summary_rows)
    total_absent = sum(int(x.get("absent", 0)) for x in summary_rows)

    summary_data = [
        ["Metric", "Value"],
        ["Students", str(len(summary_rows))],
        ["Total Present", str(total_present)],
        ["Total Late", str(total_late)],
        ["Total Absent", str(total_absent)],
    ]

    summary_table = Table(summary_data, colWidths=[180, 120])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    table_data = [["Student ID", "Name", "Present", "Late", "Absent", "Total", "%"]]
    for row in summary_rows:
        table_data.append([
            row.get("student_id", ""),
            row.get("name", ""),
            row.get("present", 0),
            row.get("late", 0),
            row.get("absent", 0),
            row.get("total", 0),
            f"{float(row.get('percentage', 0)):.2f}"
        ])

    table = Table(table_data, repeatRows=1, colWidths=[65, 145, 40, 40, 40, 40, 40])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#e5e7eb")]),
    ]))
    story.append(table)

    doc.build(story)
    return str(out_path)