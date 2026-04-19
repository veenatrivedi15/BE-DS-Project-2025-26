from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import atexit
import os
import json
import uuid
import numpy as np
import io
import base64
import re
from PIL import Image

# New Feature Imports
from dotenv import load_dotenv
from groq import Groq
from deep_translator import GoogleTranslator

load_dotenv()

# Lazy TensorFlow imports to avoid crashing on startup if TF isn't available in current interpreter
try:
    from tensorflow.keras.models import load_model as tf_load_model
    from tensorflow.keras.preprocessing.image import load_img as tf_load_img, img_to_array as tf_img_to_array
    _tf_import_error = None
except Exception as _e:
    tf_load_model = None
    tf_load_img = None
    tf_img_to_array = None
    _tf_import_error = _e
from functools import wraps
try:
    from inference_sdk import InferenceHTTPClient
    _inference_sdk_available = True
except ImportError:
    InferenceHTTPClient = None
    _inference_sdk_available = False

from color_feature import color_bp

# ---------------- App Setup ----------------
app = Flask(__name__)
app.secret_key = "change_this_secret"

# Configure Groq API
try:
    groq_client = Groq(
        api_key=os.getenv("GROQ_API_KEY"),
    )
except Exception as e:
    print(f"Groq Client Init Error: {e}")
    groq_client = None

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "profile")
os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)
ALLOWED_PROFILE_EXTS = {"png", "jpg", "jpeg", "webp"}

# ---------------- SQLite Configuration ----------------
DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "icare.db"))


def _initialize_database():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn, cur


def _ensure_user_columns(conn, cur):
    cur.execute("PRAGMA table_info(users)")
    existing = {row[1] for row in cur.fetchall()}
    if "profile_image" not in existing:
        cur.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
    if "bio" not in existing:
        cur.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")
    conn.commit()


db, cursor = _initialize_database()
_ensure_user_columns(db, cursor)


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    cursor.execute(
        "SELECT id, username, email, password, profile_image, bio, created_at FROM users WHERE id=?",
        (user_id,),
    )
    return cursor.fetchone()


def _is_allowed_profile_image(filename):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_PROFILE_EXTS


def _profile_image_url(rel_path):
    if not rel_path:
        return None
    return url_for("static", filename=rel_path.replace("\\", "/"))


@app.context_processor
def inject_nav_profile():
    user = _current_user()
    if not user:
        return {"nav_user": None, "nav_profile_image_url": None, "nav_initial": None}
    username = user["username"] or ""
    return {
        "nav_user": user,
        "nav_profile_image_url": _profile_image_url(user["profile_image"]),
        "nav_initial": username[:1].upper() if username else "U",
    }

# Ensure DB connection is closed cleanly on process exit to avoid interpreter-finalization
# warnings/errors (especially on Windows/Python 3.13)
def _close_db_on_exit():
    try:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass
    except Exception:
        # Suppress any shutdown-time errors
        pass

atexit.register(_close_db_on_exit)

# Register blueprints
app.register_blueprint(color_bp)

# ---------------- Eye Disease Model (lazy) ----------------
MODEL_PATH = os.path.join("static", "models", "eye_disease_finalV2.keras")
CLASS_LABELS_PATH = os.path.join("static", "models", "class_labels_V2.json")
DEFAULT_DISEASE_CLASSES = ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]
DISEASE_CLASSES = DEFAULT_DISEASE_CLASSES.copy()
eye_disease_model = None


def _to_display_disease_label(label):
    normalized = str(label).strip().lower()
    mapping = {
        "cataract": "Cataract",
        "diabetic_retinopathy": "Diabetic Retinopathy",
        "glaucoma": "Glaucoma",
        "normal": "Normal",
    }
    if normalized in mapping:
        return mapping[normalized]
    return normalized.replace("_", " ").title()


def _load_disease_classes_from_file():
    global DISEASE_CLASSES
    if not os.path.exists(CLASS_LABELS_PATH):
        print(f"Warning: class labels file not found at {CLASS_LABELS_PATH}; using defaults")
        return

    try:
        with open(CLASS_LABELS_PATH, "r", encoding="utf-8") as f:
            labels = json.load(f)

        if isinstance(labels, list) and labels:
            DISEASE_CLASSES = [_to_display_disease_label(label) for label in labels]
        else:
            print(f"Warning: invalid class labels format in {CLASS_LABELS_PATH}; using defaults")
    except Exception as exc:
        print(f"Warning: failed to load class labels from {CLASS_LABELS_PATH}: {exc}; using defaults")


