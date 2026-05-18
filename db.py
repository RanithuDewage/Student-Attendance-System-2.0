import sqlite3
import hashlib
import json
from datetime import datetime, date, timedelta
from calendar import monthrange

from config import DB_PATH, DEFAULT_SETTINGS, ensure_dirs


# -------------------------
# Helpers
# -------------------------

def now_str():
    """Return current timestamp as a string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


def normalize_status(status: str) -> str:
    """
    Normalize status values to a standard form:
    Present, Late, Absent
    """
    s = str(status or "").strip().lower()
    mapping = {
        "present": "Present",
        "late": "Late",
        "absent": "Absent",
    }
    return mapping.get(s, str(status).strip().title() if str(status).strip() else "Present")


def _connect():
    """
    Create a SQLite connection.
    Row factory is set to sqlite3.Row so results can be accessed like dictionaries.
    """
    ensure_dirs()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# -------------------------
# DB Init / Seed
# -------------------------

def init_db():
    """
    Create all required tables if they do not exist.
    Also seeds default admin and default settings.
    """
    ensure_dirs()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _connect() as conn:
        cur = conn.cursor()

        # Admin users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'operator',
            created_at TEXT NOT NULL
        )
        """)

        # Students table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            department TEXT DEFAULT '',
            batch TEXT DEFAULT '',
            photo_path TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            photo_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        # Attendance records table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            session TEXT NOT NULL,
            time TEXT NOT NULL,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            distance REAL DEFAULT 0,
            manual INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(date, session, student_id)
        )
        """)

        # Audit log table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT ''
        )
        """)

        # Settings table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)

        # Session stats table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS session_stats (
            date TEXT NOT NULL,
            session TEXT NOT NULL,
            unknown_faces INTEGER NOT NULL DEFAULT 0,
            known_faces INTEGER NOT NULL DEFAULT 0,
            started_at TEXT DEFAULT '',
            ended_at TEXT DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (date, session)
        )
        """)

        conn.commit()

    seed_default_admin()
    seed_default_settings()


def seed_default_admin():
    """Create default admin account if no admin exists."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM admins")
        if cur.fetchone()["c"] == 0:
            cur.execute("""
            INSERT INTO admins (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
            """, ("admin", hash_password("admin123"), "admin", now_str()))
            conn.commit()


def seed_default_settings():
    """Insert default settings into the settings table if missing."""
    with _connect() as conn:
        cur = conn.cursor()
        for k, v in DEFAULT_SETTINGS.items():
            cur.execute("SELECT 1 FROM settings WHERE key=?", (k,))
            if cur.fetchone() is None:
                cur.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, json.dumps(v)))
        conn.commit()


# -------------------------
# Settings
# -------------------------

def set_setting(key, value):
    """Insert or update one setting value."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value))
        )
        conn.commit()


def get_setting(key, default=None):
    """Get one setting value from the database."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]


def load_settings():
    """Load all settings and merge them with defaults."""
    settings = DEFAULT_SETTINGS.copy()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM settings")
        for row in cur.fetchall():
            try:
                settings[row["key"]] = json.loads(row["value"])
            except Exception:
                settings[row["key"]] = row["value"]
    return settings


def save_settings(settings: dict):
    """Save multiple settings at once."""
    for k, v in settings.items():
        set_setting(k, v)


# -------------------------
# Admin
# -------------------------

def create_admin(username, password, role="operator"):
    """Create or update an admin account."""
    username = str(username).strip()
    password = str(password).strip()
    role = str(role).strip() or "operator"

    if not username or not password:
        raise ValueError("Username and password required")

    with _connect() as conn:
        conn.execute("""
        INSERT INTO admins (username, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            password_hash=excluded.password_hash,
            role=excluded.role
        """, (username, hash_password(password), role, now_str()))
        conn.commit()


def verify_admin(username, password):
    """Check admin login credentials."""
    username = str(username).strip()
    password = str(password).strip()

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, password_hash, role FROM admins WHERE username=?", (username,))
        row = cur.fetchone()
        if not row:
            return False, None

        ok = row["password_hash"] == hash_password(password)
        return ok, row["role"] if ok else None


def change_admin_password(username, old_password, new_password):
    """Change an admin password after verifying the old password."""
    ok, _ = verify_admin(username, old_password)
    if not ok:
        return False

    with _connect() as conn:
        conn.execute(
            "UPDATE admins SET password_hash=? WHERE username=?",
            (hash_password(new_password), username)
        )
        conn.commit()
    return True


def list_admins():
    """Return all admin users."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, role, created_at FROM admins ORDER BY username")
        return [dict(r) for r in cur.fetchall()]


# -------------------------
# Audit log
# -------------------------

def log_audit(actor, action, details=""):
    """Save an audit log entry."""
    with _connect() as conn:
        conn.execute("""
        INSERT INTO audit_log (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str(), actor, action, details))
        conn.commit()


