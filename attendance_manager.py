from datetime import datetime, date, timedelta
import json
import cv2
import pandas as pd

from config import (
    ATTENDANCE_DIR, ROSTER_FILE, ATTENDANCE_COLUMNS, ROSTER_COLUMNS,
    FACE_MODEL_FILE, LABELS_FILE, ensure_base_files, load_settings, save_json
)

def today_str():
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()

class AttendanceManager:
    """
    Main business logic for:
    - student roster handling
    - attendance marking
    - report generation
    - live face-recognition attendance session
    """

    def __init__(self, settings=None):
        ensure_base_files()
        self.settings = settings or load_settings()

    def reload_settings(self):
        """Reload settings from disk."""
        self.settings = load_settings()

    def _day_dir(self, date_str=None):
        """Return a date-wise attendance folder path."""
        date_str = date_str or today_str()
        p = ATTENDANCE_DIR / date_str
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _attendance_csv(self, date_str=None):
        return self._day_dir(date_str) / "attendance.csv"

    def _attendance_xlsx(self, date_str=None):
        return self._day_dir(date_str) / "attendance.xlsx"

    def _late_csv(self, date_str=None):
        return self._day_dir(date_str) / "late_report.csv"

    def _late_xlsx(self, date_str=None):
        return self._day_dir(date_str) / "late_report.xlsx"

    def _absent_csv(self, date_str=None):
        return self._day_dir(date_str) / "absent_report.csv"

    def _absent_xlsx(self, date_str=None):
        return self._day_dir(date_str) / "absent_report.xlsx"

    def _summary_json(self, date_str=None):
        return self._day_dir(date_str) / "session_summary.json"

    def _empty_attendance_df(self):
        """Create an empty attendance dataframe with required columns."""
        return pd.DataFrame(columns=ATTENDANCE_COLUMNS)

    def _empty_roster_df(self):
        """Create an empty roster dataframe with required columns."""
        return pd.DataFrame(columns=ROSTER_COLUMNS)

    def load_attendance(self, date_str=None):
        """Load attendance CSV for a given date."""
        csv_path = self._attendance_csv(date_str)
        if not csv_path.exists() or csv_path.stat().st_size == 0:
            return self._empty_attendance_df()

        try:
            df = pd.read_csv(csv_path, dtype=str)
        except Exception:
            return self._empty_attendance_df()

        for col in ATTENDANCE_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        return df[ATTENDANCE_COLUMNS]

    def load_roster(self):
        """Load the student roster file."""
        if not ROSTER_FILE.exists() or ROSTER_FILE.stat().st_size == 0:
            return self._empty_roster_df()

        try:
            df = pd.read_csv(ROSTER_FILE, dtype=str)
        except Exception:
            return self._empty_roster_df()

        for col in ROSTER_COLUMNS:
            if col not in df.columns:
                if col == "active":
                    df[col] = "1"
                else:
                    df[col] = ""

        df["active"] = df["active"].fillna("1")
        return df[ROSTER_COLUMNS]

    def save_roster(self, df):
        """Save roster dataframe back to CSV."""
        df = df.copy()

        for col in ROSTER_COLUMNS:
            if col not in df.columns:
                if col == "active":
                    df[col] = "1"
                else:
                    df[col] = ""

        df.to_csv(ROSTER_FILE, index=False)

    def add_student(self, student_id: str, name: str, email: str = ""):
        """
        Add a new student to roster or update existing student info.
        """
        student_id = str(student_id).strip()
        name = str(name).strip()
        email = str(email).strip()

        if not student_id or not name:
            raise ValueError("Student ID and name are required")

        df = self.load_roster()
        if df.empty:
            df = self._empty_roster_df()

        mask = df["student_id"].astype(str) == student_id

        new_row = {
            "student_id": student_id,
            "name": name,
            "email": email,
            "active": "1"
        }

        if mask.any():
            df.loc[mask, ["name", "email", "active"]] = [name, email, "1"]
        else:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        self.save_roster(df)
        return True

    def _export_excel(self, df, path):
        """Export dataframe to Excel if openpyxl is available."""
        try:
            df.to_excel(path, index=False)
        except Exception:
            pass

    def _compute_status(self, now_dt):
        """
        Determine whether a student is Present or Late.
        """
        start_time_str = self.settings.get("class_start_time", "09:00")
        grace = int(self.settings.get("grace_minutes", 10))

        try:
            class_start = datetime.strptime(start_time_str, "%H:%M").time()
        except Exception:
            class_start = datetime.strptime("09:00", "%H:%M").time()

        cutoff = datetime.combine(now_dt.date(), class_start) + timedelta(minutes=grace)
        return "Late" if now_dt > cutoff else "Present"

    def mark_attendance(self, student_id: str, name: str, distance: float, when=None):
        """
        Add a student entry to the current day's attendance file.
        Returns (created_new_row, status).
        """
        student_id = str(student_id).strip()
        name = str(name).strip()
        now_dt = when or datetime.now()
        date_str = now_dt.date().isoformat()

        df = self.load_attendance(date_str)

        if not df.empty and (df["student_id"].astype(str) == student_id).any():
            existing = df[df["student_id"].astype(str) == student_id].iloc[0].to_dict()
            return False, existing.get("status", "Present")

        status = self._compute_status(now_dt)

        row = {
            "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "date": date_str,
            "time": now_dt.strftime("%H:%M:%S"),
            "student_id": student_id,
            "name": name,
            "status": status,
            "distance": f"{float(distance):.2f}"
        }

        if df.empty:
            df = self._empty_attendance_df()

        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

        csv_path = self._attendance_csv(date_str)
        xlsx_path = self._attendance_xlsx(date_str)

        df.to_csv(csv_path, index=False)
        self._export_excel(df, xlsx_path)

        return True, status

    def daily_summary(self, date_str=None):
        """
        Return a summary dictionary for a given date.
        """
        date_str = date_str or today_str()
        att = self.load_attendance(date_str)
        roster = self.load_roster()

        if roster.empty:
            roster = self._empty_roster_df()

        active_mask = roster["active"].fillna("1").astype(str).str.lower().isin(["1", "true", "yes", "y"])
        active_roster = roster[active_mask].copy()

        present_ids = set()
        late_count = 0

        if not att.empty:
            present_ids = set(att["student_id"].astype(str).tolist())
            late_count = int((att["status"].astype(str).str.lower() == "late").sum())

        absent_count = max(int(len(active_roster) - len(present_ids)), 0)

        return {
            "date": date_str,
            "total_registered": int(len(active_roster)),
            "present": int(len(present_ids)),
            "late": int(late_count),
            "absent": int(absent_count),
            "unknown": 0,
            "marked": int(len(present_ids))
        }

    def generate_reports(self, date_str=None):
        """
        Generate attendance, late, and absent reports for a given date.
        """
        date_str = date_str or today_str()

        att = self.load_attendance(date_str)
        roster = self.load_roster()

        if roster.empty:
            roster = self._empty_roster_df()

        # Always save attendance report, even if empty
        att.to_csv(self._attendance_csv(date_str), index=False)
        self._export_excel(att, self._attendance_xlsx(date_str))

        if att.empty:
            late_df = self._empty_attendance_df()
        else:
            late_df = att[att["status"].astype(str).str.lower() == "late"].copy()

        active_mask = roster["active"].fillna("1").astype(str).str.lower().isin(["1", "true", "yes", "y"])
        active_roster = roster[active_mask].copy()

        present_ids = set(att["student_id"].astype(str).tolist()) if not att.empty else set()
        absent_df = active_roster[~active_roster["student_id"].astype(str).isin(present_ids)].copy()

        # Save late report
        late_csv = self._late_csv(date_str)
        late_xlsx = self._late_xlsx(date_str)
        late_df.to_csv(late_csv, index=False)
        self._export_excel(late_df, late_xlsx)

        # Save absent report
        absent_csv = self._absent_csv(date_str)
        absent_xlsx = self._absent_xlsx(date_str)
        absent_df.to_csv(absent_csv, index=False)
        self._export_excel(absent_df, absent_xlsx)

        summary = self.daily_summary(date_str)
        summary["late"] = int(len(late_df))
        summary["absent"] = int(len(absent_df))
        summary["present"] = int(len(present_ids))
        summary["total_registered"] = int(len(active_roster))

        save_json(self._summary_json(date_str), summary)

        return {
            "attendance_csv": str(self._attendance_csv(date_str)),
            "attendance_xlsx": str(self._attendance_xlsx(date_str)),
            "late_csv": str(late_csv),
            "late_xlsx": str(late_xlsx),
            "absent_csv": str(absent_csv),
            "absent_xlsx": str(absent_xlsx),
            "summary_json": str(self._summary_json(date_str))
        }, summary

    def run_live_attendance(self, stop_event=None, event_callback=None):
        """
        Run live webcam attendance session using the trained face model.
        """
        self.reload_settings()

        if not FACE_MODEL_FILE.exists():
            raise RuntimeError("face_model.yml not found. Train the model first.")
        if not LABELS_FILE.exists():
            raise RuntimeError("labels.json not found. Train the model first.")

        threshold = float(self.settings.get("face_threshold", 62.0))
        camera_index = int(self.settings.get("camera_index", 0))

        with open(LABELS_FILE, "r", encoding="utf-8") as f:
            labels = json.load(f)

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(str(FACE_MODEL_FILE))

        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError("Camera is not open")

        session_marked = set()
        session = {
            "date": today_str(),
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "unknown": 0,
            "seen_known": 0,
            "marked": 0
        }

        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    break

                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.2,
                    minNeighbors=5,
                    minSize=(100, 100)
                )

                for (x, y, w, h) in faces:
                    face_roi = gray[y:y+h, x:x+w]

                    try:
                        face_roi = cv2.resize(face_roi, (200, 200))
                    except Exception:
                        continue

                    try:
                        label_id, distance = recognizer.predict(face_roi)
                    except Exception:
                        continue

                    label_id_str = str(label_id)
                    known = label_id_str in labels and distance < threshold

                    if known:
                        info = labels[label_id_str]
                        student_id = str(info.get("student_id", "")).strip()
                        name = str(info.get("name", "")).strip()

                        session["seen_known"] += 1
                        color = (0, 255, 0)
                        text = f"{student_id} | {name} ({distance:.1f})"

                        if student_id and student_id not in session_marked:
                            created, status = self.mark_attendance(student_id, name, float(distance))
                            session_marked.add(student_id)

                            if created:
                                session["marked"] += 1

                            if event_callback:
                                event_callback({
                                    "type": "mark",
                                    "student_id": student_id,
                                    "name": name,
                                    "status": status,
                                    "distance": float(distance)
                                })
                    else:
                        session["unknown"] += 1
                        color = (0, 0, 255)
                        text = f"Unknown ({distance:.1f})"

                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(
                        frame,
                        text,
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        color,
                        2
                    )

                cv2.putText(
                    frame,
                    f"Known: {session['seen_known']}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )
                cv2.putText(
                    frame,
                    f"Unknown: {session['unknown']}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )
                cv2.putText(
                    frame,
                    f"Marked: {session['marked']}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    frame,
                    "Press q to close",
                    (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 0),
                    2
                )

                cv2.imshow("Attendance Session", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        # Generate session files after webcam session ends
        paths, summary = self.generate_reports(today_str())
        summary.update(session)
        summary["reports"] = paths
        summary["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        save_json(self._summary_json(today_str()), summary)

        if event_callback:
            event_callback({
                "type": "finished",
                "summary": summary
            })

        return summary