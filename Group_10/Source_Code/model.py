import google.generativeai as genai
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime



# Load your API key
#API_KEY = "AIzaSyAoleA8SrPlOa0AWzGR4d9rCT17UiDt8lM"
API_KEY = "AIzaSyDoCmuZMzrDQ6w-2mzW2hdQG4oNKY28YnA"
genai.configure(api_key=API_KEY)

# List all available models
models = genai.list_models()

# Print them
print("Available Gemini models:")
for model in models:
    print(model.name)
    
# Initialize the extension without the app first
db = SQLAlchemy()
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    role = db.Column(db.String(20), default="user")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    audio_instructions = db.Column(db.Text) # Base64 audio strings are long!
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
# --- Assessment Report Table ---
class AssessmentReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    age_group = db.Column(db.String(50))
    behavior_score = db.Column(db.Integer)
    image_label = db.Column(db.String(50))
    final_risk = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- Therapist Table ---
class Therapist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    specialty = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    age_groups = db.Column(db.String(200))
    
class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('assessment_report.id'), nullable=False)
    therapist_id = db.Column(db.Integer, db.ForeignKey('therapist.id'), nullable=False)
    assignment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="active")

    # Relationships to easily fetch names in the UI
    report = db.relationship('AssessmentReport', backref='match')
    therapist = db.relationship('Therapist', backref='matches')

# --- Social Skill Assignment Table ---
class SkillAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    therapist_name = db.Column(db.String(100))
    skill_name = db.Column(db.String(100), nullable=False)
    skill_category = db.Column(db.String(50))
    difficulty_level = db.Column(db.String(20))
    description = db.Column(db.Text)
    learning_objectives = db.Column(db.Text)
    assessment_criteria = db.Column(db.Text)
    practice_scenarios = db.Column(db.Text)
    video_reference = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer)
    due_date = db.Column(db.String(50))
    status = db.Column(db.String(20), default="active")
    progress = db.Column(db.Integer, default=0) # Must exist!
    reflection = db.Column(db.Text)            # Must exist!
    practice_log = db.Column(db.Text)          # Must exist!
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