def get_audit_logs(limit=200):
    """Return recent audit log entries."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT id, timestamp, actor, action, details
        FROM audit_log
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


# -------------------------
# Students
# -------------------------

def save_student(student_id, name, email="", department="", batch="", photo_path="", active=1, photo_count=0):
    """
    Add or update a student record.
    """
    student_id = str(student_id).strip()
    name = str(name).strip()

    if not student_id or not name:
        raise ValueError("Student ID and name required")

    ts = now_str()
    with _connect() as conn:
        conn.execute("""
        INSERT INTO students (
            student_id, name, email, department, batch, photo_path,
            active, photo_count, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            department=excluded.department,
            batch=excluded.batch,
            photo_path=excluded.photo_path,
            active=excluded.active,
            photo_count=excluded.photo_count,
            updated_at=excluded.updated_at
        """, (student_id, name, email, department, batch, photo_path, int(active), int(photo_count), ts, ts))
        conn.commit()


def delete_student(student_id):
    """Delete a student from the database."""
    with _connect() as conn:
        conn.execute("DELETE FROM students WHERE student_id=?", (student_id,))
        conn.commit()


def get_student(student_id):
    """Get one student record by student ID."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE student_id=?", (student_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def search_students(query="", active_only=None):
    """Search students by ID, name, email, department, or batch."""
    q = f"%{query.strip()}%"
    sql = """
    SELECT * FROM students
    WHERE (student_id LIKE ? OR name LIKE ? OR email LIKE ? OR department LIKE ? OR batch LIKE ?)
    """
    params = [q, q, q, q, q]

    if active_only is True:
        sql += " AND active=1"
    elif active_only is False:
        sql += " AND active=0"

    sql += " ORDER BY name COLLATE NOCASE"

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def list_students(active_only=None):
    """List all students, optionally filtered by active status."""
    sql = "SELECT * FROM students"
    if active_only is True:
        sql += " WHERE active=1"
    elif active_only is False:
        sql += " WHERE active=0"
    sql += " ORDER BY name COLLATE NOCASE"

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def count_active_students():
    """Count active students only."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM students WHERE active=1")
        return int(cur.fetchone()["c"])


def count_students():
    """Count all students."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM students")
        return int(cur.fetchone()["c"])


# -------------------------
# Attendance logic
# -------------------------

def compute_status(start_time="09:00", grace_minutes=10):
    """
    Determine attendance status based on the class start time and grace period.
    Returns 'Present' or 'Late'.
    """
    try:
        class_start = datetime.strptime(start_time, "%H:%M").time()
    except Exception:
        class_start = datetime.strptime("09:00", "%H:%M").time()

    cutoff = datetime.combine(date.today(), class_start) + timedelta(minutes=int(grace_minutes))
    return "Late" if datetime.now() > cutoff else "Present"


def mark_attendance(student_id, name, status, distance=0.0, session="Morning", manual=0,
                    date_str=None, time_str=None):
    """
    Insert attendance for one student.
    If the record already exists for the same date/session/student, update only if manual override is used.
    """
    student_id = str(student_id).strip()
    name = str(name).strip()
    status = normalize_status(status)

    date_str = date_str or today_str()
    time_str = time_str or datetime.now().strftime("%H:%M:%S")

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT id, status, manual FROM attendance
        WHERE date=? AND session=? AND student_id=?
        """, (date_str, session, student_id))
        existing = cur.fetchone()

        # If already marked and this is not a manual update, do nothing
        if existing and int(manual) == 0:
            return int(existing["id"]), False, existing["status"]

        # If record exists and manual override is enabled, update it
        if existing:
            conn.execute("""
            UPDATE attendance
            SET time=?, name=?, status=?, distance=?, manual=?, created_at=?
            WHERE id=?
            """, (time_str, name, status, float(distance), int(manual), now_str(), int(existing["id"])))
            conn.commit()
            return int(existing["id"]), True, status

        # Create a new attendance row
        cur.execute("""
        INSERT INTO attendance (
            date, session, time, student_id, name, status, distance, manual, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date_str, session, time_str, student_id, name, status, float(distance), int(manual), now_str()))
        conn.commit()
        return int(cur.lastrowid), True, status


def update_attendance_status(attendance_id, status, actor="admin"):
    """Manual override for attendance status."""
    status = normalize_status(status)
    with _connect() as conn:
        conn.execute("""
        UPDATE attendance
        SET status=?, manual=1, created_at=?
        WHERE id=?
        """, (status, now_str(), int(attendance_id)))
        conn.commit()
    log_audit(actor, "manual_override", f"attendance_id={attendance_id}, status={status}")


def delete_attendance(attendance_id, actor="admin"):
    """Delete a single attendance row."""
    with _connect() as conn:
        conn.execute("DELETE FROM attendance WHERE id=?", (int(attendance_id),))
        conn.commit()
    log_audit(actor, "delete_attendance", f"attendance_id={attendance_id}")


def get_attendance(date_str=None, session=None, status=None, query=""):
    """Fetch attendance rows with optional filters."""
    sql = "SELECT * FROM attendance WHERE 1=1"
    params = []

    if date_str:
        sql += " AND date=?"
        params.append(date_str)

    if session:
        sql += " AND session=?"
        params.append(session)

    if status and status != "All":
        sql += " AND status=?"
        params.append(normalize_status(status))

    if query.strip():
        q = f"%{query.strip()}%"
        sql += " AND (student_id LIKE ? OR name LIKE ?)"
        params.extend([q, q])

    sql += " ORDER BY id DESC"

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


