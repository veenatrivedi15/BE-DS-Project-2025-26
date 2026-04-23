from flask import Blueprint, request, jsonify
from models.auth import create_user, user_login
from models.logs import log_user_login
import re

user_bp = Blueprint("user", __name__)

def is_strong_password(password):
    return re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[\W_]).{8,}$', password)

@user_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.json

        username = data.get("username")
        contact_number = data.get("contact_number")
        password = data.get("password")

        if not username or not contact_number or not password:
            return jsonify({"message": "Missing required fields"}), 400

        if not is_strong_password(password):
            return jsonify({
                "message": "Password must be at least 8 characters and include uppercase, lowercase, and special character"
            }), 400

        success = create_user(username, contact_number, password)
        if not success:
            return jsonify({"message": "Username already exists"}), 400

        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        print("Signup Error:", e)
        return jsonify({"message": "Signup failed"}), 500


@user_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = user_login(username, password)

    if user:
        log_user_login(username)
        return jsonify({"message": "User login successful"})

    return jsonify({"message": "Invalid credentials"}), 401
