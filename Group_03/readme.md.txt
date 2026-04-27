Project Title - Insuresafe-AI Powered Policy Recommendation and Customer Service Portal

Group Members:
 Avadhoot Virkar(22107064) 
 Atharva Nimkar	(22107025) 
 Chinmay Pawaskar(22107066)

Short Project Description:
“Insuresafe – AI Powered Policy Recommendation and Customer Service Portal” is an intelligent web-based insurance platform that automates key insurance processes using AI and Machine Learning. It provides personalized policy recommendations, facial verification for secure login, OCR-based document verification, and AI-based claims processing with vehicle damage detection.

The system reduces manual effort, detects fraud, improves accuracy, and speeds up the entire insurance workflow, giving both users and admins a smooth and efficient experience.

How to run the project:
🔹 1. Setup Environment
Install Python (3.8+)

Install required libraries:
pip install flask opencv-python numpy pandas pymongo easyocr

Install additional ML libraries (if used):
pip install torch torchvision ultralytics deepface

🔹 2. Database Setup
Install MongoDB
Create database collections:
users
policies
claims

🔹 3. Project Setup
Extract/download your project folder
Ensure folder structure:
app.py (main Flask file)
services/ (AI modules like face_verify, ocr_verify, claims_ai, recommender)
templates/ (HTML files)
static/ (CSS/JS/images)

🔹 4. Run the Application
Open terminal in project folder

Run:
python app.py

Server will start:
http://127.0.0.1:5000/

🔹 5. Use the System
Register/Login as user
Upload selfie → Facial Verification
Upload Aadhaar → OCR Verification
Get policy recommendations
Submit claim → AI processing