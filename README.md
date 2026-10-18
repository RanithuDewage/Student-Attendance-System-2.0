<div align="center">

# 🎓 Student Attendance System 2.0

### Smart Attendance. Real-Time Recognition. Simplified Management.

**An intelligent desktop-based attendance management system powered by Python and Computer Vision.**

Developed with ❤️ by **Team NoCtraX**

<br>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-111F68?style=for-the-badge&logo=ultralytics&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-orange?style=for-the-badge)

<br>

**Automate attendance • Recognize faces • Generate reports • Manage records**

</div>

---

## 📌 Table of Contents

- [📖 About the Project](#-about-the-project)
- [✨ Key Features](#-key-features)
- [🛠️ Technology Stack](#️-technology-stack)
- [🏗️ Project Architecture](#️-project-architecture)
- [📸 Screenshots](#-screenshots)
- [⚙️ Installation and Setup](#️-installation-and-setup)
- [🚀 How to Use](#-how-to-use)
- [🔧 Configuration](#-configuration)
- [🔐 Security and Privacy](#-security-and-privacy)
- [🗺️ Future Improvements](#️-future-improvements)
- [🤝 Contributing](#-contributing)
- [🙏 Acknowledgements](#-acknowledgements)
- [📄 License](#-license)
- [📬 Connect With Me](#-connect-with-me)

---

## 📖 About the Project

**Student Attendance System 2.0** is a Python-based desktop application
designed to modernize student attendance management through computer
vision, face recognition, database management, and automation.

Traditional attendance systems often require manual record-keeping,
which can be time-consuming and difficult to manage.

This project provides an integrated solution that helps educational
institutions manage student information, record attendance, monitor
daily statistics, generate reports, and maintain database backups
through a graphical user interface.

The system combines face recognition with attendance tracking and
administrative tools to create a centralized attendance management
workflow.

### 🎯 Project Objectives

- Automate student attendance recording.
- Reduce repetitive manual attendance tasks.
- Simplify student information management.
- Provide real-time attendance monitoring.
- Generate daily and monthly attendance reports.
- Improve data management through backup and restore tools.
- Support administrative notifications and configurable settings.

### 💡 Project Highlights

| Capability | Description |
|---|---|
| 🧠 Computer Vision | Face detection and recognition |
| ⚡ Automation | Automatic attendance recording |
| 📊 Analytics | Attendance statistics and summaries |
| 📄 Reporting | Daily and monthly reports with PDF export |
| 🗄️ Database | Structured data storage using SQLite |
| 🔔 Notifications | Email and Telegram integration |
| 💾 Data Recovery | Database and file backup/restore |
| 🖥️ Desktop GUI | Interactive graphical interface |

---

## ✨ Key Features

### 🔐 1. Secure Admin Authentication

- Administrator login interface.
- Credential-based authentication.
- Remember username option.
- Password change functionality.
- Administrative account management.

### 📊 2. Interactive Dashboard

- Total registered students.
- Present, late, and absent statistics.
- Unknown face count.
- Daily attendance overview.
- Weekly attendance summary.
- Live attendance counters.

### 👨‍🎓 3. Student Management

- Register new students.
- Update student information.
- Delete student records.
- Search and manage student profiles.
- Store student IDs, names, emails, and departments.
- Organize students by batch.
- Activate or deactivate student records.
- Manage student profile photographs.

### 📷 4. Face Capture and Model Training

- Capture face samples using a camera.
- Import student photographs from files.
- Train the face recognition model.
- Reload the trained model when required.
- Generate QR codes for fallback workflows.

### 🧠 5. Live Attendance Recognition

- Real-time face detection and recognition.
- Automatic attendance recording.
- Configurable attendance status handling.
- Present, late, absent, and unknown categories.
- Session-based attendance support.
- Unknown-face alerts and optional beep notifications.

### 📝 6. Attendance Record Management

- View attendance records.
- Filter records by date, session, and status.
- Search attendance entries.
- Mark attendance manually.
- Delete selected records.
- Monitor attendance counts in real time.

### 📈 7. Reports and Analytics

- Daily attendance reports.
- Monthly attendance reports.
- Monthly summary tables.
- PDF report generation.
- Attendance statistics for administrative review.

### 💾 8. Backup and Restore

- Create system backups.
- Preserve database and related application files.
- Restore data from available backups.

**Important:** Always create a separate backup before restoring data.
Restoring an older backup may overwrite newer records.

### 🔔 9. Email and Telegram Notifications

- SMTP-based email integration.
- Telegram Bot API integration.
- Configurable notification settings.
- Test notification functionality.

### ⚙️ 10. Customizable Settings

- Application theme.
- Class start time.
- Attendance grace period.
- Camera index.
- Face recognition threshold.
- Current attendance session.
- Unknown-face sound alerts.
- Liveness-check settings.
- QR fallback options.
- SMTP configuration.
- Telegram bot configuration.
- Administrator and password settings.

---

## 🛠️ Technology Stack

The project uses the following technologies and libraries.

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Tkinter | Desktop graphical user interface |
| OpenCV | Computer vision and image processing |
| OpenCV Contrib | LBPH face recognition functionality |
| SQLite | Local database management |
| YOLOv8 | Object detection model integration |
| Pillow | Image processing and display |
| Matplotlib | Charts and attendance visualization |
| ReportLab | PDF report generation |
| qrcode | QR code generation |
| requests | HTTP requests and API integration |
| SMTP | Email notifications |
| Telegram Bot API | Telegram messaging integration |

### 🧠 Face Recognition

The project uses OpenCV's LBPH face recognition functionality
for facial recognition.

The application also includes a YOLOv8 model file
(`yolov8n.pt`) for object detection-related functionality.

**Note:** YOLOv8 object detection and LBPH face recognition serve
different purposes. Their exact roles depend on how they are
integrated into the application's source code.

---

## 🏗️ Project Architecture

The application is organized into separate Python modules to make
the codebase easier to understand and maintain.

```text
student-attendance-system/
│
├── backups/
├── data/
├── logs/
├── models/
├── reports/
│
├── attendance_manager.py
├── auth.py
├── config.py
├── db.py
├── face_utils.py
├── gui_app.py
├── mailer.py
├── main.py
├── phase2_tools.py
├── reports.py
├── requirements.txt
├── yolov8n.pt
└── README.md

---

## 📸 Screenshots

Explore the interface and key features of Student Attendance System 2.0.

> 📌 Add your actual application screenshots to the `screenshots/` directory and update the image paths below if necessary.

### 🔐 Login Screen

Secure administrator login interface.

![Login Screen](screenshots/login.png)

### 📊 Dashboard

Monitor attendance statistics and daily activity from a centralized dashboard.

![Dashboard](screenshots/dashboard.png)

### 👨‍🎓 Student Management

Register, update, search, and manage student information.

![Student Management](screenshots/students.png)

### 📷 Capture & Train

Capture facial samples and prepare the recognition model.

![Capture and Train](screenshots/capture-train.png)

### 📝 Attendance Management

Monitor attendance records and manage attendance sessions.

![Attendance Management](screenshots/attendance.png)

### 📈 Reports

Generate attendance summaries and export reports as PDF files.

![Reports](screenshots/reports.png)

### ⚙️ Settings

Configure application preferences and notification settings.

![Settings](screenshots/settings.png)

---

## ⚙️ Installation and Setup

Follow this guide to clone, configure, and run Student Attendance System 2.0 on your computer.

### 📋 Prerequisites

Before installing the application, make sure you have:

- 🐍 Python installed.
- 🔧 Git installed.
- 📷 A compatible webcam for live attendance.
- 💻 An operating system compatible with the application's dependencies.
- 📦 Access to the project's required files and dependencies.

**Recommended:** Windows 10 or Windows 11.

> ⚠️ Python and package versions must be compatible with the dependencies specified by the project.

### 1️⃣ Clone the Repository

Open your terminal or command prompt.

Run the following command using your actual repository URL:

```bash
git clone https://github.com/YOUR-USERNAME/student-attendance-system.git