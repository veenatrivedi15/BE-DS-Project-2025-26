# 🚦 VISTA – Vision Integrated Smart Traffic Automation

VISTA is an **AI-powered smart traffic management system** designed to automate traffic signal control, analyze real-time traffic conditions, detect violations and accidents, and improve overall road safety using computer vision and intelligent decision-making.

---

## 👥 Group Members

* **Sahil Gorde** (22107035)
* **Siddhi Patwardhan** (22107033)
* **Varad Chaudhari** (22107053)
* **Kisankumar Jena** (22107049)

---

## 📝 Project Description

The **Vision-Integrated Smart Traffic Automation (VISTA)** project addresses urban congestion by replacing static timers with a dynamic, AI-driven approach. Utilizing **YOLOv11** for real-time vehicle detection and **Reinforcement Learning (PPO)** for decision-making, the system optimizes signal timings based on live density. Beyond signal control, VISTA integrates safety features such as **Crash Detection**, **Red-Light Violation Detection**, and **Pedestrian Crossing Monitoring**, providing a comprehensive 4-way intersection management solution through a centralized dashboard.

---

## 🚀 How to Run the Project

Follow these steps to set up and run the VISTA system on your local machine:

### 1. Prerequisites
Ensure you have **Python 3.9+** installed. You will also need a GPU (recommended) for optimal YOLO and RL performance.

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/VISTA.git
cd VISTA
```

### 3. Install Dependencies
Install the required libraries including PyTorch, OpenCV, and Flask:
```bash
pip install -r requirements.txt
```

### 4. Set Up Models
Ensure the pre-trained weights for **YOLOv11** and the **PPO Agent** are placed in the `models/` directory.

### 5. Launch the System
Run the main application script (Flask/FastAPI backend):
```bash
python app.py
```

### 6. Access the Dashboard
Open your web browser and navigate to:
```
http://localhost:5000
```

---

## 🛠️ Tech Stack

* **Computer Vision:** YOLOv11, DeepSORT, OpenCV
* **AI & Decision-Making:** Reinforcement Learning (PPO), LLM (LLaMA, Phi-3)
* **Backend:** Flask, FastAPI
* **Data Science:** Python, NumPy, Pandas, PyTorch, TensorFlow
* **Frontend:** HTML, CSS, JavaScript

---

## 🔍 Key Features

* **Dynamic Signal Control:** Optimizes green light duration based on vehicle count.
* **Incident Detection:** Real-time identification of crashes and signal violations.
* **Emergency Mode:** Prioritizes emergency vehicles using AI agent overrides.
* **Pedestrian Safety:** Monitors waiting queues to integrate pedestrian priority.
* **Transparency:** Maintains a detailed decision log for every signal change.