_load_disease_classes_from_file()

# ---------------- Eye Fatigue Models (lazy) ----------------
EYE_REDNESS_MODEL_PATH = os.path.join("static", "models", "eye_redness_model.keras")
eye_redness_model = None
roboflow_client = None

def ensure_eye_model():
    global eye_disease_model
    if eye_disease_model is not None:
        return True, None
    if tf_load_model is None:
        return False, _tf_import_error or RuntimeError("TensorFlow is not available in this environment")
    if not os.path.exists(MODEL_PATH):
        return False, FileNotFoundError(f"Model file not found at {MODEL_PATH}")
    try:
        eye_disease_model = tf_load_model(MODEL_PATH)
        return True, None
    except Exception as e:
        return False, e

def ensure_fatigue_models():
    global eye_redness_model, roboflow_client
    
    # Load redness model
    if eye_redness_model is None:
        if not os.path.exists(EYE_REDNESS_MODEL_PATH):
            return False, FileNotFoundError(f"Eye redness model not found at {EYE_REDNESS_MODEL_PATH}")
        try:
            import keras
            eye_redness_model = keras.models.load_model(EYE_REDNESS_MODEL_PATH)
        except Exception as e:
            return False, e
    
    # Initialize Roboflow client
    if roboflow_client is None and _inference_sdk_available:
        try:
            roboflow_client = InferenceHTTPClient(
                api_url="https://serverless.roboflow.com",
                api_key="hBljhOwZ15CdLgOj0Kjj"
            )
        except Exception as e:
            print(f"Warning: Could not initialize Roboflow client: {e}")
    
    return True, None

def preprocess_eye_image(image, target_size=(224, 224)):
    """Preprocess image for eye redness model prediction"""
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image = image.resize(target_size)
    img_array = np.array(image)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


def to_probabilities(raw_scores):
    """Convert model outputs to a stable probability distribution."""
    scores = np.asarray(raw_scores, dtype=np.float64).reshape(-1)

    if scores.size == 0:
        return np.zeros(len(DISEASE_CLASSES), dtype=np.float64)

    # If outputs already look like probabilities, keep and renormalize safely.
    if np.all(scores >= 0) and np.all(scores <= 1) and np.isclose(scores.sum(), 1.0, atol=1e-3):
        probs = scores.copy()
    else:
        # Treat outputs as logits and apply softmax.
        shifted = scores - np.max(scores)
        exp_scores = np.exp(shifted)
        denom = exp_scores.sum()
        probs = exp_scores / denom if denom > 0 else np.ones_like(exp_scores) / exp_scores.size

    probs = np.clip(probs, 0.0, 1.0)
    total = probs.sum()
    if total <= 0:
        return np.ones_like(probs) / probs.size
    return probs / total

# ---------------- Login Required Decorator ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login to access this feature.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- Home ----------------
@app.route('/')
def home():
    username = session.get('username')
    first_initial = username[0].upper() if username else None
    return render_template('home.html', username=username, first_initial=first_initial)

