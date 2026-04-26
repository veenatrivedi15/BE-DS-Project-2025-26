from pyexpat import model
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
import os
from functools import wraps
#from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from model import db, User, Task,Therapist, AssessmentReport
from task_management_backend import tasks_bp
from sqlalchemy import func
from model import Match
from textblob import TextBlob
from flask import jsonify, request
#from utils import login_required, role_required

# ---------------------- Load Environment ----------------------
load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# ---------------------- Database Setup ----------------------
# This creates a file called 'autism_care.db' in your project folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///autism_care.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#db = SQLAlchemy(app)

# Initialize the database with the app instance
db.init_app(app)

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()
    

# ---------------------- Import Chatbot Blueprint ----------------------
from chatbot_backend import chatbot_bp
app.register_blueprint(chatbot_bp)

# ---------------------- Import detection Blueprint ----------------------
from asd_detection import asd_bp
app.register_blueprint(asd_bp)

from social_skills_backend import social_skills_bp
app.register_blueprint(social_skills_bp, url_prefix='/social_skills_api')

# In app.py
from task_management_backend import tasks_bp
app.register_blueprint(tasks_bp)

# ---------------------- Login Required Decorator ----------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "currentUser" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------- Role Check Decorator ----------------------
def role_required(role):
    """Ensure user has correct role (user/admin)."""
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("userType") != role:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# ---------------------- API to Save Reports ----------------------
@app.route("/api/save_report", methods=["POST"])
def save_report():
    data = request.json
    # We now capture the 'synthesis_score' which is the mathematical combined result
    new_report = AssessmentReport(
        patient_name=session.get("currentUser", "Unknown User"),
        age_group=data.get('age_group'),
        behavior_score=data.get('behavior_score'),
        image_label=data.get('image_label'),
        # final_risk now contains the descriptive summary
        final_risk=data.get('final_risk') 
    )
    db.session.add(new_report)
    db.session.commit()
    return jsonify({"status": "success", "message": "Comprehensive report saved"})

@app.route("/api/add_user", methods=["POST"])
def add_user():
    data = request.json
    new_user = User(
        full_name=data['full_name'], 
        username=data['username'], 
        password=data['password']
    )
    db.session.add(new_user)
    db.session.commit()
    return {"isOk": True}

@app.route("/api/add_therapist", methods=["POST"])
def add_therapist():
    data = request.json
    new_therapist = Therapist(
        full_name=data['full_name'], 
        username=data['username'], 
        password=data['password'],
        specialty=data['specialty'],
        experience=data['experience_years'],
        age_groups=data['age_groups']
    )
    db.session.add(new_therapist)
    db.session.commit()
    return {"isOk": True}

