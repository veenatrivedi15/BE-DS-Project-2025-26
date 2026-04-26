from flask import Blueprint, request, jsonify, session
from datetime import datetime
# Import 'db' and your models from your main app or a shared models file
#from app import db, User 
from model import db, User, Task

tasks_bp = Blueprint('tasks', __name__)
'''
# --- Database Model (If not already in app.py) ---
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    priority = db.Column(db.String(20))
    duration = db.Column(db.Integer)  # minutes
    status = db.Column(db.String(20), default="pending") # pending, completed
    date_assigned = db.Column(db.Date, default=datetime.utcnow().date)
'''
# --- Routes ---

# 1. Therapist creates task (Voice to DB)
@tasks_bp.route("/api/tasks/create", methods=["POST"])
def create_task():
    try:
        data = request.json
        new_task = Task(
            user_id=data['user_id'],
            title=data['title'],
            category=data['category'],
            description=data['description'],
            audio_instructions=data['audio_instructions'],
            # CHANGE 'time_range' TO THE EXACT NAME IN model.py
            # If your model has no time column, remove this line or add it to model.py
            duration=data['duration'],
            status='pending'
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify({"isOk": True})
    except Exception as e:
        print(f"Error: {e}") 
        return jsonify({"isOk": False, "message": str(e)}), 500

# 2. User fetches their specific tasks
@tasks_bp.route("/api/tasks/my_tasks") # Make sure this matches the JS fetch call
def get_my_tasks():
    username = session.get("currentUser")
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"tasks": []})

    user_tasks = Task.query.filter_by(user_id=user.id).all()
    
    task_list = []
    for t in user_tasks:
        task_list.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "status": t.status,
            "audio_instructions": t.audio_instructions
        })
    return jsonify({"tasks": task_list})

# 3. User updates task status (Completing the routine)
@tasks_bp.route("/api/update_task_status/<int:task_id>", methods=["POST"])
def update_status(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json
    task.status = data.get('status')
    db.session.commit()
    return jsonify({"isOk": True})

# 4. Therapist fetches aggregate stats for Progress Reports
@tasks_bp.route("/api/reports/overall_stats")
def get_stats():
    total = Task.query.count()
    completed = Task.query.filter_by(status='completed').count()
    percentage = round((completed / total) * 100) if total > 0 else 0
    return jsonify({"progress": percentage, "total": total, "completed": completed})