# ---------------- Eye Disease Detection ----------------
@app.route("/detection", methods=["GET", "POST"])
@login_required
def detection():
    prediction = None
    uploaded_file_path = None
    disease_description = None

    DISEASE_INFO = {
        "Cataract": "Cataract causes clouding of the eye lens. Consult an ophthalmologist for diagnosis and treatment options.",
        "Diabetic Retinopathy": "This is a diabetes-related eye condition that can damage the retina. Early treatment is crucial.",
        "Glaucoma": "Glaucoma can cause damage to the optic nerve. See an eye specialist for tests and treatment.",
        "Normal": "Your eyes appear normal. Regular check-ups are recommended to maintain eye health."
    }

    if request.method == "POST":
        if "image" not in request.files or request.files["image"].filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)

        file = request.files["image"]
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        uploaded_file_path = f"uploads/{filename}"

        # Ensure TensorFlow and model are available
        ok, err = ensure_eye_model()
        if not ok:
            flash("Eye disease model isn't available in the current Python environment. Please run the app using the provided start script or a compatible virtual environment.", "danger")
            # Optional: include error details for developers
            flash(str(err), "warning")
            return redirect(request.url)

        img = tf_load_img(filepath, target_size=(224, 224))
        img_array = tf_img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        raw_preds = eye_disease_model.predict(img_array, verbose=0)[0]
        probs = to_probabilities(raw_preds)

        # Sort predictions by confidence
        sorted_indices = probs.argsort()[::-1]
        
        results = []
        for i in sorted_indices:
            cls_name = DISEASE_CLASSES[i] if i < len(DISEASE_CLASSES) else f"Class {i}"
            conf = float(probs[i]) * 100
            results.append({
                "class_name": cls_name,
                "confidence": conf,
                "description": DISEASE_INFO.get(cls_name, "Please consult an ophthalmologist for a detailed assessment.")
            })

        top_class = results[0]["class_name"]
        top_conf = results[0]["confidence"]

        if top_class == "Normal":
            prediction = "Normal Finding"
            if top_conf >= 80:
                disease_description = f"The analysis strongly indicates a normal finding. {DISEASE_INFO['Normal']}"
            else:
                disease_description = f"The analysis suggests normal findings, but with moderate confidence. {DISEASE_INFO['Normal']}"
        else:
            prediction = f"Potential {top_class} Detected"
            disease_description = f"The analysis indicates a potential risk of {top_class}. {DISEASE_INFO.get(top_class, 'Please consult an ophthalmologist for a detailed assessment.')}"

        # Store in session then redirect (PRG pattern)
        session['eye_pred'] = {
            'prediction': prediction,
            'uploaded_file': uploaded_file_path,
            'disease_description': disease_description,
            'results': results
        }
        return redirect(url_for('detection_result'))

    return render_template(
        "feature_eye_disease.html",
        prediction=None,
        uploaded_file=None,
        disease_description=None
    )

@app.route('/detection/result')
@login_required
def detection_result():
    data = session.get('eye_pred')
    if not data:
        return redirect(url_for('detection'))
    # Optionally pop to avoid re-display on refresh
    # data = session.pop('eye_pred')
    return render_template(
        'feature_eye_disease_result.html',
        **data
    )

# ---------------- Color Blindness ----------------
@app.route('/colorblind')
@login_required
def colorblind():
    return render_template('feature_colorblind.html')

# ---------------- Eye Fatigue ----------------
@app.route('/fatigue')
@login_required
def fatigue():
    return render_template('feature_fatigue.html')

