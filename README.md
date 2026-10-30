# 🔬 IntegrityShield – Biometric Liveness Detection Exam System

IntegrityShield is an AI-powered web-based online examination proctoring system developed to improve the security, fairness, and integrity of digital examinations. It uses computer vision, artificial intelligence, and real-time audio monitoring to detect suspicious activities during online exams.

The application monitors students through their webcam and microphone, automatically detecting activities such as multiple faces appearing in the camera frame, absence of the student, suspicious head movements, mobile phone usage, and unusual speech or loud audio. It uses Python and Flask for backend processing, OpenCV and YOLOv8 for AI-based detection, and HTML, CSS, and JavaScript for the frontend.

The system provides separate interfaces for students and teachers. Teachers can create time-restricted examination rooms and share unique exam codes with students, while students can join exams and access a live monitoring dashboard. At the end of each examination, the system generates session logs and Excel reports containing violation details and attention scores.

## 🎯 Objectives

- Develop an AI-powered web-based platform for secure online examination monitoring.
- Automate the detection of suspicious activities during online examinations.
- Monitor student presence using real-time face detection.
- Detect multiple faces appearing in the webcam frame.
- Identify suspicious head movements and sideways looking behaviour.
- Detect mobile phone usage using the YOLOv8 object detection model.
- Monitor microphone audio levels to identify unusual speech or loud talking.
- Implement time-restricted examination sessions.
- Generate violation records with timestamps.
- Calculate and display student attention scores.
- Generate automated examination reports in JSON and Excel formats.
- Reduce the need for continuous manual invigilation.

## ✨ Features

- **Face Detection:** Detects whether the student is present in the webcam frame and identifies when multiple faces appear.
- **Gaze and Head Movement Detection:** Monitors eye and head movements to identify suspicious sideways looking behaviour.
- **Mobile Phone Detection:** Uses the YOLOv8 object detection model to identify mobile phones appearing in the camera frame.
- **Speech Detection:** Uses the browser's Web Audio API to monitor microphone volume and identify unusually loud audio.
- **Time-Locked Examination:** Allows students to join an examination only during the time window configured by the teacher.
- **Exam Room Creation:** Allows teachers to create examination rooms with exam title, subject, date, start time, end time, and optional password.
- **Unique Exam Code:** Generates a six-character examination code that teachers can share with students.
- **Student Registration:** Allows students to join an examination using their name and examination code.
- **Live Monitoring Dashboard:** Displays webcam footage, examination countdown, violation alerts, and monitoring statistics.
- **Real-Time Violation Alerts:** Displays detected suspicious activities during the examination.
- **Attention Score:** Displays a student attention score based on recorded monitoring events.
- **Automatic Session Management:** Ends examination sessions automatically when the scheduled time expires.
- **JSON Session Logs:** Saves examination session information and violation records in JSON format.
- **Excel Report Generation:** Generates downloadable Excel reports containing examination summaries and violation details.
- **Teacher Control Panel:** Allows teachers to create examination rooms, view examination sessions, and download reports.
- **Real-Time Communication:** Uses Flask-SocketIO to transmit webcam frames and monitoring events between the browser and backend.

## 🛠️ Technologies Used

| Technology | Purpose |
| ---------- | ------- |
| Python | Backend programming and AI processing |
| Flask | Building the web server and handling API requests |
| Flask-SocketIO | Real-time communication between frontend and backend |
| Flask-CORS | Enabling cross-origin communication |
| OpenCV | Face detection, image processing, and movement analysis |
| YOLOv8 | Detecting mobile phones in webcam frames |
| NumPy | Processing image data and numerical operations |
| openpyxl | Generating and formatting Excel reports |
| dlib | Optional face detection using HOG-based methods |
| Eventlet | Supporting asynchronous Socket.IO communication |
| HTML5 | Structuring the frontend pages |
| CSS3 | Designing the user interface and dark theme |
| JavaScript | Handling webcam access, audio monitoring, and frontend functionality |
| Socket.IO JavaScript Client | Connecting the browser with the Flask-SocketIO server |
| Web Audio API | Monitoring microphone audio levels |
| Canvas API | Capturing webcam frames for backend processing |
| Fetch API | Sending HTTP requests to Flask endpoints |

## 🏗️ System Architecture

The application follows a client-server architecture in which the browser handles user interaction and media capture, while the Python Flask backend performs monitoring and AI-based detection.

