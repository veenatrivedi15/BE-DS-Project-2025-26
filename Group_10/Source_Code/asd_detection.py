import os
import cv2
import numpy as np
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model

# --- Configuration Changes ---
asd_bp = Blueprint('asd_bp', __name__)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. Update IMG_SIZE to match the ResNet50 model input
IMG_SIZE = (224, 224) 
MODEL_PATH = "asd_model/asd_face_model.h5"

# 2. Add Face Cascade Path
FACE_CASCADE_PATH = "haarcascade_frontalface_default.xml" 

# Load the model and cascade classifier once on startup
try:
    model = load_model(MODEL_PATH)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

try:
    # Load the Haar Cascade for face detection
    face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
except Exception as e:
    print(f"Error loading face cascade: {e}. Ensure the file is present.")
    face_cascade = None


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@asd_bp.route("/predict_asd", methods=["POST"])
def predict_asd():
    if model is None or face_cascade is None:
        return jsonify({"error": "Server initialization error (Model/Detector missing)."}), 500

    if "photo" not in request.files:
        return jsonify({"error": "No photo part in the request."}), 400

    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed."}), 400

    # Save uploaded file
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        # Load image
        img = cv2.imread(filepath)
        if img is None:
            return jsonify({"error": "Cannot read image file."}), 400

        # --- CRITICAL FIX: FACE DETECTION & CROPPING ---
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )

        if len(faces) == 0:
            return jsonify({"error": "No clear face detected in the image. Please upload a clear photo."}), 400

        # Crop the face (using the first one found)
        (x, y, w, h) = faces[0]
        # Add buffer around the face
        buffer = int(0.1 * w) 
        x_crop = max(0, x - buffer)
        y_crop = max(0, y - buffer)
        x_end = min(img.shape[1], x + w + buffer)
        y_end = min(img.shape[0], y + h + buffer)
        
        face_img = img[y_crop:y_end, x_crop:x_end]
        
        # Preprocess Cropped Face (BGR to RGB, Resize, Normalize)
        face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB) 
        img_resized = cv2.resize(face_img_rgb, IMG_SIZE)
        img_array = np.expand_dims(img_resized, axis=0) / 255.0

        # Predict
        prediction = float(model.predict(img_array)[0][0])

        # --- Enhanced Prediction Logic (for better user feedback) ---
        if prediction >= 0.7:
            result_class = "Autistic (High Likelihood)"
            confidence = prediction
        elif prediction >= 0.5:
            result_class = "Autistic (Moderate Likelihood)"
            confidence = prediction
        else:
            result_class = "Non-Autistic"
            confidence = 1 - prediction
        
        return jsonify({"class": result_class, "confidence": round(confidence, 3)})

    except Exception as e:
        print(f"Prediction Error: {e}")
        return jsonify({"error": f"Internal server error during prediction: {e}"}), 500

    finally:
        # Delete uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)