@app.route('/fatigue/predict', methods=['POST'])
@login_required
def fatigue_predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Ensure models are loaded
    ok, err = ensure_fatigue_models()
    if not ok:
        return jsonify({'error': f'Model loading failed: {str(err)}'}), 500
    
    try:
        # Read image
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Get questionnaire data
        questionnaire_data = {
            'burning': request.form.get('burning', 'no'),
            'itching': request.form.get('itching', 'no'),
            'screen_time': request.form.get('screen_time', '0'),
            'contact_lens': request.form.get('contact_lens', 'no'),
            'redness_visible': request.form.get('redness_visible', 'no'),
            'watery_eyes': request.form.get('watery_eyes', 'no'),
            'sensitivity': request.form.get('sensitivity', 'no'),
            'sleep_hours': request.form.get('sleep_hours', '0')
        }
        
        # 1. Redness Detection
        processed_image = preprocess_eye_image(image)
        prediction = eye_redness_model.predict(processed_image, verbose=0)
        
        if prediction.shape[1] == 1:
            redness_score = float(prediction[0][0]) * 100
            normal_score = 100 - redness_score
        else:
            redness_score = float(prediction[0][1]) * 100
            normal_score = float(prediction[0][0]) * 100
        
        # 2. Fatigue Detection (Roboflow)
        temp_path = os.path.join(UPLOAD_FOLDER, 'temp_fatigue_image.jpg')
        if image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            rgb_image.save(temp_path)
        elif image.mode != 'RGB':
            image.convert('RGB').save(temp_path)
        else:
            image.save(temp_path)
        
        fatigue_score = 0
        fatigue_status = "Normal"
        
        if roboflow_client:
            try:
                FATIGUE_MODEL = "eyes-bhltc/1"
                fatigue_result = roboflow_client.infer(temp_path, model_id=FATIGUE_MODEL)
                
                if isinstance(fatigue_result, dict):
                    predictions = fatigue_result.get('predictions', {})
                    
                    if isinstance(predictions, dict):
                        normal_confidence = predictions.get('normal', {}).get('confidence', 0) if isinstance(predictions.get('normal'), dict) else 0
                        red_eyes_confidence = predictions.get('red_eyes', {}).get('confidence', 0) if isinstance(predictions.get('red_eyes'), dict) else 0
                        tired_confidence = predictions.get('tired', {}).get('confidence', 0) if isinstance(predictions.get('tired'), dict) else 0
                        fatigue_confidence_val = predictions.get('fatigue', {}).get('confidence', 0) if isinstance(predictions.get('fatigue'), dict) else 0
                        
                        fatigue_score = max(red_eyes_confidence, tired_confidence, fatigue_confidence_val) * 100
                        
                        if fatigue_score > 50:
                            fatigue_status = "Fatigued"
                    elif isinstance(predictions, list) and len(predictions) > 0:
                        fatigue_pred = max(predictions, key=lambda x: x.get('confidence', 0) if isinstance(x, dict) else 0)
                        if isinstance(fatigue_pred, dict):
                            fatigue_class = fatigue_pred.get('class', 'normal').lower()
                            fatigue_confidence = fatigue_pred.get('confidence', 0) * 100
                            
                            if 'fatigue' in fatigue_class or 'tired' in fatigue_class or 'red' in fatigue_class:
                                fatigue_score = fatigue_confidence
                                fatigue_status = "Fatigued"
            except Exception as e:
                print(f"Fatigue detection error: {str(e)}")
        
        # 3. Dryness Detection (Roboflow)
        dryness_score = 0
        dryness_status = "Normal"
        
        if roboflow_client:
            try:
                DRYNESS_MODEL = "dry-eye-prediction/3"
                dryness_result = roboflow_client.infer(temp_path, model_id=DRYNESS_MODEL)
                
                if isinstance(dryness_result, dict) and 'predictions' in dryness_result and len(dryness_result['predictions']) > 0:
                    dryness_pred = max(dryness_result['predictions'], key=lambda x: x.get('confidence', 0))
                    dryness_class = dryness_pred.get('class', 'normal').lower()
                    dryness_confidence = dryness_pred.get('confidence', 0) * 100
                    
                    if 'dry' in dryness_class:
                        dryness_score = dryness_confidence
                        dryness_status = "Dry"
            except Exception as e:
                print(f"Dryness detection error: {str(e)}")
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Generate diagnosis
        diagnosis = generate_fatigue_diagnosis(
            redness_score, fatigue_score, dryness_score, questionnaire_data
        )
        
        # Convert image to base64
        buffered = io.BytesIO(image_bytes)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'redness_score': round(redness_score, 2),
            'normal_score': round(normal_score, 2),
            'fatigue_score': round(fatigue_score, 2),
            'fatigue_status': fatigue_status,
            'dryness_score': round(dryness_score, 2),
            'dryness_status': dryness_status,
            'diagnosis': diagnosis,
            'image': f'data:image/jpeg;base64,{img_str}'
        })
    
    except Exception as e:
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500

