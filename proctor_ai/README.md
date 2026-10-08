# 🛡️ IntegrityShield — AI Exam Proctoring System

A full-stack AI exam proctoring system using **Python + Flask + OpenCV + YOLOv8**.  
Real-time webcam monitoring with face detection, gaze tracking, phone detection, and audio monitoring.

---

## 🏗️ Project Structure

```
proctor_ai/
├── app.py              ← Flask web server + Socket.IO
├── detector.py         ← All AI detection (face, eyes, YOLO)
├── requirements.txt    ← Python packages
├── start.sh            ← One-click start (Linux/macOS)
├── start.bat           ← One-click start (Windows)
├── templates/
│   ├── index.html      ← Landing / session setup page
│   └── dashboard.html  ← Live monitoring dashboard
├── static/
│   └── models/         ← Place dlib .dat file here
└── logs/               ← Session JSON reports saved here
```

---

## ✅ System Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.9 – 3.12 |
| pip | latest |
| Webcam | any USB or built-in |
| Microphone | any input device |
| RAM | 4 GB+ recommended |
| OS | Windows 10+, macOS 11+, Ubuntu 20.04+ |

---

## 🚀 STEP-BY-STEP SETUP

---

### STEP 1 — Install Python

Download from https://www.python.org/downloads/ (choose 3.10 or 3.11)

**Windows:** During install, ✅ check **"Add Python to PATH"**

Verify:
```bash
python --version       # Windows
python3 --version      # macOS / Linux
```

---

### STEP 2 — Download / Clone This Project

```bash
# If you have git:
git clone <your-repo-url>
cd proctor_ai

# OR just download the ZIP and extract it, then:
cd proctor_ai
```

---

### STEP 3 — Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

---

### STEP 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, OpenCV, YOLOv8, and all required packages.

> ⏳ First run may take 2–5 minutes (downloads ~100 MB of packages)

---

### STEP 5 — Platform-specific: PyAudio

PyAudio requires **PortAudio** system library.

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Ubuntu / Debian:**
```bash
sudo apt-get update
sudo apt-get install python3-dev portaudio19-dev
pip install pyaudio
```

**Windows:**
```bash
# Option A — pip (usually works):
pip install pyaudio

# Option B — if that fails, download pre-built wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# Then: pip install PyAudio-0.2.11-cp311-cp311-win_amd64.whl
```

> **If PyAudio fails:** The system still works — audio monitoring uses
> the browser's Web Audio API instead, so PyAudio is optional.

---

### STEP 6 — (Optional) Install dlib for Better Face Detection

dlib gives more accurate face detection and enables 68-point landmark gaze tracking.

**Prerequisites for dlib:**
```bash
# macOS:
brew install cmake

# Linux:
sudo apt-get install cmake build-essential

# Windows: Install CMake from https://cmake.org/download/
#          AND Visual Studio Build Tools from https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**Install dlib:**
```bash
pip install dlib
```

> ⏳ dlib compiles from source — takes 5–15 minutes.

**Then install imutils:**
```bash
pip install imutils
```

**Uncomment in requirements.txt:** Remove the `#` before `dlib` and `imutils`.

> ✅ The system works without dlib (falls back to Haar cascades).

---

### STEP 7 — (Optional) Download 68-Point Landmark Model

For advanced gaze tracking, download the dlib landmark model:

1. Download: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
2. Extract the `.dat` file
3. Place it at: `static/models/shape_predictor_68_face_landmarks.dat`

---

### STEP 8 — YOLOv8 Model

YOLOv8 downloads automatically on first run (~6 MB). Or pre-download:
```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); print('YOLO ready!')"
```

---

## ▶️ RUNNING THE SYSTEM

### Quick Start (Recommended)

```bash
# Linux / macOS:
chmod +x start.sh
./start.sh

# Windows:
start.bat
```

### Manual Start

```bash
# Activate virtual environment first!
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows

# Run the server
python app.py
```

### Expected Output:

```
============================================================
  🛡️  AI EXAM PROCTORING SYSTEM
============================================================
  Server: http://localhost:5000
  Models: Haar✓ | dlib✓ | YOLOv8✓ | Landmarks✓
============================================================
```

---

## 🌐 USING THE SYSTEM

### 1. Open the browser
Go to: **http://localhost:5000**

### 2. Start a Session
- Enter **Student Name** and **Exam Name**
- Click **"Begin Proctoring"**

### 3. Allow Camera + Microphone
- Click **"Allow Camera & Mic"** in the dashboard
- Browser will ask for permissions → click **Allow**

### 4. Monitoring is Active
The AI begins analyzing:
- 📸 2 frames per second (webcam → server → detection → response)
- 🎙️ Audio levels every 800ms (browser Web Audio API)

### 5. Violations appear in real-time
| Type | Trigger | Severity |
|------|---------|---------|
| `MULTIPLE_FACES` | > 1 face detected | 🔴 HIGH |
| `PHONE_DETECTED` | Mobile phone in frame | 🔴 HIGH |
| `NO_FACE` | No face for 0.5s | 🟡 MEDIUM |
| `LOOKING_AWAY` | Eyes not visible | 🟡 MEDIUM |
| `SPEECH_DETECTED` | Microphone activity | 🟡 MEDIUM |

### 6. End Session
- Click **"⏹ End Exam"**
- Report is saved to `logs/session_XXXX.json`

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Landing page |
| GET | `/monitor?session_id=X&name=Y&exam=Z` | Dashboard |
| POST | `/api/session/create` | Create new session |
| POST | `/api/session/<id>/end` | End session + save log |
| GET | `/api/session/<id>` | Get session details |
| GET | `/api/sessions` | List all sessions |
| WS | Socket.IO `/` | Real-time frame analysis |

---

## 🔧 Troubleshooting

### "Camera access denied"
- Chrome: Click the 🔒 lock icon → allow Camera and Microphone
- Firefox: Click the camera icon in address bar → Allow

### "Server error — is the backend running?"
- Make sure `python app.py` is running
- Check terminal for errors
- Verify you're at http://localhost:5000 (not 5001 or 3000)

### "YOLO model not found"
```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### "dlib fails to install"
- Install CMake first
- On Windows: install Visual Studio Build Tools
- Or skip dlib — system works fine with Haar cascades

### "PyAudio install fails"
- Install portaudio system library first
- Or skip it — audio uses browser Web Audio API

### "Port 5000 already in use"
Edit `app.py`, change last line port to `5001`:
```python
socketio.run(app, host='0.0.0.0', port=5001, ...)
```

### "Module not found: audioop" (Python 3.13+)
```bash
pip install audioop-lts
```

---

## 📦 Complete install (Ubuntu/Debian — copy-paste)

```bash
# System dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv cmake build-essential \
  python3-dev portaudio19-dev

# Project setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install dlib imutils  # optional but recommended

# Run
python app.py
```

---

## 📦 Complete install (macOS — copy-paste)

```bash
# Prerequisites (install Homebrew first: https://brew.sh)
brew install python cmake portaudio

# Project setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyaudio dlib imutils  # optional

# Run
python app.py
```
