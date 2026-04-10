from flask import Flask, render_template, request, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
from google.genai import types
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import sqlite3
import io
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"   # 🔥 REQUIRED

# ================= LOGIN SETUP =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page"

class User(UserMixin):
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role   # 🔥 ADD THIS

def get_db():
    return sqlite3.connect("db.sqlite3")

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email, role FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    conn.close()

    if user:
        return User(user[0], user[1], user[2])
    return None

# ================= AUTH ROUTES =================

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    password = generate_password_hash(data["password"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users (name,email,password) VALUES (?,?,?)",
        (data["name"], data["email"], password)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Registered"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id,email,password,role FROM users WHERE email=?",
        (data["email"],)
    )

    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user[2], data["password"]):
        login_user(User(user[0], user[1], user[3]))
        return jsonify({"redirect": "/"})

    return jsonify({"message": "Invalid credentials"}), 401

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"})

# ================= PAGES =================

@app.route("/")
@login_required   # 🔥 ONLY CHANGE HERE
def index():
    return render_template("index.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/lawyer-dashboard")
@login_required
def lawyer_dashboard():
    if current_user.role != "lawyer":
        return "Unauthorized", 403
    return render_template("lawyer.html")


@app.route("/lawyer/documents")
@login_required
def lawyer_docs():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    cur.execute("SELECT id, issue, draft FROM documents WHERE status='pending'")
    docs = cur.fetchall()

    conn.close()
    return jsonify({"documents": docs})

@app.route("/lawyer/verify", methods=["POST"])
@login_required
def verify_doc():
    data = request.json

    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    cur.execute("""
        UPDATE documents
        SET status=?, lawyer_comment=?
        WHERE id=?
    """, (data["status"], data["comment"], data["doc_id"]))

    conn.commit()
    conn.close()

    return jsonify({"message": "Updated"})



# ================= YOUR ORIGINAL AI CODE =================

SYSTEM_PROMPT = """
You are an expert Indian Legal Assistant AI specializing in drafting legal documents under the Indian legal framework.
You always operate in two distinct stages for every user request.

Stage 1:
- Output ONLY the name of the most appropriate legal document.

Stage 2:
- Output ONLY the fully drafted legal document.

Rules:
- No conversational text
- No explanations
- No markdown
- No extra commentary
- Cite relevant Indian Acts and Sections
- Produce a complete, ready-to-use legal document
"""

client = genai.Client(api_key="AIzaSyDW7ITG9Qa3Q4ROuC9CssyQ4Whs1i03dUc")

def build_user_prompt(issue, stage):
    return f"""
STAGE: {stage}
User Issue:
{issue}
"""

def generate_ai(issue, stage):
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=build_user_prompt(issue, stage))]
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            system_instruction=[types.Part.from_text(text=SYSTEM_PROMPT)]
        )
    )
    return response.text

@app.route("/stage1", methods=["POST"])
@login_required   # 🔥 PROTECTED
def stage1():
    issue = request.json["issue"]
    doc_name = generate_ai(issue, stage=1)
    return jsonify({"document_name": doc_name})

@app.route("/stage2", methods=["POST"])
@login_required   # 🔥 PROTECTED
def stage2():
    issue = request.json["issue"]
    draft = generate_ai(issue, stage=2)
    return jsonify({"draft": draft})

@app.route("/export/docx", methods=["POST"])
@login_required
def export_docx():
    text = request.json["text"]
    doc = Document()

    for line in text.split("\n"):
        doc.add_paragraph(line)

    file = io.BytesIO()
    doc.save(file)
    file.seek(0)

    return send_file(file, as_attachment=True, download_name="legal_document.docx")

@app.route("/save_document", methods=["POST"])
@login_required
def save_document():
    data = request.json

    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO documents (user_id, issue, draft, status)
        VALUES (?, ?, ?, 'pending')
    """, (current_user.id, data["issue"], data["draft"]))

    conn.commit()
    conn.close()

    return jsonify({"message": "Saved"})

@app.route("/my-documents")
@login_required
def my_documents():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()

    cur.execute("""
        SELECT issue, draft, status, lawyer_comment
        FROM documents
        WHERE user_id=?
    """, (current_user.id,))

    docs = cur.fetchall()
    conn.close()

    return jsonify({"documents": docs})

@app.route("/export/pdf", methods=["POST"])
@login_required
def export_pdf():
    text = request.json["text"]
    file = io.BytesIO()
    pdf = canvas.Canvas(file, pagesize=A4)

    y = 800
    for line in text.split("\n"):
        pdf.drawString(40, y, line)
        y -= 14
        if y < 40:
            pdf.showPage()
            y = 800

    pdf.save()
    file.seek(0)

    return send_file(file, as_attachment=True, download_name="legal_document.pdf")

# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)