def generate_fatigue_diagnosis(redness_score, fatigue_score, dryness_score, questionnaire):
    """Generate comprehensive diagnosis and recommendations"""
    
    def _safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    # Image-based risk from model outputs.
    image_risk = (redness_score + fatigue_score + dryness_score) / 3.0

    # Questionnaire risk score (0-100) based on symptoms + lifestyle indicators.
    symptom_flags = [
        questionnaire.get('burning') == 'yes',
        questionnaire.get('itching') == 'yes',
        questionnaire.get('watery_eyes') == 'yes',
        questionnaire.get('sensitivity') == 'yes',
        questionnaire.get('redness_visible') == 'yes'
    ]
    symptom_points = sum(12 for flag in symptom_flags if flag)  # max 60

    screen_time = _safe_int(questionnaire.get('screen_time', 0), 0)
    if screen_time >= 9:
        screen_points = 20
    elif screen_time >= 7:
        screen_points = 14
    elif screen_time >= 5:
        screen_points = 8
    else:
        screen_points = 3

    sleep_hours = _safe_int(questionnaire.get('sleep_hours', 0), 0)
    if sleep_hours < 5:
        sleep_points = 20
    elif sleep_hours < 7:
        sleep_points = 12
    elif sleep_hours <= 9:
        sleep_points = 4
    else:
        sleep_points = 6

    contact_lens_points = 8 if questionnaire.get('contact_lens') == 'yes' else 0
    questionnaire_risk = min(100.0, float(symptom_points + screen_points + sleep_points + contact_lens_points))

    # Final risk combines objective image signals + subjective questionnaire context.
    combined_risk = (0.7 * image_risk) + (0.3 * questionnaire_risk)
    overall_score = max(0.0, 100.0 - combined_risk)
    
    conditions = []
    severity_notes = []
    
    if redness_score > 70:
        conditions.append("Eye Redness (High Confidence)")
        severity_notes.append(f"High probability of redness detected ({redness_score:.1f}% confidence)")
    elif redness_score > 50:
        conditions.append("Eye Redness (Moderate Confidence)")
        severity_notes.append(f"Moderate probability of redness detected ({redness_score:.1f}% confidence)")
    
    if fatigue_score > 70:
        conditions.append("Eye Fatigue (High Confidence)")
        severity_notes.append(f"High probability of fatigue detected ({fatigue_score:.1f}% confidence)")
    elif fatigue_score > 50:
        conditions.append("Eye Fatigue (Moderate Confidence)")
        severity_notes.append(f"Moderate probability of fatigue detected ({fatigue_score:.1f}% confidence)")
    
    if dryness_score > 70:
        conditions.append("Dry Eyes (High Confidence)")
        severity_notes.append(f"High probability of dryness detected ({dryness_score:.1f}% confidence)")
    elif dryness_score > 50:
        conditions.append("Dry Eyes (Moderate Confidence)")
        severity_notes.append(f"Moderate probability of dryness detected ({dryness_score:.1f}% confidence)")
    
    if overall_score >= 80:
        status = "Healthy"
        severity = "low"
    elif overall_score >= 60:
        status = "Mild Concerns"
        severity = "moderate"
    else:
        status = "Attention Needed"
        severity = "high"
    
    findings = []
    findings.append(
        f"Integrated scoring: Image risk {image_risk:.1f}% and questionnaire risk {questionnaire_risk:.1f}% were combined for final assessment."
    )
    findings.extend(severity_notes)
    
    if questionnaire['burning'] == 'yes':
        findings.append("Reported burning sensation (symptomatic)")
    if questionnaire['itching'] == 'yes':
        findings.append("Reported itching discomfort (symptomatic)")
    if questionnaire['watery_eyes'] == 'yes':
        findings.append("Excessive tearing reported (symptomatic)")
    if questionnaire['sensitivity'] == 'yes':
        findings.append("Light sensitivity present (symptomatic)")
    
    if len(conditions) > 0:
        findings.insert(0, "⚕️ Note: Scores indicate detection confidence, not clinical severity. Professional examination required for accurate severity assessment.")
    
    recommendations = []
    
    if len(conditions) > 0:
        recommendations.insert(0, "⚠️ IMPORTANT: Consult an eye care professional for clinical examination and severity assessment")
    
    screen_time = _safe_int(questionnaire.get('screen_time', 0), 0)
    if screen_time > 6 or fatigue_score > 50:
        recommendations.append("Follow the 20-20-20 rule: Every 20 minutes, look at something 20 feet away for 20 seconds")
        recommendations.append("Consider blue light filtering glasses or screen filters")
    
    sleep_hours = _safe_int(questionnaire.get('sleep_hours', 0), 0)
    if sleep_hours < 7 or fatigue_score > 50:
        recommendations.append("Aim for 7-9 hours of quality sleep per night")
        recommendations.append("Maintain a consistent sleep schedule")
    
    if dryness_score > 50 or questionnaire['burning'] == 'yes':
        recommendations.append("Use preservative-free artificial tears 3-4 times daily")
        recommendations.append("Increase humidity in your environment (use a humidifier)")
        recommendations.append("Stay well-hydrated (drink 8-10 glasses of water daily)")
    
    if questionnaire['contact_lens'] == 'yes':
        recommendations.append("Reduce contact lens wearing time; give eyes a break with glasses")
        recommendations.append("Ensure proper contact lens hygiene and replacement schedule")
    
    if redness_score > 50:
        recommendations.append("Apply cool compresses to closed eyes for 10 minutes")
        recommendations.append("Avoid rubbing your eyes")
        recommendations.append("Remove potential irritants (smoke, allergens)")
    
    recommendations.extend([
        "Maintain a diet rich in Omega-3 fatty acids (fish, flaxseeds, walnuts)",
        "Ensure proper lighting when reading or working",
        "Take regular breaks from screen time and close-up work"
    ])
    
    consultation_needed = len(conditions) > 0
    if overall_score < 50 or len(conditions) >= 2:
        consultation_needed = True
        recommendations.insert(0, "🚨 URGENT: Multiple conditions detected - seek immediate professional eye care")
    
    return {
        'status': status,
        'severity': severity,
        'overall_score': round(overall_score, 1),
        'image_risk_score': round(image_risk, 1),
        'questionnaire_risk_score': round(questionnaire_risk, 1),
        'combined_risk_score': round(combined_risk, 1),
        'conditions': conditions,
        'findings': findings,
        'recommendations': recommendations,
        'consultation_needed': consultation_needed,
        'medical_note': 'This AI screening tool provides detection confidence scores, not clinical severity measurements. Only a licensed eye care professional can accurately diagnose and assess the severity of eye conditions through comprehensive examination.'
    }