# -------------------------
# Session stats
# -------------------------

def increment_unknown(date_str, session, amount=1):
    """Increase unknown face count for a session."""
    with _connect() as conn:
        conn.execute("""
        INSERT INTO session_stats (date, session, unknown_faces, known_faces, started_at, ended_at, updated_at)
        VALUES (?, ?, ?, 0, '', '', ?)
        ON CONFLICT(date, session) DO UPDATE SET
            unknown_faces=unknown_faces + excluded.unknown_faces,
            updated_at=excluded.updated_at
        """, (date_str, session, int(amount), now_str()))
        conn.commit()


def increment_known(date_str, session, amount=1):
    """Increase known face count for a session."""
    with _connect() as conn:
        conn.execute("""
        INSERT INTO session_stats (date, session, unknown_faces, known_faces, started_at, ended_at, updated_at)
        VALUES (?, ?, 0, ?, '', '', ?)
        ON CONFLICT(date, session) DO UPDATE SET
            known_faces=known_faces + excluded.known_faces,
            updated_at=excluded.updated_at
        """, (date_str, session, int(amount), now_str()))
        conn.commit()


def get_session_unknown(date_str, session):
    """Get unknown face count for one session."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT unknown_faces FROM session_stats WHERE date=? AND session=?", (date_str, session))
        row = cur.fetchone()
        return int(row["unknown_faces"]) if row else 0


# -------------------------
# Summary functions
# -------------------------

def get_daily_counts(date_str=None, session=None):
    """Return daily summary counts for dashboard usage."""
    date_str = date_str or today_str()
    session = session or load_settings().get("current_session", "Morning")

    active_students = count_active_students()
    rows = get_attendance(date_str=date_str, session=session)

    present_ids = set()
    late_ids = set()

    for r in rows:
        sid = r["student_id"]
        st = normalize_status(r["status"])
        if st == "Present":
            present_ids.add(sid)
        elif st == "Late":
            late_ids.add(sid)

    attended_ids = present_ids | late_ids
    absent_calc = max(active_students - len(attended_ids), 0)

    return {
        "date": date_str,
        "session": session,
        "total_students": active_students,
        "present": len(present_ids),
        "late": len(late_ids),
        "absent": absent_calc,
        "marked": len(rows),
        "unknown": get_session_unknown(date_str, session)
    }


def get_weekly_counts(end_date=None):
    """Return attendance count for the last 7 days."""
    end_date = end_date or date.today()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    result = []
    with _connect() as conn:
        cur = conn.cursor()
        for i in range(6, -1, -1):
            d = end_date - timedelta(days=i)
            ds = d.isoformat()
            cur.execute("""
            SELECT COUNT(*) AS c
            FROM attendance
            WHERE date=? AND status IN ('Present', 'Late', 'Absent')
            """, (ds,))
            count = int(cur.fetchone()["c"])
            result.append({"date": ds, "count": count})
    return result


def get_monthly_summary(month_str):
    """
    Build a student-wise monthly summary.
    month_str example: '2026-04'
    """
    year, month = map(int, month_str.split("-"))
    last_day = monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    active_students = list_students(active_only=True)

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM attendance
        WHERE date BETWEEN ? AND ?
        ORDER BY date ASC, session ASC
        """, (start_date, end_date))
        rows = [dict(r) for r in cur.fetchall()]

    # Number of unique session slots recorded in the month
    total_sessions = len(set((r["date"], r["session"]) for r in rows))
    total_sessions = max(total_sessions, 1)

    grouped = {}
    for r in rows:
        sid = r["student_id"]
        status = normalize_status(r["status"])

        grouped.setdefault(
            sid,
            {"Present": 0, "Late": 0, "Absent": 0, "Total": 0, "name": r["name"]}
        )
        if status in grouped[sid]:
            grouped[sid][status] += 1
        grouped[sid]["Total"] += 1
        grouped[sid]["name"] = r["name"]

    summary = []
    for student in active_students:
        sid = student["student_id"]
        data = grouped.get(sid, {
            "Present": 0,
            "Late": 0,
            "Absent": 0,
            "Total": 0,
            "name": student["name"]
        })

        attended = int(data.get("Present", 0)) + int(data.get("Late", 0))
        percentage = round((attended / total_sessions) * 100, 2)

        summary.append({
            "student_id": sid,
            "name": student["name"],
            "department": student.get("department", ""),
            "batch": student.get("batch", ""),
            "present": int(data.get("Present", 0)),
            "late": int(data.get("Late", 0)),
            "absent": int(data.get("Absent", 0)),
            "total": int(data.get("Total", 0)),
            "percentage": percentage
        })

    summary.sort(key=lambda x: x["percentage"], reverse=True)
    return summary, total_sessions


def list_month_dates(month_str):
    """Return all dates for a given month."""
    year, month = map(int, month_str.split("-"))
    last_day = monthrange(year, month)[1]
    return [f"{year:04d}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]