@app.route("/api/delete_user/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"isOk": True, "message": "User deleted"})
    return jsonify({"isOk": False, "message": "User not found"}), 404

@app.route("/api/delete_therapist/<int:therapist_id>", methods=["DELETE"])
def delete_therapist(therapist_id):
    therapist = Therapist.query.get(therapist_id)
    if therapist:
        db.session.delete(therapist)
        db.session.commit()
        return jsonify({"isOk": True, "message": "Therapist deleted"})
    return jsonify({"isOk": False, "message": "Therapist not found"}), 404


@app.route("/api/create_match", methods=["POST"])
@login_required
@role_required("admin")
def create_match():
    try:
        data = request.json
        report_id = data.get('report_id')
        therapist_id = data.get('therapist_id')

        # Check if match exists; if so, update it. If not, create it.
        match = Match.query.filter_by(report_id=report_id).first()
        if match:
            match.therapist_id = therapist_id
        else:
            new_match = Match(report_id=report_id, therapist_id=therapist_id)
            db.session.add(new_match)
        
        db.session.commit()
        return jsonify({"isOk": True, "message": "Match created successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"isOk": False, "message": str(e)}), 500

# ---------------------- Login ----------------------

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_type = request.form.get("userType")

        # 1. Basic Validation Logic
        is_valid = False
        if user_type == "admin" and password:
            username = "Admin"  # Default name for session
            is_valid = True
        elif user_type in ["user", "therapist"] and username and password:
            # Check if the user exists in the database
            if user_type == "user":
                user_obj = User.query.filter_by(username=username).first()
                if user_obj and user_obj.password == password: # Simple check, better to use hashing
                    session["user_id"] = user_obj.id  # CRITICAL: Store the numeric ID
                    session["currentUser"] = user_obj.username
                    session["userType"] = "user"
                    is_valid = True
            elif user_type == "therapist":
                ther_obj = Therapist.query.filter_by(username=username).first()
                if ther_obj and ther_obj.password == password:
                    session["user_id"] = ther_obj.id  # CRITICAL: Store the numeric ID
                    is_valid = True

        # 2. Session Initialization and Redirect
        if is_valid:
            session["currentUser"] = username
            session["userType"] = user_type

            if user_type == "user":
                return redirect(url_for("user_dashboard"))
            elif user_type == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user_type == "therapist":
                return redirect(url_for("therapist_dashboard"))
        else:
            return render_template("login.html", error="⚠️ Invalid username, password, or role selection")
            
    return render_template("login.html")


# ---------------------- User Pages ----------------------
@app.route("/user_dashboard")
@login_required
@role_required("user")
def user_dashboard():
    return render_template("user_dashboard.html", user=session.get("currentUser"))

@app.route("/autism_detection")
@login_required
@role_required("user")
def autism_detection():
    return render_template("autism_detection.html", user=session.get("currentUser"))

@app.route("/social_skills")
@login_required
@role_required("user")
def social_skills():
    return render_template("social_skills.html", user=session.get("currentUser"))

#from social_skills_backend import social_skills_bp
#app.register_blueprint(social_skills_bp)


@app.route("/task_tracker")
@login_required
@role_required("user")
def task_tracker():
    return render_template("task_tracker.html", user=session.get("currentUser"))

@app.route("/chat_session")
@login_required
def chat_session():
    return render_template("chat_session.html", user=session.get("currentUser"))

# ---------------------- Admin Pages ----------------------
@app.route("/admin_dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    # Fetch all data for the tables
    users = User.query.filter_by(role='user').all()
    therapists = Therapist.query.all()
    reports = AssessmentReport.query.all()
    matches = Match.query.all()
    
    
    # Calculate counts for the stat cards
    u_count = len(users)
    t_count = len(therapists)
    r_count = len(reports)
    # If you haven't implemented the Match table yet, set to 0
    m_count = len(matches)

    return render_template("admin_dashboard.html", 
                           users=users, 
                           therapists=therapists, 
                           reports=reports,
                           u_count=u_count,
                           t_count=t_count,
                           r_count=r_count,
                           m_count=m_count)

@app.route("/manage_users")
@login_required
@role_required("admin")
def manage_users():
    user = session.get("currentUser")
    return render_template("user-management.html", user=user)



@app.route("/task_management")
@login_required
def task_management():
    # Allow both admin and therapist to enter
    if session.get("userType") not in ["admin", "therapist"]:
        return redirect(url_for("login"))
    
    user = session.get("currentUser")
    return render_template("task-management.html", user=user)

@app.route("/api/get_users")
def get_users():
    users = User.query.filter_by(role='user').all()
    return jsonify([{"id": u.id, "full_name": u.full_name} for u in users])

@app.route("/api/get_all_tasks")
def get_all_tasks():
    # Joins Task with User to get the username for the UI
    tasks = db.session.query(Task, User).join(User).all()
    return jsonify([{
        "id": t.Task.id,
        "task_title": t.Task.title,
        "task_category": t.Task.category,
        "user_name": t.User.full_name,
        "scheduled_time": t.Task.due_date, # Map to your column name
        "duration_minutes": t.Task.duration,
        "audio_instructions": t.Task.audio_instructions, # Base64 string
        "task_description": t.Task.description,
        "created_date": t.Task.created_at.strftime('%Y-%m-%d')
    } for t in tasks])
    
@app.route('/api/data_sync')
def get_data_sync():
    from model import SkillAssignment
    # TEMPORARY: Get everything to see if database has data
    assignments = SkillAssignment.query.all()
    
    sync_data = []
    for a in assignments:
        sync_data.append({
            "id": a.id,
            "__backendId": a.id,
            "user_id": a.user_id,
            "practice_scenarios": a.practice_scenarios,
            "progress": a.progress or 0,
            "status": a.status or "active"
        })
    return jsonify(sync_data)
    
    '''
@app.route("/api/create_match", methods=["POST"])
@login_required
def create_match():
    data = request.json
    # Logic to save the match to your database
    # e.g., match = Match(user_id=data['report_id'], therapist_id=data['therapist_id'])
    # db.session.add(match)
    # db.session.commit()
    return jsonify({"isOk": True, "message": "Therapist assigned to user successfully!"})
'''
@app.route("/progress_reports")
@login_required
def progress_reports():
    if session.get("userType") not in ["admin", "therapist"]:
        return redirect(url_for("login"))

    users = User.query.filter_by(role='user').all()
    
    user_reports = []
    total_completed = 0
    total_assigned = 0  # <--- Initialize the counter

    for user in users:
        tasks = Task.query.filter_by(user_id=user.id).all()
        assigned = len(tasks)
        completed = len([t for t in tasks if t.status == 'completed'])
        
        percent = int((completed / assigned * 100)) if assigned > 0 else 0
        
        user_reports.append({
            "full_name": user.full_name,
            "initials": "".join([n[0] for n in user.full_name.split()]) if user.full_name else "U",
            "assigned": assigned,
            "completed": completed,
            "percent": percent
        })
        
        total_completed += completed
        total_assigned += assigned # <--- Calculate the total

    overall_progress = int((total_completed / total_assigned * 100)) if total_assigned > 0 else 0
    active_users_count = len(users)

    # CRITICAL: You must pass total_assigned here!
    return render_template("progress-reports.html", 
                           user_reports=user_reports,
                           overall_progress=overall_progress,
                           active_users_count=active_users_count,
                           total_assigned=total_assigned) # <--- ADD THIS LINE

@app.route("/api/tasks/update_status", methods=["POST"])
def update_task_status():
    data = request.json
    task_id = data.get('id')
    new_status = data.get('status') # 'completed' or 'pending'

    task = Task.query.get(task_id)
    if task:
        task.status = new_status
        db.session.commit() # <--- VERY IMPORTANT: The data won't save without this!
        return jsonify({"isOk": True, "message": "Updated successfully"})
    
    return jsonify({"isOk": False, "message": "Task not found"}), 404

@app.route("/api/tasks/update/<int:task_id>", methods=["POST"])
def update_task(task_id):
    data = request.json
    task = Task.query.get_or_404(task_id)
    
    if 'status' in data:
        task.status = data['status']
        db.session.commit() # <--- This is what makes the Progress Report update!
        
    return jsonify({"isOk": True})


@app.route("/social_skills_management")
@login_required
def social_skills_management():
    # Only allow Admin or Therapist to access this page
    if session.get("userType") not in ["admin", "therapist"]:
        return redirect(url_for("login"))
    
    user = session.get("currentUser")
    return render_template("social_skills_management.html", user=user)

@app.route('/social_skills_api/get_my_patients')
def get_my_patients():
    # 1. Get the ID of the therapist currently logged in
    therapist_id = session.get('user_id') 
    
    if not therapist_id:
        return jsonify([]), 401  # Unauthorized

    # 2. Query your database for patients linked to THIS therapist
    # This is an example - adjust 'Patient' and 'therapist_id' to match your Model
    my_patients = Patient.query.filter_by(therapist_id=therapist_id).all()

    # 3. Format the data for the dropdown
    return jsonify([
        {"id": p.id, "name": p.name} for p in my_patients
    ])
'''
@app.route('/social_skills_api/get_assignments')
def get_assignments():
    # Make sure we use the numeric ID from session
    uid = session.get('user_id')
    
    if not uid:
        print("DEBUG: No user_id found in session. Assignments will be empty.")
        return jsonify([])

    try:
        # Fetch all assignments for this user
        assignments = SkillAssignment.query.filter_by(user_id=uid).all()
        
        results = []
        for a in assignments:
            results.append({
                "__backendId": a.id,
                "skill_name": a.skill_name or "Social Skill",
                "practice_scenarios": a.practice_scenarios or "No scenario provided.",
                "status": a.status or "active",
                "progress": a.progress or 0,
                "difficulty": a.difficulty_level or "Beginner",
                "duration_minutes": a.duration_minutes or 10
            })
        
        print(f"DEBUG: Found {len(results)} assignments for user_id {uid}")
        return jsonify(results)
    except Exception as e:
        print(f"ERROR: Database query failed: {e}")
        return jsonify([])

    
@social_skills_bp.route('/assign_skill', methods=['POST'])
def assign_skill():
    data = request.json
    try:
        # Debug: Print what the therapist is sending
        print(f"Assigning skill to user_id: {data.get('user_id')}")
        
        new_skill = SkillAssignment(
            user_id=int(data['user_id']),
            skill_name="Social Interaction",
            practice_scenarios=data['practice_scenarios'],
            status='active',
            progress=0 # Explicitly set starting progress
        )
        db.session.add(new_skill)
        db.session.commit()
        return jsonify({"isOk": True})
    except Exception as e:
        print(f"Assignment Error: {e}")
        db.session.rollback()
        return jsonify({"isOk": False, "message": str(e)})

'''

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        
        # Call Gemini
        response = model.generate_content(user_message)
        
        return jsonify({"reply": response.text})
    except Exception as e:
        print(f"Error occurred: {e}") # This shows in your terminal
        return jsonify({"error": str(e)}), 500
    
@app.route('/social_skills_api/chat_practice', methods=['POST'])
def chat_practice():
    data = request.json
    user_message = data.get('message', '') # Convert to lowercase for easier matching

    # 1. Standard TextBlob Analysis
    analysis = TextBlob(user_message)
    pol = round(analysis.sentiment.polarity, 2)
    subj = round(analysis.sentiment.subjectivity, 2)
    # 2. Enhanced Social Logic (To make it fluctuate more)

    if any(word in user_message for word in ["hello", "hey", "hi", "how are you"]):
        tone = "Friendly Opening"
        feedback = "Good start! Using a greeting is the best way to initiate rapport."
    elif pol > 0.3:
        tone = "Highly Positive"
        feedback = "Excellent! Your enthusiasm makes the other person feel welcome."
    elif pol > 0:
        tone = "Positive"
        feedback = "Nice! You're maintaining a pleasant atmosphere."
    elif pol < 0:
        tone = "Constructive"
        feedback = "This sounds a bit negative. Try reframing it to be more neutral."
    elif subj > 0.5:
        tone = "Opinionated"
        feedback = "You're sharing a lot of feelings! Make sure to ask the other person's view too."
    else:
        tone = "Neutral/Observational"
        feedback = "Steady and calm. This is a safe way to keep the conversation going."

    return jsonify({
        "isOk": True,
        "reply": f"AI: I understand. How else can I help?", # Or your AI logic
        "detected_tone": tone,
        "coaching_feedback": feedback,
        "history": data.get('history', []) + [user_message]
    })


@app.route("/therapist_dashboard")
@login_required
@role_required("therapist")
def therapist_dashboard():
    return render_template("therapist_dashboard.html", user=session.get("currentUser"))

# ---------------------- Logout ----------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------------- Run App ----------------------
if __name__ == "__main__":
    app.run(debug=True)
