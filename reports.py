from pathlib import Path
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import csv

from openpyxl import Workbook

from config import ATTENDANCE_DIR, REPORTS_DIR, BACKUP_DIR
from db import get_attendance, list_students, get_monthly_summary, get_daily_counts, today_str


def _write_xlsx(headers, rows, xlsx_path, sheet_name="Report"):
    """Write rows into an Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    wb.save(xlsx_path)


def export_day_report(date_str=None, session=None):
    """
    Export attendance and absent reports for one day.
    Returns report file paths and summary counts.
    """
    date_str = date_str or today_str()
    rows = get_attendance(date_str=date_str, session=session)

    day_dir = ATTENDANCE_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    csv_path = day_dir / "attendance.csv"
    xlsx_path = day_dir / "attendance.xlsx"

    headers = ["id", "date", "session", "time", "student_id", "name", "status", "distance", "manual", "created_at"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({h: r.get(h, "") for h in headers})

    _write_xlsx(headers, rows, xlsx_path, "Attendance")

    students = list_students(active_only=True)
    attended_ids = set()
    for r in rows:
        if r["status"] in ("Present", "Late"):
            attended_ids.add(r["student_id"])

    absent_rows = []
    for s in students:
        if s["student_id"] not in attended_ids:
            absent_rows.append({
                "student_id": s["student_id"],
                "name": s["name"],
                "department": s.get("department", ""),
                "batch": s.get("batch", ""),
                "email": s.get("email", "")
            })

    absent_csv = day_dir / "absent_report.csv"
    absent_xlsx = day_dir / "absent_report.xlsx"
    absent_headers = ["student_id", "name", "department", "batch", "email"]

    with open(absent_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=absent_headers)
        writer.writeheader()
        for r in absent_rows:
            writer.writerow(r)

    _write_xlsx(absent_headers, absent_rows, absent_xlsx, "Absent")

    summary = get_daily_counts(date_str, session=session)

    return {
        "attendance_csv": str(csv_path),
        "attendance_xlsx": str(xlsx_path),
        "absent_csv": str(absent_csv),
        "absent_xlsx": str(absent_xlsx)
    }, summary


def export_monthly_report(month_str):
    """
    Export student-wise monthly attendance summary.
    """
    summary_rows, total_sessions = get_monthly_summary(month_str)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = REPORTS_DIR / f"monthly_summary_{month_str}.csv"
    xlsx_path = REPORTS_DIR / f"monthly_summary_{month_str}.xlsx"

    headers = ["student_id", "name", "department", "batch", "present", "late", "absent", "total", "percentage"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in summary_rows:
            writer.writerow({h: r.get(h, "") for h in headers})

    _write_xlsx(headers, summary_rows, xlsx_path, "MonthlySummary")

    return {
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
        "total_sessions": total_sessions,
        "rows": summary_rows
    }


def backup_system():
    """Create a zip backup of data, models, and reports."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"backup_{ts}.zip"

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
        for folder_name in ["data", "models", "reports"]:
            p = Path(folder_name)
            if p.exists():
                for file in p.rglob("*"):
                    if file.is_file():
                        z.write(file, arcname=str(file))

    return str(zip_path)


def restore_system(zip_file_path):
    """Restore a backup zip into the project folder."""
    zip_file_path = Path(zip_file_path)
    if not zip_file_path.exists():
        raise FileNotFoundError("Backup zip not found")

    with ZipFile(zip_file_path, "r") as z:
        z.extractall(Path(".").resolve())

    return True