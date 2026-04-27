# 🚦 SafeRide – AI Enabled Smart Road Safety Violation Detection And Monitoring System Using Neural Vision

SafeRide is an **AI-powered road safety monitoring system** that detects traffic violations such as helmet violations, triple riding, and number plate recognition in real time using deep learning and computer vision. The system integrates live video processing, OCR-based license plate extraction, and automated challan generation to assist traffic authorities in efficient enforcement.

---

## 👥 Group Members

| Name                                                     | Roll No. |
| -------------------------------------------------------- | -------- |
| [**Sakshi Kadam**](https://github.com/Rebelbytes)        | 22107032 |
| [**Radhika Pradhan**](https://github.com/pradhanradhika) | 22107005 |
| [**Priyanka Barman**](https://github.com/PriyankaB26)    | 22107004 |
| [**Tejas Deshmukh**](https://github.com/TejasDeshmukh13) | 22107015 |

---

## 📝 Project Description

**SafeRide** deploys an AI-driven violation detection pipeline at traffic checkpoints. Using **YOLOv8** for real-time object detection, the system identifies helmet violations, triple riding, and performs **LPRNet-based** license plate recognition. Detected violations are logged and a digital **challan** is auto-generated, all accessible through a live React dashboard backed by a Django REST API.

---

## 🛠️ Tech Stack

| Layer              | Technologies                        |
| ------------------ | ----------------------------------- |
| **AI / Detection** | YOLOv8, LPRNet, OpenCV, Ultralytics |
| **Backend**        | Django, Django REST Framework       |
| **Frontend**       | React.js                            |
| **Live Streaming** | WebSocket, FFmpeg, MediaMTX (RTSP)  |
| **Language**       | Python 3.8+, Node.js 16+            |

---

## 🚀 How to Run the Project

> **Before starting:** Place `best.pt` and `best_lprnet.pth` in the root directory.

### 1. Clone the Repository

```bash
git clone https://github.com/Rebelbytes/AISAFERIDE.git
cd AISAFERIDE
```

### 2. Backend Setup

```bash
cd saferide_backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000 --noreload
```

### 3. Frontend Setup

```bash
cd saferide_frontend
npm install
npm start
```

- Backend → `http://127.0.0.1:8000/`
- Frontend → `http://localhost:3000/`

---

## 🎥 Live Streaming Setup (Optional)

> Skip this if using pre-recorded video only. Requires **MediaMTX** and **FFmpeg** installed on your system.
>
> - MediaMTX: Download from [github.com/bluenviron/mediamtx/releases](https://github.com/bluenviron/mediamtx/releases) → extract to `mediamtx/` folder in project root
> - FFmpeg: `brew install ffmpeg` (Mac) / `sudo apt install ffmpeg` (Linux) / [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) (Windows) — add to PATH

**Android Chrome only:** Go to `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, enable it, add `http://<YOUR_LAPTOP_IP>:8080`, then relaunch Chrome.

### Run Order (5 terminals)

```bash
# Terminal 1 — RTSP Server
cd mediamtx && .\mediamtx.exe

# Terminal 2 — WebSocket Bridge
python saferide_backend/rtsp/video_ws.py

# Terminal 3 — Mobile Sender Page
cd saferide_backend/rtsp && python -m http.server 8080

# Terminal 4 — Django Backend
cd saferide_backend && python manage.py runserver 0.0.0.0:8000 --noreload

# Terminal 5 — React Frontend
cd saferide_frontend && npm start
```

Then on your phone, open `http://<LAPTOP_IP>:8080/mobile_sender.html` → tap **Start Camera**.

> **Note:** `RTSP 404` errors in the Django logs before the phone starts streaming are **expected** — ignore them.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
