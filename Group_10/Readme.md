# AutiWise - A Comprehensive Digital Toolkit for Individuals with Autism Spectrum Disorder

## 👥 Group Members

* Arya Patil
* Nisha Patel
* Prachi Pawar
* Renuka Udugade

---

## 📌 Short Project Description

This project, developed as part of a **Placement Training System**, focuses on gamifying social skill development. Users engage in various practice scenarios (e.g., Library interactions, Workplace greetings) with an AI Guide.

### ✨ Key Features:

* **AI-Driven Chat Simulation:** Real-time conversation practice based on specific social scenarios.
* **Live Tone Analysis:** Utilizes NLP (TextBlob) to detect user sentiment (Positive, Neutral, Negative) for every sentence.
* **Coaching Feedback:** Provides immediate "Coach Tips" to help users refine their social approach and build rapport.
* **Gamified Dashboard:** A Gen-Z-friendly, stylish interface featuring progress tracking and interactive task cards.
* **Clinical Insight:** Logs user reflections and progress for therapist review.

---

## 🛠️ Technology Stack

* **Frontend:** HTML5, CSS3 (Modern UI with Glassmorphism), JavaScript (ES6+)
* **Backend:** Python 3.10+, Flask
* **NLP Library:** TextBlob (for Polarity and Subjectivity analysis)
* **Storage:** Local SDK / JSON Data Handling

---

## 🚀 How to Run the Project

### 1️⃣ Prerequisites

Ensure you have **Python 3.10 or higher** installed. You will also need `pip`.

---

### 2️⃣ Install Dependencies

Open terminal in project folder and run:

```bash
pip install flask textblob
```
---

### 3️⃣ Download NLP Corpora

TextBlob requires specific language data to perform analysis:

```bash
python -m textblob.download_corpora
```
---

### 4️⃣ Start the Server

Run the Flask application:

```bash
python app.py
```
---

### 5️⃣ Open in Browser
```bash
http://127.0.0.1:5000
```
---

