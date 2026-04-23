from flask import Blueprint, request, jsonify
from models.auth import create_organization, organization_login, list_all_organizations
import re
import traceback

admin_bp = Blueprint("admin", __name__)

# ===============================
# Password strength validation
# ===============================
def is_strong_password(password):
    return re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[\W_]).{8,}$', password)

# ===============================
# Organization Signup
# ===============================
@admin_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.json
        password = data.get("password")

        if not is_strong_password(password):
            return jsonify({
                "message": "Password must be at least 8 characters and include uppercase, lowercase, and special character"
            }), 400

        success = create_organization(
            data["name"],
            data.get("contact_number"),
            data["email"],
            data.get("address"),
            password
        )

        if not success:
             return jsonify({"message": "Username already exists"}), 400

        return jsonify({"message": "Organization registered successfully"}), 201
    except Exception as e:
        print("Organization Signup Error:", e)
        traceback.print_exc()
        return jsonify({"message": "Signup failed"}), 500


# ===============================
# Organization Login
# ===============================
@admin_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")
        
        org = organization_login(username, password)

        if org:
            return jsonify({
                "message": "Organization login successful",
                "username": org["username"],
                "role": "admin" # Keeping role as 'admin' for frontend compatibility
            }), 200

        return jsonify({"message": "Invalid credentials"}), 401
    except Exception as e:
        print("Organization Login Error:", e)
        return jsonify({"message": "Login failed"}), 500


# ===============================
# List Organizations
# ===============================
@admin_bp.route("/list", methods=["GET"])
def list_organizations():
    try:
        organizations = list_all_organizations()
        return jsonify(organizations), 200
    except Exception as e:
        print("Error listing organizations:", e)
        return jsonify([]), 500
