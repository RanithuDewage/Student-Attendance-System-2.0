import threading
import time
from datetime import date, datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

import cv2
from PIL import Image, ImageTk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    import winsound
except Exception:
    winsound = None

from config import APP_TITLE, FACE_MODEL_FILE, LABELS_FILE, REPORTS_DIR
from db import (
    init_db, load_settings, save_settings, set_setting,
    verify_admin, create_admin, change_admin_password,
    save_student, delete_student, search_students, get_student,
    mark_attendance, update_attendance_status, delete_attendance,
    get_attendance, get_daily_counts, get_weekly_counts,
    get_monthly_summary, log_audit, increment_unknown, increment_known, compute_status
)
from face_utils import (
    capture_faces, add_face_photo_from_file, train_face_model, load_labels,
    prepare_face, extract_largest_face, face_quality, remove_student_faces
)
from reports import export_day_report, export_monthly_report, backup_system, restore_system
from mailer import send_report_email
from phase2_tools import (
    TelegramNotifier,
    generate_student_qr,
    scan_qr_from_frame,
    parse_qr_payload,
    BasicLivenessChecker,
    export_monthly_pdf
)


def iso_today():
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


class LoginWindow(tk.Tk):
    """Version 2 login window."""

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Admin Login")
        self.geometry("780x440")
        self.resizable(False, False)
        self.configure(bg="#0b1220")

        init_db()
        self.settings = load_settings()

        self.password_visible = False
        self._busy = False

        self._setup_styles()
        self._build()
        self._center_window()

        # Keyboard shortcuts
        self.bind("<Return>", lambda event: self.login())
        self.bind("<Escape>", lambda event: self.clear_form())

    def _setup_styles(self):
        """Configure login window styles."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("LoginRoot.TFrame", background="#0b1220")
        style.configure("LeftPanel.TFrame", background="#0f172a")
        style.configure("RightPanel.TFrame", background="#0b1220")
        style.configure("LoginCard.TFrame", background="#111827", relief="flat")

        style.configure(
            "LoginTitle.TLabel",
            background="#111827",
            foreground="#f8fafc",
            font=("Segoe UI", 20, "bold")
        )
        style.configure(
            "LoginSubtitle.TLabel",
            background="#111827",
            foreground="#94a3b8",
            font=("Segoe UI", 10)
        )
        style.configure(
            "LoginLabel.TLabel",
            background="#111827",
            foreground="#e5e7eb",
            font=("Segoe UI", 10)
        )
        style.configure(
            "LoginHint.TLabel",
            background="#111827",
            foreground="#94a3b8",
            font=("Segoe UI", 9)
        )
        style.configure(
            "SideTitle.TLabel",
            background="#0f172a",
            foreground="#f8fafc",
            font=("Segoe UI", 18, "bold")
        )
        style.configure(
            "SideText.TLabel",
            background="#0f172a",
            foreground="#cbd5e1",
            font=("Segoe UI", 10)
        )
        style.configure(
            "LoginButton.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=8
        )
        style.configure(
            "SmallButton.TButton",
            font=("Segoe UI", 9),
            padding=4
        )
        style.configure(
            "LoginEntry.TEntry",
            padding=6,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Check.TCheckbutton",
            background="#111827",
            foreground="#cbd5e1",
            font=("Segoe UI", 9)
        )

    def _center_window(self):
        """Center the window on the screen."""
        self.update_idletasks()
        w = 780
        h = 440
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        """Build the login UI."""
        root = ttk.Frame(self, style="LoginRoot.TFrame")
        root.pack(fill="both", expand=True)

        # Left panel
        left = ttk.Frame(root, style="LeftPanel.TFrame", width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ttk.Label(left, text="Welcome Back!", style="SideTitle.TLabel").pack(anchor="w", padx=22, pady=(40, 8))
        ttk.Label(left, text="Developed by Team RushX", style="SideText.TLabel").pack(anchor="w", padx=22, pady=(24, 0))

        # Right side
        right = ttk.Frame(root, style="RightPanel.TFrame")
        right.pack(side="left", fill="both", expand=True)

        # Center card
        card = ttk.Frame(right, style="LoginCard.TFrame", padding=24)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Avatar circle
        avatar = tk.Canvas(card, width=76, height=76, bg="#111827", highlightthickness=0)
        avatar.grid(row=0, column=0, columnspan=3, pady=(0, 12))
        avatar.create_oval(6, 6, 70, 70, fill="#2563eb", outline="")
        avatar.create_text(38, 38, text="A", fill="white", font=("Segoe UI", 26, "bold"))

        # Header
        ttk.Label(card, text="Student Attendance System", style="LoginTitle.TLabel").grid(
            row=1, column=0, columnspan=3, pady=(0, 4)
        )
        ttk.Label(card, text="Sign in to continue", style="LoginSubtitle.TLabel").grid(
            row=2, column=0, columnspan=3, pady=(0, 16)
        )

        # Variables
        self.user_var = tk.StringVar(value=self.settings.get("last_username", "admin"))
        self.pass_var = tk.StringVar()
        self.remember_var = tk.BooleanVar(value=bool(self.settings.get("last_username", "")))
        self.status_var = tk.StringVar(value="")

        # Username row
        ttk.Label(card, text="Username", style="LoginLabel.TLabel").grid(
            row=3, column=0, sticky="e", padx=(0, 10), pady=8
        )
        self.user_entry = ttk.Entry(card, textvariable=self.user_var, width=28, style="LoginEntry.TEntry")
        self.user_entry.grid(row=3, column=1, columnspan=2, pady=8, sticky="ew")

        # Password row
        ttk.Label(card, text="Password", style="LoginLabel.TLabel").grid(
            row=4, column=0, sticky="e", padx=(0, 10), pady=8
        )
        self.pass_entry = ttk.Entry(card, textvariable=self.pass_var, width=22, show="*", style="LoginEntry.TEntry")
        self.pass_entry.grid(row=4, column=1, pady=8, sticky="ew")

        self.toggle_btn = ttk.Button(card, text="Show", style="SmallButton.TButton", command=self.toggle_password)
        self.toggle_btn.grid(row=4, column=2, padx=(8, 0), pady=8)

        # Remember me
        ttk.Checkbutton(
            card,
            text="Remember Username",
            variable=self.remember_var,
            style="Check.TCheckbutton"
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 8))

        # Login button
        self.login_btn = ttk.Button(card, text="Login", style="LoginButton.TButton", command=self.login)
        self.login_btn.grid(row=6, column=0, columnspan=3, pady=(10, 8), sticky="ew")

        # Status message
        self.status_label = ttk.Label(card, textvariable=self.status_var, style="LoginHint.TLabel")
        self.status_label.grid(row=7, column=0, columnspan=3, pady=(4, 0))

        # Default note
        ttk.Label(card, text="Default: admin / admin123", style="LoginHint.TLabel").grid(
            row=8, column=0, columnspan=3, pady=(8, 0)
        )

        # Layout tuning
        card.columnconfigure(0, weight=0)
        card.columnconfigure(1, weight=1)
        card.columnconfigure(2, weight=0)

        self.user_entry.focus_set()

    def toggle_password(self):
        """Show or hide the password field."""
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.pass_entry.configure(show="")
            self.toggle_btn.configure(text="Hide")
        else:
            self.pass_entry.configure(show="*")
            self.toggle_btn.configure(text="Show")

    def clear_form(self):
        """Clear password and status text."""
        self.pass_var.set("")
        self.status_var.set("")
        self.pass_entry.focus_set()

    def login(self):
        """Validate credentials and open the main app."""
        if self._busy:
            return

        username = self.user_var.get().strip()
        password = self.pass_var.get().strip()

        if not username or not password:
            self.status_var.set("Please enter username and password.")
            return

        self._busy = True
        self.login_btn.configure(text="Signing in...", state="disabled")
        self.status_var.set("Checking credentials...")

        # Small delay for a smoother UI feel
        self.after(120, lambda: self._do_login(username, password))

    def _do_login(self, username, password):
        """Perform login check and open the main window if valid."""
        ok, role = verify_admin(username, password)

        if not ok:
            self._busy = False
            self.login_btn.configure(text="Login", state="normal")
            self.status_var.set("Invalid username or password.")
            messagebox.showerror("Login Failed", "Invalid username or password")
            return

        # Save or clear remembered username
        if self.remember_var.get():
            save_settings({"last_username": username})
        else:
            save_settings({"last_username": ""})

        log_audit(username, "login", f"role={role}")

        self.status_var.set("Login successful. Opening dashboard...")
        self.after(180, lambda: self._open_main_app(username, role or "operator"))

    def _open_main_app(self, username, role):
        """Close login window and open the main app."""
        self.destroy()
        app = MainApp(username, role)
        app.mainloop()


class MainApp(tk.Tk):
    """Main application window."""

    def __init__(self, username, role):
        super().__init__()
        self.current_user = username
        self.current_role = role

        self.title(APP_TITLE)
        self.geometry("1360x860")
        self.minsize(1280, 800)

        init_db()
        self.settings = load_settings()

        self.telegram = TelegramNotifier(
            self.settings.get("telegram_bot_token", ""),
            self.settings.get("telegram_chat_id", "")
        )
        self.liveness_checker = BasicLivenessChecker()
        self.active_candidate_sid = None
        self.last_unknown_alert_ts = 0

        self.theme = self.settings.get("theme", "dark")
        self.apply_theme()

        self.session_marked = set()
        self.camera_running = False
        self.cap = None
        self.recognizer = None
        self.labels = {}

        self._build_ui()
        self.load_model()
        self.refresh_all()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- THEME ----------------

    def apply_theme(self):
        """Apply dark or light theme."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        if self.theme == "dark":
            bg = "#111827"
            panel = "#1f2937"
            text = "#f9fafb"
            accent = "#60a5fa"
        else:
            bg = "#f4f6fb"
            panel = "#ffffff"
            text = "#111827"
            accent = "#2563eb"

        self.palette = {"bg": bg, "panel": panel, "text": text, "accent": accent}
        self.configure(bg=bg)

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("TButton", padding=6)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", padding=[12, 8])

        style.configure("Card.TFrame", background=panel, relief="ridge")
        style.configure("CardTitle.TLabel", background=panel, foreground=text, font=("Segoe UI", 10, "bold"))
        style.configure("CardValue.TLabel", background=panel, foreground=accent, font=("Segoe UI", 20, "bold"))

        style.configure("Treeview", background=panel, fieldbackground=panel, foreground=text, rowheight=26)
        style.configure("Treeview.Heading", background=accent, foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", accent)])

    # ---------------- UI BUILDERS ----------------

    def _build_ui(self):
        """Build notebook tabs and GUI widgets."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.dashboard_tab = ttk.Frame(self.notebook, padding=10)
        self.students_tab = ttk.Frame(self.notebook, padding=10)
        self.capture_tab = ttk.Frame(self.notebook, padding=10)
        self.attendance_tab = ttk.Frame(self.notebook, padding=10)
        self.reports_tab = ttk.Frame(self.notebook, padding=10)
        self.settings_tab = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.students_tab, text="Students")
        self.notebook.add(self.capture_tab, text="Capture & Train")
        self.notebook.add(self.attendance_tab, text="Attendance")
        self.notebook.add(self.reports_tab, text="Reports")
        self.notebook.add(self.settings_tab, text="Settings")

        self._build_dashboard()
        self._build_students()
        self._build_capture()
        self._build_attendance()
        self._build_reports()
        self._build_settings()

    def _card(self, parent, title, var):
        """Create a dashboard stat card."""
        frame = ttk.Frame(parent, style="Card.TFrame", padding=12)
        ttk.Label(frame, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=var, style="CardValue.TLabel").pack(anchor="w", pady=(8, 0))
        return frame

    def _build_dashboard(self):
        """Build dashboard cards, charts, and logs."""
        self.total_students_var = tk.StringVar(value="0")
        self.present_var = tk.StringVar(value="0")
        self.late_var = tk.StringVar(value="0")
        self.absent_var = tk.StringVar(value="0")
        self.unknown_var = tk.StringVar(value="0")

        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill="x", pady=(0, 10))

        self._card(cards, "Total Students", self.total_students_var).grid(row=0, column=0, padx=6, sticky="ew")
        self._card(cards, "Present", self.present_var).grid(row=0, column=1, padx=6, sticky="ew")
        self._card(cards, "Late", self.late_var).grid(row=0, column=2, padx=6, sticky="ew")
        self._card(cards, "Absent", self.absent_var).grid(row=0, column=3, padx=6, sticky="ew")
        self._card(cards, "Unknown Faces", self.unknown_var).grid(row=0, column=4, padx=6, sticky="ew")

        for i in range(5):
            cards.columnconfigure(i, weight=1)

        actions = ttk.Frame(self.dashboard_tab)
        actions.pack(fill="x", pady=(0, 8))

        ttk.Button(actions, text="Refresh Dashboard", command=self.refresh_all).pack(side="left", padx=4)
        ttk.Button(actions, text="Start Camera", command=self.start_camera).pack(side="left", padx=4)
        ttk.Button(actions, text="Stop Camera", command=self.stop_camera).pack(side="left", padx=4)
        ttk.Button(actions, text="Train Model", command=self.train_model).pack(side="left", padx=4)
        ttk.Button(actions, text="Dark/Light Theme", command=self.toggle_theme).pack(side="left", padx=4)

        charts = ttk.Frame(self.dashboard_tab)
        charts.pack(fill="both", expand=True)

        fig = Figure(figsize=(10, 4), dpi=100)
        self.ax1 = fig.add_subplot(1, 2, 1)
        self.ax2 = fig.add_subplot(1, 2, 2)
        self.chart_canvas = FigureCanvasTkAgg(fig, master=charts)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)

        self.log_box = ScrolledText(self.dashboard_tab, height=10, wrap="word")
        self.log_box.pack(fill="x", pady=(8, 0))
        self.log_box.insert("end", "Ready.\n")
        self.log_box.configure(state="disabled")

    def _build_students(self):
        """Build student Attending form and tree view."""
        top = ttk.Frame(self.students_tab)
        top.pack(fill="x", pady=(0, 8))

        self.student_search_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.student_search_var, width=28).pack(side="left", padx=4)
        ttk.Button(top, text="Search", command=self.refresh_students).pack(side="left", padx=4)
        ttk.Button(top, text="Show All", command=self.clear_student_filter).pack(side="left", padx=4)

        form = ttk.LabelFrame(self.students_tab, text="Add / Update Student", padding=10)
        form.pack(fill="x", pady=(0, 10))

        self.sid_var = tk.StringVar()
        self.sname_var = tk.StringVar()
        self.semail_var = tk.StringVar()
        self.sdept_var = tk.StringVar()
        self.sbatch_var = tk.StringVar()
        self.sphoto_var = tk.StringVar()
        self.sactive_var = tk.IntVar(value=1)

        labels = ["Student ID", "Name", "Email", "Department", "Batch", "Profile Photo"]
        vars_ = [self.sid_var, self.sname_var, self.semail_var, self.sdept_var, self.sbatch_var, self.sphoto_var]

        for i, (lbl, var) in enumerate(zip(labels, vars_)):
            ttk.Label(form, text=lbl).grid(row=0, column=i * 2, sticky="w", padx=(0, 4), pady=5)
            ttk.Entry(form, textvariable=var, width=18 if i < 2 else 20).grid(row=0, column=i * 2 + 1, padx=(0, 10), pady=5)

        ttk.Button(form, text="Browse", command=self.browse_student_photo).grid(row=0, column=12, padx=4)
        ttk.Checkbutton(form, text="Active", variable=self.sactive_var).grid(row=0, column=13, padx=10)
        ttk.Button(form, text="Save Student", command=self.save_student_form).grid(row=0, column=14, padx=6)
        ttk.Button(form, text="Delete Student", command=self.delete_student_form).grid(row=0, column=15, padx=6)
        ttk.Button(form, text="Clear", command=self.clear_student_form).grid(row=0, column=16, padx=6)

        tree_frame = ttk.LabelFrame(self.students_tab, text="Students", padding=8)
        tree_frame.pack(fill="both", expand=True)

        cols = ("student_id", "name", "email", "department", "batch", "photo_count", "active")
        self.students_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)
        for c in cols:
            self.students_tree.heading(c, text=c.replace("_", " ").title())
            self.students_tree.column(c, width=120, anchor="center")
        self.students_tree.column("name", width=160)
        self.students_tree.pack(side="left", fill="both", expand=True)
        self.students_tree.bind("<<TreeviewSelect>>", self.on_student_select)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.students_tree.yview)
        scroll.pack(side="right", fill="y")
        self.students_tree.configure(yscrollcommand=scroll.set)

    def _build_capture(self):
        """Build face capture and training controls."""
        form = ttk.LabelFrame(self.capture_tab, text="Face Capture / Training", padding=12)
        form.pack(fill="x")

        self.cap_sid_var = tk.StringVar()
        self.cap_name_var = tk.StringVar()
        self.cap_samples_var = tk.StringVar(value="10")

        ttk.Label(form, text="Student ID").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.cap_sid_var, width=20).grid(row=0, column=1, padx=6, pady=5)

        ttk.Label(form, text="Name").grid(row=0, column=2, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.cap_name_var, width=20).grid(row=0, column=3, padx=6, pady=5)

        ttk.Label(form, text="Samples").grid(row=0, column=4, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.cap_samples_var, width=10).grid(row=0, column=5, padx=6, pady=5)

        ttk.Button(form, text="Capture From Camera", command=self.capture_from_camera).grid(row=0, column=6, padx=8)
        ttk.Button(form, text="Add Photo From File", command=self.add_photo_from_file_ui).grid(row=0, column=7, padx=8)
        ttk.Button(form, text="Train Model", command=self.train_model).grid(row=0, column=8, padx=8)
        ttk.Button(form, text="Reload Model", command=self.load_model).grid(row=0, column=9, padx=8)
        ttk.Button(form, text="Generate QR", command=self.generate_qr_for_student).grid(row=0, column=10, padx=8)

        ttk.Label(
            self.capture_tab,
            text="Tip: 2-5 photos per student is better. Clear front + left + right angles improve accuracy.",
            foreground="#888"
        ).pack(anchor="w", pady=8)

    def _build_attendance(self):
        """Build live camera preview and attendance table."""
        top = ttk.Frame(self.attendance_tab)
        top.pack(fill="x", pady=(0, 8))

        self.session_var = tk.StringVar(value=self.settings.get("current_session", "Morning"))
        ttk.Label(top, text="Session").pack(side="left")
        ttk.Entry(top, textvariable=self.session_var, width=16).pack(side="left", padx=5)
        ttk.Button(top, text="Save Session", command=self.save_session_name).pack(side="left", padx=5)

        ttk.Button(top, text="Start Live Preview", command=self.start_camera).pack(side="left", padx=10)
        ttk.Button(top, text="Stop", command=self.stop_camera).pack(side="left", padx=5)

        body = ttk.Frame(self.attendance_tab)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = ttk.LabelFrame(body, text="Live Stats", padding=10)
        right.pack(side="right", fill="y")

        self.camera_label = ttk.Label(left)
        self.camera_label.pack(fill="both", expand=True)

        self.live_present_var = tk.StringVar(value="0")
        self.live_late_var = tk.StringVar(value="0")
        self.live_unknown_var = tk.StringVar(value="0")
        self.live_total_var = tk.StringVar(value="0")

        for text, var in [
            ("Present", self.live_present_var),
            ("Late", self.live_late_var),
            ("Unknown", self.live_unknown_var),
            ("Marked", self.live_total_var),
        ]:
            ttk.Label(right, text=text, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 0))
            ttk.Label(right, textvariable=var, font=("Segoe UI", 16, "bold")).pack(anchor="w")

        ttk.Separator(right).pack(fill="x", pady=10)
        ttk.Label(right, text="Unknown alert beep").pack(anchor="w")
        self.beep_var = tk.BooleanVar(value=bool(self.settings.get("beep_unknown", True)))
        ttk.Checkbutton(right, text="Enable", variable=self.beep_var, command=self.save_beep_setting).pack(anchor="w")

        ttk.Button(right, text="Refresh Records", command=self.refresh_attendance).pack(fill="x", pady=(10, 4))

        filter_box = ttk.LabelFrame(self.attendance_tab, text="Search / Filter", padding=8)
        filter_box.pack(fill="x", pady=(8, 8))

        self.att_date_var = tk.StringVar(value=iso_today())
        self.att_session_filter_var = tk.StringVar(value=self.session_var.get())
        self.att_status_var = tk.StringVar(value="All")
        self.att_query_var = tk.StringVar()

        ttk.Label(filter_box, text="Date").grid(row=0, column=0, sticky="w")
        ttk.Entry(filter_box, textvariable=self.att_date_var, width=12).grid(row=0, column=1, padx=5)
        ttk.Label(filter_box, text="Session").grid(row=0, column=2, sticky="w")
        ttk.Entry(filter_box, textvariable=self.att_session_filter_var, width=14).grid(row=0, column=3, padx=5)
        ttk.Label(filter_box, text="Status").grid(row=0, column=4, sticky="w")
        ttk.Combobox(filter_box, textvariable=self.att_status_var, values=["All", "Present", "Late", "Absent"], width=10, state="readonly").grid(row=0, column=5, padx=5)
        ttk.Label(filter_box, text="Search").grid(row=0, column=6, sticky="w")
        ttk.Entry(filter_box, textvariable=self.att_query_var, width=18).grid(row=0, column=7, padx=5)
        ttk.Button(filter_box, text="Apply", command=self.refresh_attendance).grid(row=0, column=8, padx=5)

        tree_frame = ttk.Frame(self.attendance_tab)
        tree_frame.pack(fill="both", expand=True)

        cols = ("id", "date", "session", "time", "student_id", "name", "status", "distance", "manual")
        self.att_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.att_tree.heading(c, text=c.title())
            self.att_tree.column(c, width=95, anchor="center")
        self.att_tree.column("name", width=160)
        self.att_tree.column("session", width=110)
        self.att_tree.pack(side="left", fill="both", expand=True)
        self.att_tree.bind("<<TreeviewSelect>>", self.on_attendance_select)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.att_tree.yview)
        scroll.pack(side="right", fill="y")
        self.att_tree.configure(yscrollcommand=scroll.set)

        btns = ttk.Frame(self.attendance_tab)
        btns.pack(fill="x", pady=6)

        ttk.Button(btns, text="Mark Present", command=lambda: self.override_selected("Present")).pack(side="left", padx=4)
        ttk.Button(btns, text="Mark Late", command=lambda: self.override_selected("Late")).pack(side="left", padx=4)
        ttk.Button(btns, text="Mark Absent", command=lambda: self.override_selected("Absent")).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete Row", command=self.delete_selected_attendance).pack(side="left", padx=4)

        self.selected_attendance_id = None

    def _build_reports(self):
        """Build report controls and monthly summary tree."""
        top = ttk.Frame(self.reports_tab)
        top.pack(fill="x", pady=(0, 8))

        self.report_date_var = tk.StringVar(value=iso_today())
        self.report_month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))

        ttk.Label(top, text="Date").pack(side="left")
        ttk.Entry(top, textvariable=self.report_date_var, width=12).pack(side="left", padx=4)
        ttk.Button(top, text="Day Report", command=self.generate_day_report).pack(side="left", padx=4)

        ttk.Label(top, text="Month").pack(side="left", padx=(10, 0))
        ttk.Entry(top, textvariable=self.report_month_var, width=10).pack(side="left", padx=4)
        ttk.Button(top, text="Monthly Report", command=self.generate_monthly_report).pack(side="left", padx=4)
        ttk.Button(top, text="Export Monthly PDF", command=self.export_monthly_pdf_ui).pack(side="left", padx=4)

        ttk.Button(top, text="Backup", command=self.backup_data).pack(side="left", padx=10)
        ttk.Button(top, text="Restore", command=self.restore_data).pack(side="left", padx=4)
        ttk.Button(top, text="Send Email", command=self.send_email_report).pack(side="left", padx=4)

        main = ttk.Frame(self.reports_tab)
        main.pack(fill="both", expand=True)

        self.report_text = ScrolledText(main, height=18, wrap="word")
        self.report_text.pack(fill="both", expand=True, pady=(0, 8))
        self.report_text.insert("end", "Reports will appear here.\n")
        self.report_text.configure(state="disabled")

        summary_frame = ttk.LabelFrame(main, text="Monthly Summary", padding=8)
        summary_frame.pack(fill="both", expand=True)

        cols = ("student_id", "name", "present", "late", "absent", "total", "percentage")
        self.month_tree = ttk.Treeview(summary_frame, columns=cols, show="headings", height=10)
        for c in cols:
            self.month_tree.heading(c, text=c.title())
            self.month_tree.column(c, width=110, anchor="center")
        self.month_tree.column("name", width=180)
        self.month_tree.pack(fill="both", expand=True)

    def _build_settings(self):
        """Build system settings, admin and email sections."""
        main = ttk.Frame(self.settings_tab)
        main.pack(fill="both", expand=True)

        left = ttk.LabelFrame(main, text="System Settings", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = ttk.LabelFrame(main, text="Admin / Email / Telegram", padding=10)
        right.pack(side="right", fill="y")

        self.theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        self.class_start_var = tk.StringVar(value=self.settings.get("class_start_time", "09:00"))
        self.grace_var = tk.StringVar(value=str(self.settings.get("grace_minutes", 10)))
        self.cam_index_var = tk.StringVar(value=str(self.settings.get("camera_index", 0)))
        self.threshold_var = tk.StringVar(value=str(self.settings.get("face_threshold", 62.0)))
        self.session_setting_var = tk.StringVar(value=self.settings.get("current_session", "Morning"))
        self.auto_email_var = tk.BooleanVar(value=bool(self.settings.get("auto_email_after_session", False)))
        self.beep_unknown_var = tk.BooleanVar(value=bool(self.settings.get("beep_unknown", True)))
        self.enable_liveness_var = tk.BooleanVar(value=bool(self.settings.get("enable_liveness", True)))
        self.enable_qr_var = tk.BooleanVar(value=bool(self.settings.get("enable_qr_fallback", True)))

        self.smtp_host_var = tk.StringVar(value=self.settings.get("smtp_host", ""))
        self.smtp_port_var = tk.StringVar(value=str(self.settings.get("smtp_port", 587)))
        self.smtp_tls_var = tk.BooleanVar(value=bool(self.settings.get("smtp_use_tls", True)))
        self.sender_email_var = tk.StringVar(value=self.settings.get("sender_email", ""))
        self.sender_password_var = tk.StringVar(value=self.settings.get("sender_password", ""))
        self.receiver_email_var = tk.StringVar(value=self.settings.get("receiver_email", ""))

        self.telegram_token_var = tk.StringVar(value=self.settings.get("telegram_bot_token", ""))
        self.telegram_chat_var = tk.StringVar(value=self.settings.get("telegram_chat_id", ""))

        row = 0

        def add_row(lbl, var, width=20, show=None):
            nonlocal row
            ttk.Label(left, text=lbl).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(left, textvariable=var, width=width, show=show).grid(row=row, column=1, sticky="w", pady=4, padx=6)
            row += 1

        add_row("Theme", self.theme_var, width=20)
        add_row("Class Start Time", self.class_start_var)
        add_row("Grace Minutes", self.grace_var)
        add_row("Camera Index", self.cam_index_var)
        add_row("Face Threshold", self.threshold_var)
        add_row("Current Session", self.session_setting_var, width=24)

        ttk.Checkbutton(left, text="Auto Email After Session", variable=self.auto_email_var).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        ttk.Checkbutton(left, text="Unknown Face Beep", variable=self.beep_unknown_var).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        ttk.Checkbutton(left, text="Enable Liveness Check", variable=self.enable_liveness_var).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        ttk.Checkbutton(left, text="Enable QR Fallback", variable=self.enable_qr_var).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        ttk.Button(left, text="Save Settings", command=self.save_settings_ui).grid(row=row, column=0, columnspan=2, pady=10, sticky="ew")
        row += 1

        ttk.Separator(left, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        add_row("SMTP Host", self.smtp_host_var, width=28)
        add_row("SMTP Port", self.smtp_port_var, width=12)
        ttk.Checkbutton(left, text="Use TLS", variable=self.smtp_tls_var).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        add_row("Sender Email", self.sender_email_var, width=28)
        add_row("Sender Password", self.sender_password_var, width=28, show="*")
        add_row("Receiver Email", self.receiver_email_var, width=28)

        ttk.Separator(right, orient="horizontal").grid(row=0, column=0, sticky="ew", pady=6)
        ttk.Label(right, text="Create Admin").grid(row=1, column=0, sticky="w", pady=4)
        self.new_admin_user_var = tk.StringVar()
        self.new_admin_pass_var = tk.StringVar()
        self.new_admin_role_var = tk.StringVar(value="operator")
        ttk.Entry(right, textvariable=self.new_admin_user_var, width=24).grid(row=2, column=0, pady=4)
        ttk.Entry(right, textvariable=self.new_admin_pass_var, width=24, show="*").grid(row=3, column=0, pady=4)
        ttk.Entry(right, textvariable=self.new_admin_role_var, width=24).grid(row=4, column=0, pady=4)
        ttk.Button(right, text="Add / Update Admin", command=self.create_admin_ui).grid(row=5, column=0, pady=6, sticky="ew")

        self.old_pass_var = tk.StringVar()
        self.new_pass_var = tk.StringVar()

        ttk.Separator(right, orient="horizontal").grid(row=6, column=0, sticky="ew", pady=8)
        ttk.Label(right, text="Change My Password").grid(row=7, column=0, sticky="w", pady=4)
        ttk.Entry(right, textvariable=self.old_pass_var, width=24, show="*").grid(row=8, column=0, pady=4)
        ttk.Entry(right, textvariable=self.new_pass_var, width=24, show="*").grid(row=9, column=0, pady=4)
        ttk.Button(right, text="Change Password", command=self.change_my_password).grid(row=10, column=0, pady=6, sticky="ew")

        ttk.Separator(right, orient="horizontal").grid(row=11, column=0, sticky="ew", pady=8)
        ttk.Label(right, text="Telegram Bot Token").grid(row=12, column=0, sticky="w", pady=4)
        ttk.Entry(right, textvariable=self.telegram_token_var, width=28).grid(row=13, column=0, pady=4)

        ttk.Label(right, text="Telegram Chat ID").grid(row=14, column=0, sticky="w", pady=4)
        ttk.Entry(right, textvariable=self.telegram_chat_var, width=28).grid(row=15, column=0, pady=4)
        ttk.Button(right, text="Test Telegram", command=self.test_telegram).grid(row=16, column=0, pady=6, sticky="ew")

    # ---------------- DASHBOARD HELPERS ----------------

    def log(self, text):
        """Append a line to the dashboard log box."""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def refresh_all(self):
        """Refresh all visible data on the app."""
        self.refresh_dashboard()
        self.refresh_students()
        self.refresh_attendance()
        self.refresh_month_tree()

    def refresh_dashboard(self):
        """Refresh stat cards and charts."""
        counts = get_daily_counts(iso_today(), self.session_var.get().strip())
        self.total_students_var.set(str(counts["total_students"]))
        self.present_var.set(str(counts["present"]))
        self.late_var.set(str(counts["late"]))
        self.absent_var.set(str(counts["absent"]))
        self.unknown_var.set(str(counts["unknown"]))
        self.live_present_var.set(str(counts["present"]))
        self.live_late_var.set(str(counts["late"]))
        self.live_unknown_var.set(str(counts["unknown"]))
        self.live_total_var.set(str(counts["marked"]))

        weekly = get_weekly_counts()
        self.ax1.clear()
        self.ax2.clear()

        self.ax1.bar(["Present", "Late", "Absent"], [counts["present"], counts["late"], counts["absent"]],
                     color=["#22c55e", "#f59e0b", "#ef4444"])
        self.ax1.set_title("Today Status")
        self.ax1.grid(axis="y", alpha=0.2)

        x = [d["date"][5:] for d in weekly]
        y = [d["count"] for d in weekly]
        self.ax2.plot(x, y, marker="o", color="#60a5fa")
        self.ax2.set_title("Weekly Attendance")
        self.ax2.grid(alpha=0.2)

        self.chart_canvas.draw_idle()

    # ---------------- STUDENTS ----------------

    def refresh_students(self):
        """Refresh the students table."""
        query = self.student_search_var.get().strip()
        rows = search_students(query)
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)

        for r in rows:
            self.students_tree.insert("", "end", values=(
                r["student_id"], r["name"], r.get("email", ""), r.get("department", ""),
                r.get("batch", ""), r.get("photo_count", 0), r.get("active", 1)
            ))

    def clear_student_filter(self):
        """Clear search filter and refresh student list."""
        self.student_search_var.set("")
        self.refresh_students()

    def clear_student_form(self):
        """Clear student form fields."""
        self.sid_var.set("")
        self.sname_var.set("")
        self.semail_var.set("")
        self.sdept_var.set("")
        self.sbatch_var.set("")
        self.sphoto_var.set("")
        self.sactive_var.set(1)
        self.students_tree.selection_remove(self.students_tree.selection())

    def on_student_select(self, event=None):
        """Load selected student row into the form."""
        sel = self.students_tree.selection()
        if not sel:
            return
        values = self.students_tree.item(sel[0], "values")
        self.sid_var.set(values[0])
        self.sname_var.set(values[1])
        self.semail_var.set(values[2])
        self.sdept_var.set(values[3])
        self.sbatch_var.set(values[4])
        student = get_student(values[0])
        self.sphoto_var.set(student.get("photo_path", "") if student else "")
        self.sactive_var.set(int(values[6]))

    def browse_student_photo(self):
        """Browse and choose a profile photo."""
        p = filedialog.askopenfilename(title="Select Profile Photo", filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if p:
            self.sphoto_var.set(p)

    def save_student_form(self):
        """Save or update a student record."""
        try:
            sid = self.sid_var.get().strip()
            existing = get_student(sid) or {}

            save_student(
                sid,
                self.sname_var.get().strip() or existing.get("name", ""),
                self.semail_var.get().strip() or existing.get("email", ""),
                self.sdept_var.get().strip() or existing.get("department", ""),
                self.sbatch_var.get().strip() or existing.get("batch", ""),
                self.sphoto_var.get().strip() or existing.get("photo_path", ""),
                int(self.sactive_var.get()),
                photo_count=existing.get("photo_count", 0)
            )
            log_audit(self.current_user, "save_student", f"{sid} | {self.sname_var.get().strip()}")
            self.log(f"[STUDENT] Saved {sid} - {self.sname_var.get().strip()}")
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_student_form(self):
        """Delete selected student and their face folder."""
        sid = self.sid_var.get().strip()
        if not sid:
            return
        if not messagebox.askyesno("Confirm", f"Delete student {sid}?"):
            return
        remove_student_faces(sid)
        delete_student(sid)
        log_audit(self.current_user, "delete_student", sid)
        self.clear_student_form()
        self.refresh_all()

    # ---------------- CAPTURE / TRAIN ----------------

    def capture_from_camera(self):
        """Capture face images from webcam."""
        sid = self.cap_sid_var.get().strip()
        name = self.cap_name_var.get().strip()
        samples = int(self.cap_samples_var.get().strip() or "10")
        camera_index = int(self.cam_index_var.get().strip())

        if not sid or not name:
            messagebox.showerror("Error", "Student ID and Name required")
            return

        self.stop_camera()

        try:
            result = capture_faces(sid, name, samples=samples, camera_index=camera_index)
            self.log(f"[CAPTURE] {result['student_id']} | {result['name']} | {result['captured']} images")
            log_audit(self.current_user, "capture_faces", f"{sid} | {name} | {result['captured']} images")
            self.refresh_students()
        except Exception as e:
            messagebox.showerror("Capture Error", str(e))

    def add_photo_from_file_ui(self):
        """Add one face image from a file."""
        sid = self.cap_sid_var.get().strip()
        name = self.cap_name_var.get().strip()

        if not sid or not name:
            messagebox.showerror("Error", "Student ID and Name required")
            return

        file_path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
        )
        if not file_path:
            return

        try:
            saved = add_face_photo_from_file(sid, name, file_path)
            self.log(f"[CAPTURE] Added photo {saved}")
            log_audit(self.current_user, "add_face_photo", f"{sid} | {name}")
            self.refresh_students()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def generate_qr_for_student(self):
        """Generate a QR code for a student."""
        sid = self.sid_var.get().strip() or self.cap_sid_var.get().strip()
        name = self.sname_var.get().strip() or self.cap_name_var.get().strip()

        if not sid or not name:
            messagebox.showerror("Error", "Student ID and Name required")
            return

        try:
            qr_path = generate_student_qr(sid, name)
            self.log(f"[QR] Generated: {qr_path}")
            messagebox.showinfo("QR Generated", f"Saved:\n{qr_path}")
        except Exception as e:
            messagebox.showerror("QR Error", str(e))

    def train_model(self):
        """Train the face recognition model."""
        try:
            result = train_face_model()
            self.load_model()
            self.log(f"[TRAIN] Done. Students={result['students']} Images={result['images']}")
            log_audit(self.current_user, "train_model", f"students={result['students']}, images={result['images']}")
            messagebox.showinfo("Train", "Model trained successfully.")
        except Exception as e:
            messagebox.showerror("Training Error", str(e))

    def load_model(self):
        """Load model and labels from disk."""
        self.labels = load_labels()
        if FACE_MODEL_FILE.exists():
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.recognizer.read(str(FACE_MODEL_FILE))
            self.log("[MODEL] Loaded face model.")
        else:
            self.recognizer = None
            self.log("[MODEL] No trained model found yet.")

    # ---------------- ATTENDANCE / CAMERA ----------------

    def save_session_name(self):
        """Save the active session name."""
        s = self.session_var.get().strip() or "Morning"
        self.settings["current_session"] = s
        save_settings({"current_session": s})
        self.att_session_filter_var.set(s)
        self.log(f"[SETTINGS] Session set to {s}")

    def save_beep_setting(self):
        """Save unknown-face beep setting."""
        self.settings["beep_unknown"] = bool(self.beep_var.get())
        save_settings({"beep_unknown": bool(self.beep_var.get())})

    def test_telegram(self):
        """Send a test Telegram message."""
        try:
            self.telegram = TelegramNotifier(
                self.telegram_token_var.get().strip(),
                self.telegram_chat_var.get().strip()
            )
            ok, msg = self.telegram.send_message("Attendance system test message.")
            if ok:
                messagebox.showinfo("Telegram", "Test message sent.")
            else:
                messagebox.showwarning("Telegram", msg)
        except Exception as e:
            messagebox.showerror("Telegram Error", str(e))

    def start_camera(self):
        """Start live camera preview."""
        if self.camera_running:
            return

        self.settings = load_settings()
        self.session_marked = set()
        self.last_unknown_alert_ts = 0
        self.liveness_checker.reset()
        self.active_candidate_sid = None

        cam_index = int(self.cam_index_var.get().strip() or "0")
        self.cap = cv2.VideoCapture(cam_index)
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Camera is not accessible. Check the index and permissions.")
            return

        self.camera_running = True
        self.update_camera()
        self.log("[CAMERA] Started live preview.")

    def stop_camera(self):
        """Stop live camera preview."""
        self.camera_running = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.camera_label.configure(image="")
        self.log("[CAMERA] Stopped.")

    def _beep_unknown(self):
        """Play a short beep for unknown faces."""
        if not self.beep_var.get():
            return
        if winsound:
            try:
                winsound.Beep(1800, 120)
            except Exception:
                pass
        else:
            self.bell()

    def update_camera(self):
        """
        Main live camera loop.
        Handles:
        - face recognition
        - QR fallback
        - liveness checking
        - unknown face alerts
        """
        if not self.camera_running or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.stop_camera()
            return

        session_name = self.session_var.get().strip() or "Morning"
        enable_liveness = bool(self.enable_liveness_var.get())
        enable_qr = bool(self.enable_qr_var.get())
        threshold = float(self.threshold_var.get().strip() or "62")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        face_box = extract_largest_face(gray)
        candidate_marked = False

        if face_box is not None and self.recognizer is not None and self.labels:
            x, y, fw, fh = face_box
            roi = prepare_face(gray, face_box)

            try:
                label_id, dist = self.recognizer.predict(roi)
                label_id = str(label_id)
                known = label_id in self.labels and dist < threshold

                if known:
                    info = self.labels[label_id]
                    sid = info.get("student_id", "")
                    name = info.get("name", "")
                    color = (0, 255, 0)
                    status = compute_status(
                        self.class_start_var.get().strip() or "09:00",
                        int(self.grace_var.get().strip() or "10")
                    )

                    if enable_liveness:
                        if self.active_candidate_sid != sid:
                            self.liveness_checker.reset()
                            self.active_candidate_sid = sid

                        passed, stats = self.liveness_checker.update(roi, face_box)

                        cv2.putText(
                            frame,
                            f"Live check: blinks={stats['blink_count']} motion={stats['motion_score']}",
                            (x, max(25, y - 28)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (255, 255, 0),
                            2
                        )

                        if passed and sid not in self.session_marked:
                            mark_attendance(
                                sid, name, status, float(dist),
                                session=session_name,
                                manual=0,
                                date_str=iso_today()
                            )
                            self.session_marked.add(sid)
                            candidate_marked = True
                            increment_known(iso_today(), session_name, 1)
                            self.log(f"[MARK] {sid} | {name} | {status}")
                            log_audit(self.current_user, "auto_mark", f"{sid} | {name} | {status} | dist={dist:.1f}")

                            if status == "Late" and self.telegram.is_configured():
                                try:
                                    self.telegram.send_message(
                                        f"Late attendance: {sid} | {name} | {iso_today()} | {session_name}"
                                    )
                                except Exception:
                                    pass
                    else:
                        if sid not in self.session_marked:
                            mark_attendance(
                                sid, name, status, float(dist),
                                session=session_name,
                                manual=0,
                                date_str=iso_today()
                            )
                            self.session_marked.add(sid)
                            candidate_marked = True
                            increment_known(iso_today(), session_name, 1)
                            self.log(f"[MARK] {sid} | {name} | {status}")
                            log_audit(self.current_user, "auto_mark", f"{sid} | {name} | {status} | dist={dist:.1f}")

                            if status == "Late" and self.telegram.is_configured():
                                try:
                                    self.telegram.send_message(
                                        f"Late attendance: {sid} | {name} | {iso_today()} | {session_name}"
                                    )
                                except Exception:
                                    pass

                    text = f"{sid} | {name} | {status} | {dist:.1f}"
                    cv2.rectangle(frame, (x, y), (x + fw, y + fh), color, 2)
                    cv2.putText(
                        frame,
                        text,
                        (x, max(30, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        color,
                        2
                    )
                else:
                    color = (0, 0, 255)
                    cv2.rectangle(frame, (x, y), (x + fw, y + fh), color, 2)
                    cv2.putText(
                        frame,
                        f"Unknown | {dist:.1f}",
                        (x, max(30, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        color,
                        2
                    )

                    now = time.time()
                    if now - self.last_unknown_alert_ts > 10:
                        self.last_unknown_alert_ts = now
                        increment_unknown(iso_today(), session_name, 1)
                        if self.telegram.is_configured():
                            try:
                                self.telegram.send_message(
                                    f"Unknown face detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Session: {session_name}"
                                )
                            except Exception:
                                pass
                        if bool(self.beep_var.get()):
                            self._beep_unknown()

            except Exception:
                pass

        # QR fallback path
        if enable_qr and not candidate_marked:
            payload, bbox = scan_qr_from_frame(frame)
            if payload:
                sid, name = parse_qr_payload(payload)
                student = get_student(sid)

                if student and sid not in self.session_marked:
                    status = compute_status(
                        self.class_start_var.get().strip() or "09:00",
                        int(self.grace_var.get().strip() or "10")
                    )

                    mark_attendance(
                        sid,
                        student.get("name", name) or name,
                        status,
                        0.0,
                        session=session_name,
                        manual=0,
                        date_str=iso_today()
                    )
                    self.session_marked.add(sid)
                    log_audit(self.current_user, "qr_mark", f"{sid} | {student.get('name', name)} | {status}")

                    if self.telegram.is_configured():
                        try:
                            self.telegram.send_message(
                                f"QR attendance: {sid} | {student.get('name', name)} | {status}"
                            )
                        except Exception:
                            pass

        counts = get_daily_counts(iso_today(), session_name)

        cv2.putText(frame, f"Session: {session_name}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"Present: {counts['present']}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Late: {counts['late']}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        cv2.putText(frame, f"Unknown: {counts['unknown']}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = img.resize((760, 500))
        imgtk = ImageTk.PhotoImage(image=img)

        self.camera_label.imgtk = imgtk
        self.camera_label.configure(image=imgtk)

        self.live_present_var.set(str(counts["present"]))
        self.live_late_var.set(str(counts["late"]))
        self.live_unknown_var.set(str(counts["unknown"]))
        self.live_total_var.set(str(counts["marked"]))

        self.refresh_dashboard()
        self.after(25, self.update_camera)

    def refresh_attendance(self):
        """Refresh attendance table with current filters."""
        date_str = self.att_date_var.get().strip() or iso_today()
        session = self.att_session_filter_var.get().strip() or None
        status = self.att_status_var.get().strip() or "All"
        query = self.att_query_var.get().strip()

        rows = get_attendance(date_str=date_str, session=session, status=status, query=query)

        for item in self.att_tree.get_children():
            self.att_tree.delete(item)

        for r in rows:
            self.att_tree.insert("", "end", values=(
                r["id"], r["date"], r["session"], r["time"], r["student_id"],
                r["name"], r["status"], f"{float(r.get('distance', 0)):.1f}", r.get("manual", 0)
            ))

    def on_attendance_select(self, event=None):
        """Track selected attendance row."""
        sel = self.att_tree.selection()
        if not sel:
            self.selected_attendance_id = None
            return
        vals = self.att_tree.item(sel[0], "values")
        self.selected_attendance_id = vals[0]

    def override_selected(self, status):
        """Manually change attendance status for selected row."""
        if not self.selected_attendance_id:
            messagebox.showerror("Error", "Select an attendance row first")
            return
        update_attendance_status(self.selected_attendance_id, status, actor=self.current_user)
        self.log(f"[MANUAL] Row {self.selected_attendance_id} -> {status}")
        self.refresh_all()

    def delete_selected_attendance(self):
        """Delete selected attendance row."""
        if not self.selected_attendance_id:
            messagebox.showerror("Error", "Select an attendance row first")
            return
        if not messagebox.askyesno("Confirm", "Delete selected attendance row?"):
            return
        delete_attendance(self.selected_attendance_id, actor=self.current_user)
        self.log(f"[DELETE] Row {self.selected_attendance_id}")
        self.refresh_all()

    # ---------------- REPORTS ----------------

    def generate_day_report(self):
        """Generate day attendance and absent reports."""
        date_str = self.report_date_var.get().strip() or iso_today()
        session = self.session_var.get().strip() or "Morning"
        paths, summary = export_day_report(date_str, session=session)

        self._write_report_text(
            f"Day Report: {date_str} | Session: {session}\n"
            f"Total Students: {summary['total_students']}\n"
            f"Present: {summary['present']}\n"
            f"Late: {summary['late']}\n"
            f"Absent: {summary['absent']}\n"
            f"Unknown: {summary['unknown']}\n\n"
            f"Files:\n"
            f"Attendance CSV: {paths['attendance_csv']}\n"
            f"Attendance XLSX: {paths['attendance_xlsx']}\n"
            f"Absent CSV: {paths['absent_csv']}\n"
            f"Absent XLSX: {paths['absent_xlsx']}\n"
        )
        log_audit(self.current_user, "generate_day_report", date_str)
        messagebox.showinfo("Report", "Day report generated.")

    def generate_monthly_report(self):
        """Generate monthly CSV/XLSX report and refresh tree."""
        month = self.report_month_var.get().strip() or date.today().strftime("%Y-%m")
        result = export_monthly_report(month)

        self._write_report_text(
            f"Monthly Report: {month}\n"
            f"Total Sessions: {result['total_sessions']}\n"
            f"CSV: {result['csv']}\n"
            f"XLSX: {result['xlsx']}\n"
        )
        self._fill_month_tree(result["rows"])
        log_audit(self.current_user, "generate_monthly_report", month)
        messagebox.showinfo("Report", "Monthly report generated.")

    def export_monthly_pdf_ui(self):
        """Export monthly summary to PDF."""
        month = self.report_month_var.get().strip() or date.today().strftime("%Y-%m")

        try:
            rows, total_sessions = get_monthly_summary(month)
            out_path = REPORTS_DIR / f"monthly_report_{month}.pdf"
            pdf_file = export_monthly_pdf(month, rows, total_sessions, out_path)
            self._write_report_text(f"Monthly PDF saved:\n{pdf_file}\n")
            log_audit(self.current_user, "export_monthly_pdf", month)
            messagebox.showinfo("PDF", f"PDF saved:\n{pdf_file}")
        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    def _fill_month_tree(self, rows):
        """Fill monthly summary tree with rows."""
        for item in self.month_tree.get_children():
            self.month_tree.delete(item)
        for r in rows:
            self.month_tree.insert("", "end", values=(
                r["student_id"], r["name"], r["present"], r["late"], r["absent"], r["total"], f"{r['percentage']:.2f}"
            ))

    def refresh_month_tree(self):
        """Refresh monthly summary tree from selected month."""
        month = self.report_month_var.get().strip() or date.today().strftime("%Y-%m")
        try:
            rows, _ = get_monthly_summary(month)
            self._fill_month_tree(rows)
        except Exception:
            pass

    def backup_data(self):
        """Create a backup zip file."""
        try:
            path = backup_system()
            self._write_report_text(f"Backup created:\n{path}\n")
            log_audit(self.current_user, "backup", path)
            messagebox.showinfo("Backup", f"Backup created:\n{path}")
        except Exception as e:
            messagebox.showerror("Backup Error", str(e))

    def restore_data(self):
        """Restore a backup zip file."""
        p = filedialog.askopenfilename(title="Select Backup Zip", filetypes=[("Zip Files", "*.zip")])
        if not p:
            return
        if not messagebox.askyesno("Confirm", "This will restore backup files. Continue?"):
            return
        try:
            restore_system(p)
            log_audit(self.current_user, "restore", p)
            messagebox.showinfo("Restore", "Backup restored. Restart the app.")
        except Exception as e:
            messagebox.showerror("Restore Error", str(e))

    def send_email_report(self):
        """Generate a report and email it."""
        try:
            date_str = self.report_date_var.get().strip() or iso_today()
            session = self.session_var.get().strip() or "Morning"
            paths, summary = export_day_report(date_str, session=session)
            body = (
                f"Attendance Report: {date_str}\n"
                f"Session: {session}\n\n"
                f"Total Students: {summary['total_students']}\n"
                f"Present: {summary['present']}\n"
                f"Late: {summary['late']}\n"
                f"Absent: {summary['absent']}\n"
                f"Unknown: {summary['unknown']}\n"
            )
            send_report_email(
                self.settings,
                subject=f"Attendance Report - {date_str}",
                body=body,
                attachments=[paths["attendance_csv"], paths["attendance_xlsx"], paths["absent_csv"], paths["absent_xlsx"]]
            )
            log_audit(self.current_user, "send_email", date_str)
            messagebox.showinfo("Email", "Report sent successfully.")
        except Exception as e:
            messagebox.showerror("Email Error", str(e))

    def _write_report_text(self, text):
        """Write content to the report text box."""
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("end", text)
        self.report_text.configure(state="disabled")

    # ---------------- SETTINGS ----------------

    def save_settings_ui(self):
        """Save settings from the UI into the database."""
        try:
            self.theme = self.theme_var.get().strip() or "dark"
            self.settings = {
                "theme": self.theme,
                "class_start_time": self.class_start_var.get().strip() or "09:00",
                "grace_minutes": int(self.grace_var.get().strip() or "10"),
                "current_session": self.session_setting_var.get().strip() or "Morning",
                "camera_index": int(self.cam_index_var.get().strip() or "0"),
                "face_threshold": float(self.threshold_var.get().strip() or "62"),
                "beep_unknown": bool(self.beep_unknown_var.get()),
                "auto_email_after_session": bool(self.auto_email_var.get()),
                "enable_liveness": bool(self.enable_liveness_var.get()),
                "enable_qr_fallback": bool(self.enable_qr_var.get()),
                "smtp_host": self.smtp_host_var.get().strip(),
                "smtp_port": int(self.smtp_port_var.get().strip() or "587"),
                "smtp_use_tls": bool(self.smtp_tls_var.get()),
                "sender_email": self.sender_email_var.get().strip(),
                "sender_password": self.sender_password_var.get().strip(),
                "receiver_email": self.receiver_email_var.get().strip(),
                "telegram_bot_token": self.telegram_token_var.get().strip(),
                "telegram_chat_id": self.telegram_chat_var.get().strip()
            }
            save_settings(self.settings)
            set_setting("current_session", self.settings["current_session"])
            set_setting("beep_unknown", self.settings["beep_unknown"])
            self.telegram = TelegramNotifier(
                self.settings.get("telegram_bot_token", ""),
                self.settings.get("telegram_chat_id", "")
            )
            self.apply_theme()
            self.refresh_all()
            self.log("[SETTINGS] Saved.")
            log_audit(self.current_user, "save_settings", "updated")
            messagebox.showinfo("Saved", "Settings saved.")
        except Exception as e:
            messagebox.showerror("Settings Error", str(e))

    def create_admin_ui(self):
        """Create or update an admin user."""
        try:
            create_admin(self.new_admin_user_var.get(), self.new_admin_pass_var.get(), self.new_admin_role_var.get())
            log_audit(self.current_user, "create_admin", self.new_admin_user_var.get())
            messagebox.showinfo("Admin", "Admin user saved.")
        except Exception as e:
            messagebox.showerror("Admin Error", str(e))

    def change_my_password(self):
        """Change password for the current logged-in admin."""
        if change_admin_password(self.current_user, self.old_pass_var.get(), self.new_pass_var.get()):
            messagebox.showinfo("Success", "Password changed.")
            self.old_pass_var.set("")
            self.new_pass_var.set("")
        else:
            messagebox.showerror("Error", "Old password incorrect")

    def toggle_theme(self):
        """Toggle between dark and light mode."""
        self.theme = "light" if self.theme == "dark" else "dark"
        self.theme_var.set(self.theme)
        self.save_settings_ui()

    # ---------------- CLOSE ----------------

    def on_close(self):
        """Gracefully close the app."""
        self.stop_camera()
        self.destroy()