- **Frontend Layer:** Uses HTML, CSS, and vanilla JavaScript to provide student and teacher interfaces.
- **Student Interface:** Allows students to enter examination details and access the live monitoring dashboard.
- **Teacher Interface:** Provides functionality for creating examination rooms, viewing sessions, and downloading reports.
- **Media Capture Layer:** Uses the browser's Webcam API and Web Audio API to capture video and monitor microphone volume.
- **Communication Layer:** Uses Fetch API for HTTP requests and Flask-SocketIO for continuous real-time communication.
- **Detection Layer:** Uses OpenCV for face and movement analysis and YOLOv8 for mobile phone detection.
- **Session Management Layer:** Manages examination rooms, student sessions, time restrictions, and violation records.
- **Reporting Layer:** Generates JSON session logs and formatted Excel reports using openpyxl.

## ⚙️ Core Operations

The system performs the following important examination monitoring operations:

### 1. Examination Room Creation

- Teacher opens the teacher control panel.
- Enters the examination title and subject.
- Provides the examination date.
- Sets the starting and ending time.
- Optionally configures an examination password.
- Creates the examination room.
- The system generates a unique six-character examination code.

### 2. Student Examination Registration

- Student opens the examination landing page.
- Enters the six-character examination code.
- Provides their name.
- Enters the optional examination password, if required.
- The system checks the examination details and scheduled time.
- Student joins the examination session if the conditions are satisfied.

### 3. Webcam Monitoring

- The browser requests webcam permission.
- Captures the live video stream.
- Displays the webcam feed on the monitoring dashboard.
- Uses an invisible HTML canvas to capture individual video frames.
- Sends captured frames to the Python backend through Socket.IO.
- The backend processes the frames using computer vision techniques.

### 4. Face and Movement Detection

- Detects whether the student is visible.
- Counts the number of faces in the camera frame.
- Identifies situations where multiple faces appear.
- Analyses head orientation and eye movement.
- Identifies suspicious sideways head movements.
- Generates violation alerts when configured conditions are met.

### 5. Mobile Phone Detection

- Receives webcam frames from the frontend.
- Processes the frames using the YOLOv8 model.
- Detects mobile phones using the COCO object detection class for cell phones.
- Generates a phone detection violation when the detection conditions are satisfied.

### 6. Audio Monitoring

- Accesses the microphone through browser permissions.
- Uses the Web Audio API to analyse audio volume.
- Monitors unusual loud audio levels.
- Generates speech-related violation alerts when configured thresholds are exceeded.

### 7. Violation Tracking and Attention Score

- Records detected violations during the examination.
- Stores violation types and timestamps.
- Updates the monitoring dashboard with violation information.
- Displays the total number of violations.
- Tracks monitoring statistics and attention score.

### 8. Automatic Examination Reporting

- Ends the examination when the scheduled duration expires.
- Finalizes the student monitoring session.
- Saves session information in JSON format.
- Generates an Excel report using openpyxl.
- Provides teachers with an option to download examination reports.

## 🔌 Communication and API Operations

The application uses two communication methods to connect the frontend and backend.

### 1. HTTP Communication – Fetch API

Used for one-time operations such as:

- Creating examination rooms.
- Retrieving examination information.
- Joining examination sessions.
- Fetching session details.
- Downloading examination reports.

### 2. Real-Time Communication – Flask-SocketIO

Used for continuous communication between the browser and Python backend.

- Sending webcam frames.
- Receiving monitoring updates.
- Transmitting violation information.
- Updating the live examination dashboard.

### Important API Endpoints

The following endpoints are documented in the project guides:

| Method | Endpoint | Operation |
| ------ | -------- | --------- |
| GET | `/` | Display student landing page |
| GET | `/teacher` | Display teacher control panel |
| GET | `/monitor?session_id=...` | Open student monitoring dashboard |
| POST | `/api/session/join` | Join an examination session |
| GET | `/api/report/SESSION_ID/download` | Download the examination Excel report |

*Note: Additional endpoints and Socket.IO event names should be documented according to the actual implementation in app.py.*

## 🤖 AI and Computer Vision Modules

The system integrates multiple computer vision and monitoring techniques.

### 1. Face Detection

- Uses OpenCV Haar Cascade classifiers for detecting faces.
- Checks student presence in the camera frame.
- Counts detected faces to identify multiple-person situations.
- Can optionally use dlib for HOG-based face detection.

### 2. Gaze and Movement Analysis

- Uses eye and pupil-related image processing.
- Analyses head orientation and eye movement.
- Detects suspicious sideways looking behaviour.
- Does not treat ordinary downward-looking behaviour as a violation according to the implemented detection rules.

