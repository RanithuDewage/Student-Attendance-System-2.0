# Student Attendance System 2.0

A smart **desktop-based attendance management system** built with **Python**, designed to automate student attendance using **face recognition**, live monitoring, reporting, backup/restore, and notification features.

Developed by **Team NoCtraX**

---

## Overview

**Student Attendance System 2.0** is a modern and efficient attendance solution developed to replace traditional manual attendance methods.  
The system provides a complete workflow for:

- student registration
- face sample collection
- model training
- live attendance marking
- daily/monthly reporting
- PDF export
- database backup and restore
- email and Telegram notifications
- secure admin management
- customizable system settings

The project combines **computer vision**, **database management**, **graphical user interface development**, and **automation** into one practical application suitable for educational institutions and academic environments.

---

## Key Features

### Secure Admin Login
- Protected login interface for authorized access
- Remember username option
- Secure credential-based authentication

### Dashboard with Live Statistics
- Total Students
- Present
- Late
- Absent
- Unknown Faces
- Today’s status overview
- Weekly attendance summary

### Student Management
- Add new students
- Update student details
- Delete student records
- Search students
- Manage active/inactive status
- Store profile photos and batch information

### Face Capture and Training
- Capture face samples from camera
- Add photos from file
- Train recognition model
- Reload model when needed
- Generate QR code fallback support

### Live Attendance Marking
- Real-time face recognition
- Automatic attendance marking
- Status categories:
  - Present
  - Late
  - Absent
  - Unknown
- Session-based attendance support

### Attendance Records
- View daily attendance logs
- Filter by date, session, and status
- Search attendance records
- Manual attendance marking
- Delete selected rows
- Live attendance counters

### Reports
- Daily attendance report
- Monthly attendance report
- Monthly summary table
- PDF export support

### Backup and Restore
- Create full system backup
- Restore database and related files from backup

### Notifications
- Email support using SMTP
- Telegram bot integration
- Test message support

### Settings and Customization
- Theme selection
- Class start time
- Grace minutes
- Camera index
- Face threshold
- Current session
- Unknown face beep
- Liveness check
- QR fallback
- SMTP email settings
- Telegram settings
- Admin account management
- Password change support

---

## Technology Stack

- **Python**
- **Tkinter** / Custom GUI
- **OpenCV**
- **OpenCV Contrib (LBPH Face Recognition)**
- **SQLite**
- **Matplotlib**
- **Pillow**
- **ReportLab**
- **qrcode**
- **requests**
- **SMTP Email**
- **Telegram Bot API**
- **YOLOv8** (`yolov8n.pt`)

---

## Project Structure

```bash
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

## File Description

- main.py – Main entry point of the application
- gui_app.py – Graphical user interface logic
- auth.py – Authentication and login handling
- db.py – Database connection and queries
- attendance_manager.py – Attendance processing logic
- face_utils.py – Face detection and recognition utilities
- mailer.py – Email handling
- reports.py – Report generation and export
- phase2_tools.py – Additional supporting tools
- config.py – Configuration and settings
- yolov8n.pt – YOLOv8 model file
- requirements.txt – Python dependencies

## Screenshots

- Login Screen
- Dashboard
- Student Management
- Capture & Train
- Attendance
- Reports
- Settings

## Installation

1. Clone the Repository
git clone https://github.com/your-username/student-attendance-system.git
cd student-attendance-system

2. Create a Virtual Environment
python -m venv .venv

3. Activate the Virtual Environment
Windows
.venv\Scripts\activate
macOS / Linux
source .venv/bin/activate

4. Install Dependencies
pip install -r requirements.txt

5. Run the Application
python main.py

## Configuration

Before running the project, make sure the following settings are configured properly:

- Camera index
- Face threshold
- Class start time
- Grace minutes
- Email sender details
- Telegram bot token
- Telegram chat ID
- Session name
- Theme preference

## Important Security Note

Do not commit sensitive information such as:

- email passwords
- Telegram bot tokens
- API keys
- admin passwords
- Use local configuration files or environment variables for secret values.

## Usage Guide

1. Login
Open the application and sign in using admin credentials.

2. Manage Students
Go to the Students tab and add student details such as:

- Student ID
- Name
- Email
- Department
- Batch
- Profile Photo
3. Capture Face Samples
Use the Capture & Train tab to:

collect face images from the camera
upload photos from file
generate QR codes if required
4. Train the Model
Train the recognition model after collecting enough samples for each student.

5. Start Attendance
Open the Attendance tab and start live preview.
The system will detect faces and mark attendance automatically.

6. Review Reports
Use the Reports tab to:

generate daily reports
generate monthly reports
export monthly PDF files
7. Backup and Restore
Use the backup tools to secure your data and restore it whenever needed.

8. Update System Settings
Use the Settings tab to configure:

theme
class time
camera
email
Telegram
admin accounts
password changes

##Core Modules

Dashboard
Shows live system statistics and attendance analytics.

Students
Handles student record creation, editing, searching, and deletion.

Capture & Train
Manages face sample collection, photo uploads, model training, and QR generation.

Attendance
Supports live attendance marking, manual updates, filtering, and record management.

Reports
Generates daily/monthly reports and monthly PDF summaries.

Settings
Controls system configuration, admin management, notifications, and custom preferences.

## Features in Summary

Secure admin login
Student record management
Face sample capture
Face recognition-based attendance
Live dashboard analytics
Manual and automatic attendance marking
Attendance filtering and search
Monthly PDF report export
Backup and restore system
Email and Telegram alerts
Theme customization
Modular code architecture

## Future Enhancements

Possible future improvements include:

Web-based version
Cloud database integration
Mobile companion app
SMS notifications
Multi-camera support
Excel export
Role-based user access
Improved AI recognition accuracy
Real-time analytics dashboard

## Security & Privacy

This system is intended for educational and internal use.

Best practices:

Do not upload real passwords or bot tokens to GitHub
Keep backups in a secure location
Restrict admin access
Review logs regularly
Remove test data before public release

## Acknowledgements

Special thanks to the technologies and libraries that made this project possible:

Python
OpenCV
Tkinter
SQLite
Pillow
Matplotlib
ReportLab
qrcode
requests
Telegram Bot API
YOLOv8
Also thanks to Team RushX for the development and support behind this project.

## License

This project is shared for educational and demonstration purposes.

If you want to make it open source, you may add a license such as:

MIT License
Apache 2.0
GNU GPL v3

## Contact

Project Name: Student Attendance System 2.0
Team: NoCtraX

For collaboration, feedback, or improvement suggestions, feel free to connect through GitHub.