# ---------------- Recommendations / Chatbot ----------------
@app.route('/recommendations')
@login_required
def recommendations():
    return render_template('feature_recommend.html')


def get_suggested_questions(user_message: str):
    """Return concise follow-up question suggestions based on user intent."""
    text = (user_message or "").lower()

    if any(k in text for k in ["dry", "burn", "itch", "watery", "red"]):
        return [
            "What daily habits help reduce dry eyes?",
            "When should I see an eye specialist for these symptoms?",
            "Which eye drops are usually safer for daily use?"
        ]

    if any(k in text for k in ["screen", "laptop", "mobile", "computer", "fatigue", "strain"]):
        return [
            "Can you give me a 20-20-20 eye care routine?",
            "What screen settings are better for eye comfort?",
            "How many breaks should I take in a workday?"
        ]

    if any(k in text for k in ["glaucoma", "cataract", "retina", "diabetic", "disease"]):
        return [
            "What early warning signs should I monitor?",
            "How often should I get an eye check-up?",
            "What tests are commonly done by an ophthalmologist?"
        ]

    return [
        "How can I protect my eyes during long screen use?",
        "What symptoms mean I should get an eye exam soon?",
        "Can you suggest daily eye-care habits?"
    ]


def clean_bot_text(text: str) -> str:
    """Normalize model output for readable spacing and clean formatting."""
    msg = (text or "").replace('**', '').replace('__', '').strip()
    msg = re.sub(r'^\s*[-*]\s+', '', msg, flags=re.MULTILINE)
    msg = re.sub(r'([,.;!?])(?=\S)', r'\1 ', msg)
    # Put numbered points on separate lines when model returns inline numbering.
    msg = re.sub(r'\s+(?=(\d+)\.\s)', '\n', msg)
    msg = re.sub(r'[ \t]+', ' ', msg)
    msg = re.sub(r'\s*\n\s*', '\n', msg).strip()
    return msg


def looks_spacing_broken(text: str) -> bool:
    """Detect suspiciously de-spaced output like 'Hello,howcanIhelpyou'."""
    msg = (text or "").strip()
    if len(msg) < 20:
        return False
    letters = re.sub(r'[^A-Za-z]', '', msg)
    if len(letters) < 15:
        return False
    space_count = msg.count(' ')
    # Very low space density for long English text indicates malformed output.
    return space_count == 0 or (space_count / max(len(msg), 1) < 0.03)