### 3. YOLOv8 Object Detection

- Uses the YOLOv8 Nano model (`yolov8n.pt`).
- Detects mobile phones in webcam frames.
- Uses COCO class ID 67 for mobile phone detection.
- Processes captured images to identify prohibited objects.

### 4. Audio Monitoring

- Uses the browser's Web Audio API.
- Reads microphone audio levels.
- Monitors loud or unusual audio activity.
- Generates speech-related alerts based on configured thresholds.

## 🗄️ Data Storage and Report Management

The current implementation uses Python dictionaries to maintain examination room and session information during runtime.

### 1. In-Memory Data

- `exam_rooms` – Stores examination room information.
- `sessions` – Stores student examination session information.

The current implementation does not use a database for session management. Therefore, in-memory session data is lost when the Flask server restarts.

### 2. JSON Session Logs

The application saves examination session information and violation records in JSON files.

These records include relevant session details, monitoring events, and violation information.

### 3. Excel Reports

The application uses openpyxl to generate formatted Excel reports.

Reports include:

- Examination session summary.
- Student information.
- Total violations.
- Violation details.
- Timestamps.
- Attention score.

## 🚀 Setup and Installation

### Prerequisites

- Python 3.9–3.12
- pip
- Visual Studio Code
- Webcam
- Microphone
- Google Chrome or another modern browser
- Git

### 1. Clone the Repository

```bash
git clone <your-github-repository-url>
```

Navigate to the project directory:

```bash
cd proctor_ai
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The main dependencies include:

```text
Flask
Flask-SocketIO
Flask-CORS
python-socketio
python-engineio
eventlet
opencv-python
numpy
ultralytics
openpyxl
Pillow
```

### 4. Configure Model Files

Make sure the YOLOv8 model weights file is available in the project directory:

```text
yolov8n.pt
```

If optional dlib-based detection is enabled, configure its required model files in the appropriate directory.

### 5. Start the Application

Run the Flask application:

```bash
python app.py
```

Alternatively, use the provided launcher script on Windows:

```bash
start.bat
```

### 6. Open the Application

Open your browser and visit:

`http://localhost:5000`

The student landing page will appear.

The teacher control panel is available at:

`http://localhost:5000/teacher`

Allow webcam and microphone permissions when prompted.

## 📁 Project Structure

```text
IntegrityShield/
│
├── app.py
├── detector.py
├── yolov8n.pt
├── requirements.txt
│
├── start.bat
├── start.sh
│
├── templates/
│   ├── index.html
│   ├── dashboard.html
│   └── teacher.html
│
├── static/
│   └── models/
│
├── logs/
│
├── reports/
│
└── README.md
```

**Folder and file descriptions:**

- `app.py` – Main Flask application, API routes, Socket.IO events, session management, and report generation.
- `detector.py` – Contains the AI-based face, eye, gaze, and phone detection logic.
- `yolov8n.pt` – Pre-trained YOLOv8 Nano model weights.
- `requirements.txt` – Contains Python dependencies.
- `templates/index.html` – Student examination landing and joining page.
- `templates/dashboard.html` – Live student monitoring dashboard.
- `templates/teacher.html` – Teacher examination management panel.
- `static/models/` – Optional dlib model files.
- `logs/` – Stores automatically generated JSON session logs.
- `reports/` – Stores generated Excel examination reports.
- `start.bat` – Windows application launcher.
- `start.sh` – Linux/macOS application launcher.

*The structure represents the documented project organization. Adjust it if your final repository contains additional files or different folder names.*

## 🔮 Future Scope

- Implement database integration using MySQL for permanent examination and session storage.
- Introduce advanced biometric face verification.
- Improve liveness detection to prevent photo and recorded-video spoofing.
- Implement more advanced gaze tracking and head-pose estimation.
- Improve voice and speech analysis using speech recognition techniques.
- Add enhanced screen activity monitoring.
- Introduce student authentication and administrator access control.
- Develop detailed examination analytics and performance dashboards.
- Improve violation classification and detection accuracy.
- Add cloud-based deployment for remote examination management.
- Implement historical examination records and report management.
- Introduce configurable monitoring rules for different examination types.

## 🎓 Project Information

**Project Name:** IntegrityShield – Biometric Liveness Detection Exam System  
**Student:** Lakshay  

---

**IntegrityShield — Enhancing Online Examination Integrity Through Artificial Intelligence, Computer Vision, and Real-Time Monitoring.**