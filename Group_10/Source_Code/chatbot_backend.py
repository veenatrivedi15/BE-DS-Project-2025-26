# chatbot_backend.py

from flask import Blueprint, request, jsonify, session
import google.generativeai as genai
import os
from functools import wraps
from dotenv import load_dotenv

# ---------------------- Load environment variables ----------------------
load_dotenv()

chatbot_bp = Blueprint("chatbot", __name__)

# ---------------------- Configure Gemini ----------------------
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment variables")

genai.configure(api_key=API_KEY)

# ---------------------- Use a valid Gemini model ----------------------
# Recommended for text/chat: "models/gemini-2.5-flash"
model = genai.GenerativeModel("models/gemini-2.5-flash")

# ---------------------- Login Required Decorator ----------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "currentUser" not in session:
            return jsonify({"response": "You must be logged in to chat."}), 401
        return f(*args, **kwargs)
    return decorated_function


# ---------------------- Chat Endpoint ----------------------
'''
@chatbot_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    try:
        user_message = request.json.get("message", "").strip()
        if not user_message:
            return jsonify({"response": "I didn’t receive any message. Could you try again?"})

        # Generate response from Gemini
        response = model.generate_content(
            f"You are a supportive assistant for autistic individuals. "
            f"Respond clearly, calmly, and kindly.\n\nUser: {user_message}\nAssistant:"
        )

        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"response": f"⚠️ Error: {str(e)}"}), 500
'''

# ---------------------- Chat Endpoint ----------------------
@chatbot_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    try:
        user_message = request.json.get("message", "").strip()
        if not user_message:
            return jsonify({"response": "I didn’t receive any message. Could you try again?"})

        # Updated Prompt for shorter, concise answers
        # Updated Prompt for a warm, 4-6 line response
        prompt = (
            "You are a warm, kind, and supportive assistant for autistic individuals. "
            "Respond in a friendly way, ensuring your answer is roughly 4 to 6 lines long. "
            "Avoid being too blunt or short, but do not use long paragraphs. "
            f"User: {user_message}\nAssistant:"
        )

        response = model.generate_content(prompt)

        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"response": f"⚠️ Error: {str(e)}"}), 500