@app.route('/chat', methods=['POST'])
def chat():
    if not groq_client:
        return jsonify({'error': 'Groq client not initialized (Missing API Key?)'}), 500

    data = request.json
    user_message = data.get('message')
    target_language = data.get('language', 'en')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an eye-care assistant for an ophthalmology-focused app. "
                        "Follow these rules strictly: "
                        "1) Handle basic greetings naturally and briefly. "
                        "2) Answer only eye-health-related queries (symptoms, habits, prevention, eye care, when to seek specialist care). "
                        "3) If the topic is unrelated to eye health, politely refuse in one short sentence and ask the user to ask an eye-care question. "
                        "4) Keep responses concise and directly relevant. "
                        "5) Prefer professional point-wise answers when useful (2-5 short points). "
                        "6) Do not add extra explanations that were not asked. "
                        "7) Do not use markdown formatting symbols, especially no asterisks or bold markers. "
                        "8) Do not claim diagnosis; provide general guidance only. "
                        "9) Mention medical disclaimer only when clinically relevant; do not append it to every response."
                    )
                },
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        bot_reply = clean_bot_text(chat_completion.choices[0].message.content)

        # If output is malformed, request one concise repaired rewrite.
        if looks_spacing_broken(bot_reply):
            repair_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Rewrite the given text with proper spacing and punctuation. "
                            "Keep meaning the same, keep it concise, and do not use markdown symbols."
                        )
                    },
                    {
                        "role": "user",
                        "content": bot_reply
                    }
                ],
                model="llama-3.3-70b-versatile",
            )
            bot_reply = clean_bot_text(repair_completion.choices[0].message.content)

        suggestions = get_suggested_questions(user_message)
        
        # Translate response if target language is not English
        if target_language != 'en':
            try:
                bot_reply = GoogleTranslator(source='auto', target=target_language).translate(bot_reply)
                suggestions = [
                    GoogleTranslator(source='auto', target=target_language).translate(s)
                    for s in suggestions
                ]
            except Exception as trans_e:
                print(f"Translation Error: {trans_e}")
                # Fallback to English but append a note? Or just leave it as is.
                pass
        
        # Check for trigger phrases to suggest finding a clinic
        trigger_phrases = ["consult an eye specialist", "find a nearby clinic", "see a doctor", "visit an eye specialist", "ophthalmologist"]
        should_search = any(phrase in bot_reply.lower() for phrase in trigger_phrases)

        return jsonify({'response': bot_reply, 'should_search': should_search, 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_clinics', methods=['POST'])
def search_clinics():
    data = request.json or {}
    location = data.get('location')
    if not location:
        return jsonify({'error': 'No location provided'}), 400

    try:
        parts = location.split(',')
        lat, lng = float(parts[0].strip()), float(parts[1].strip())
    except (ValueError, IndexError):
        return jsonify({'error': 'Invalid location format. Expected "lat,lng"'}), 400

    # 1) Prefer SerpApi (Google Maps) when configured.
    serpapi_key = os.getenv('SERPAPI_API_KEY')
    if serpapi_key:
        try:
            import requests as _req
            resp = _req.get('https://serpapi.com/search.json', params={
                'engine': 'google_maps',
                'q': 'eye clinic',
                'll': f'@{lat},{lng},14z',
                'type': 'search',
                'api_key': serpapi_key
            })
            resp.raise_for_status()
            results = resp.json()
            local_results = results.get('local_results', []) or []

            clinics = []
            for item in local_results:
                gps = item.get('gps_coordinates') or {}
                clat = gps.get('latitude')
                clng = gps.get('longitude')
                if clat is None or clng is None:
                    continue

                clinics.append({
                    'name': item.get('title', 'Eye Clinic'),
                    'address': item.get('address', ''),
                    'phone': item.get('phone', ''),
                    'website': item.get('website', ''),
                    'rating': item.get('rating'),
                    'reviews': item.get('reviews'),
                    'latitude': clat,
                    'longitude': clng,
                })

            return jsonify({'clinics': clinics, 'source': 'serpapi'})
        except Exception as e:
            # Fall back to OpenStreetMap query if SerpApi fails.
            print(f"SerpApi clinic lookup failed, falling back to Overpass: {e}")

    # 2) Fallback: OpenStreetMap Overpass
    try:
        import requests as _req
        radius = 5000
        query = (
            f'[out:json][timeout:25];'
            f'('
            f'node["amenity"="hospital"]["name"~"eye|vision|optic|cataract|retina|netralaya|nethra|nayan|chakshu",i](around:{radius},{lat},{lng});'
            f'node["amenity"="clinic"]["name"~"eye|vision|optic|cataract|retina|netralaya|nethra|nayan|chakshu",i](around:{radius},{lat},{lng});'
            f'node["healthcare"="optometrist"](around:{radius},{lat},{lng});'
            f'node["healthcare"="ophthalmologist"](around:{radius},{lat},{lng});'
            f'node["shop"="optician"](around:{radius},{lat},{lng});'
            f');out center;'
        )
        resp = _req.post(
            'https://overpass-api.de/api/interpreter',
            data={'data': query},
            timeout=30
        )
        resp.raise_for_status()
        elements = resp.json().get('elements', [])

        clinics = []
        for el in elements:
            clat = el.get('lat') or (el.get('center') or {}).get('lat')
            clng = el.get('lon') or (el.get('center') or {}).get('lon')
            if not clat or not clng:
                continue
            tags = el.get('tags', {})
            addr_parts = filter(None, [
                tags.get('addr:housenumber'), tags.get('addr:street'),
                tags.get('addr:suburb'), tags.get('addr:city')
            ])
            clinics.append({
                'name': tags.get('name', 'Eye Clinic'),
                'address': ', '.join(addr_parts) or tags.get('addr:full', ''),
                'phone': tags.get('phone') or tags.get('contact:phone', ''),
                'latitude': clat,
                'longitude': clng,
            })

        return jsonify({'clinics': clinics, 'source': 'overpass'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- Report ----------------
@app.route('/report')
@login_required
def report():
    return render_template('feature_report.html')

# ---------------- Signup ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            db.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email is already registered.", "danger")
        except sqlite3.DatabaseError as err:
            flash(f"Error: {err}", "danger")

    return render_template('signup.html')

# ---------------- Login ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')

# ---------------- Logout ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = _current_user()
    if not user:
        session.clear()
        flash("Session expired. Please login again.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        bio = (request.form.get('bio') or '').strip()

        if not username:
            flash("Username cannot be empty.", "danger")
            return redirect(url_for('profile'))
        if not email or '@' not in email:
            flash("Please enter a valid email.", "danger")
            return redirect(url_for('profile'))
        if len(bio) > 280:
            flash("Bio must be 280 characters or less.", "danger")
            return redirect(url_for('profile'))

        avatar_file = request.files.get('profile_image')
        profile_image_rel = user['profile_image']

        if avatar_file and avatar_file.filename:
            if not _is_allowed_profile_image(avatar_file.filename):
                flash("Profile image must be PNG, JPG, JPEG, or WEBP.", "danger")
                return redirect(url_for('profile'))

            original = secure_filename(avatar_file.filename)
            ext = original.rsplit('.', 1)[1].lower()
            filename = f"u{user['id']}_{uuid.uuid4().hex[:10]}.{ext}"
            out_path = os.path.join(PROFILE_UPLOAD_FOLDER, filename)
            avatar_file.save(out_path)
            profile_image_rel = os.path.join('uploads', 'profile', filename).replace('\\', '/')

            old_rel = user['profile_image']
            if old_rel:
                old_abs = os.path.join('static', old_rel)
                try:
                    if os.path.exists(old_abs):
                        os.remove(old_abs)
                except OSError:
                    pass

        try:
            cursor.execute(
                """
                UPDATE users
                SET username=?, email=?, bio=?, profile_image=?
                WHERE id=?
                """,
                (username, email, bio, profile_image_rel, user['id'])
            )
            db.commit()
            session['username'] = username
            flash("Profile updated successfully.", "success")
        except sqlite3.IntegrityError:
            flash("Email is already used by another account.", "danger")
        except sqlite3.DatabaseError as err:
            flash(f"Database error: {err}", "danger")

        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    user = _current_user()
    if not user:
        session.clear()
        flash("Session expired. Please login again.", "warning")
        return redirect(url_for('login'))

    current_password = request.form.get('current_password') or ''
    new_password = request.form.get('new_password') or ''
    confirm_password = request.form.get('confirm_password') or ''

    if not check_password_hash(user['password'], current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for('profile'))

    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "danger")
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash("New password and confirmation do not match.", "danger")
        return redirect(url_for('profile'))

    try:
        cursor.execute(
            "UPDATE users SET password=? WHERE id=?",
            (generate_password_hash(new_password), user['id'])
        )
        db.commit()
        flash("Password changed successfully.", "success")
    except sqlite3.DatabaseError as err:
        flash(f"Password update failed: {err}", "danger")

    return redirect(url_for('profile'))

# ---------------- About Us ----------------
@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

# ---------------- Run App ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
