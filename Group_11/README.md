# Retrieval-Augmented Vision-Language Agent for CCTVs

## 👥 Group Members

- Abhimanyu Pankaj Deshmukh (22107036)
- Gauri Sasikumar Iyer (22107030)
- Siddhesh Nitin Patil (22107019)
- Ganesh Sambhaji Patil (22107045)

---

## 📌 Project Description

The use of CCTV cameras has become widespread across both public and private spaces as a key tool for ensuring safety and security. However, these systems generate massive amounts of surveillance footage that often remain underutilized, only being reviewed when an incident occurs. Analyzing such large volumes of video manually is time-consuming and inefficient.

Traditional methods rely heavily on manual inspection or timestamp-based searches, making it difficult to locate specific events within non-linear video data. This can lead to missed evidence and delays in response. As surveillance systems continue to expand, the challenge of extracting meaningful insights from video data becomes even more critical.

To address these challenges, we propose a **Retrieval-Augmented Vision-Language Agent for CCTVs** — an intelligent system that transforms passive video archives into an active, searchable, and interactive database.

It automatically detects significant events in video streams and generates textual summaries. Users can interact with the system using simple natural language queries, enabling quick retrieval of relevant information without manually scanning hours of footage.

This approach enhances usability, reduces investigation time, and enables even non-technical users to efficiently access critical insights from surveillance data.

---

## 🛠️ Tech Stack

- Python
- YOLO (Object Detection)
- DeepSORT (Object Tracking)
- FastAPI (Backend API)
- React (Frontend)
- ChromaDB (Vector Database)

---

## ▶️ How to Run the Project

## Create `.env`

GEMINI_API_KEY=your_api_key

```bash
git clone <your-repo-link>
cd <your-project-folder>

cd backend
pip install -r requirements.txt
uvicorn main:app --reload

cd frontend
npm install
npm start
```
