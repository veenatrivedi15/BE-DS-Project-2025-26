from flask import Blueprint, request, jsonify, render_template, session

import google.generativeai as genai

import os

from model import db, User, SkillAssignment, Therapist, Match, AssessmentReport

from model import Match



# Use the blueprint name for all routes

social_skills_bp = Blueprint('social_skills_api', __name__)



# ---------------------- Configure Gemini ----------------------

API_KEY = "AIzaSyBbuCLlxqiOra39-jrjTcPDKTEy39PtLKA"

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")



# ---------------------- Routes ----------------------



@social_skills_bp.route("/management")
def social_skills_management():
    import app 
    @app.login_required
    def decorated():
        return render_template("social_skills_management.html")
    return decorated() # Added the () here to actually execute the function



@social_skills_bp.route('/get_my_patients')

def get_my_patients():

    # JUST ONE version of this function!

    users = User.query.filter_by(role='user').all()

    return jsonify([{"id": u.id, "name": u.full_name} for u in users])



@social_skills_bp.route("/generate_scenarios", methods=["POST"])

def generate_scenarios():

    import app

    @app.login_required

    def decorated():

        try:

            API_KEY = "AIzaSyBbuCLlxqiOra39-jrjTcPDKTEy39PtLKA"

            genai.configure(api_key=API_KEY)

           

            # --- USE FULL RESOURCE NAME ---

            # 'gemini-flash' is a new alias; v1beta often requires the full versioned name

            model_name = "models/gemini-2.5-flash"

            ai_model = genai.GenerativeModel(model_name)

            # -------------------------------



            data = request.json

            context = data.get('context', 'general setting')

           

            prompt = (
                f"Create a short (2-3 sentence) roleplay scenario for an autistic child. "
                f"Context: {context}. "
                f"Example: 'You are at a grocery store and cannot find the milk. Ask an employee for help.' "
                f"Return ONLY the scenario text."
            )
            response = ai_model.generate_content(prompt)
            # Just return the whole text as one scenario
            return jsonify({"scenarios": [response.text.strip()]})
        
        except Exception as e:
            # If 'gemini-2.5-flash' fails, print the actual available names for your key
            print("--- VERIFYING ACCESSIBLE MODELS ---")
            try:

                for m in genai.list_models():

                    if 'generateContent' in m.supported_generation_methods:

                        print(f"Available: {m.name}")

            except:

                pass

            print(f"CRITICAL AI ERROR: {str(e)}")

            return jsonify({"error": str(e)}), 500

    return decorated()



from flask import request, jsonify, session

from model import db, SkillAssignment  # Make sure these are imported!

@social_skills_bp.route("/update_assignment", methods=["POST"])
def update_assignment():
    try:
        data = request.json
        assignment_id = data.get('__backendId') or data.get('id')
        assignment = SkillAssignment.query.get(assignment_id)

        if not assignment:
            return jsonify({"isOk": False, "message": "Record not found"}), 404

        # Update the database with data from the Frontend
        assignment.progress = data.get('progress', assignment.progress)
        assignment.reflection = data.get('reflection')
        assignment.practice_log = data.get('practice_log')
        
        if assignment.progress >= 100:
            assignment.status = "completed"

        db.session.commit()
        return jsonify({"isOk": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"isOk": False, "message": str(e)})


@social_skills_bp.route('/get_assignments')
def get_assignments():
    uid = session.get('user_id')
    if not uid: return jsonify([])
    assignments = SkillAssignment.query.filter_by(user_id=uid).all()
    return jsonify([{
        "id": a.id,
        "__backendId": a.id,
        "practice_scenarios": a.practice_scenarios,
        "progress": a.progress or 0,
        "status": a.status
    } for a in assignments])

@social_skills_bp.route('/assign_skill', methods=['POST'])
def assign_skill():
    data = request.json
    try:
        new_skill = SkillAssignment(
            user_id=int(data['user_id']),
            skill_name="Social Interaction",
            practice_scenarios=data['practice_scenarios'],
            status='active',
            progress=0
        )
        db.session.add(new_skill)
        db.session.commit()
        return jsonify({"isOk": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"isOk": False, "message": str(e)})

@social_skills_bp.route("/chat_practice", methods=["POST"])

def chat_practice():

    try:

        data = request.json

        user_message = data.get('message')

        chat_history = data.get('history', [])

       

        # This is the scenario generated by therapist (e.g., "At the park", "Doctor visit")

        assigned_context = data.get('context', 'a social interaction')



        # Dynamically set instructions based on the specific assignment

        system_instruction = (

            f"Act as the other person in this social scenario: {assigned_context}. "

            f"The user is practicing social skills. Keep your replies concise and "

            f"directly related to the scene. Start by responding to the user."

        )



        chat_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=system_instruction

        )



        chat = chat_model.start_chat(history=chat_history)

        response = chat.send_message(user_message)



        return jsonify({
            "isOk": True, 
            "reply": response.text, 
            "history": [
                *chat_history,
                {"role": "user", "parts": [user_message]},
                {"role": "model", "parts": [response.text]}
            ]
        })

    except Exception as e:

        return jsonify({"isOk": False, "message": str(e)})