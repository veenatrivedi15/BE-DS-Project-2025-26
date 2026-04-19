from flask import Flask, render_template, request, jsonify
import os
import numpy as np
from werkzeug.utils import secure_filename
import keras
from PIL import Image
import io
import base64
from inference_sdk import InferenceHTTPClient

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MODEL_PATH = 'models/eye_redness_model.keras'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load the trained model
print("Loading model...")
model = keras.models.load_model(MODEL_PATH)
print("Model loaded successfully!")

# Initialize Roboflow client
roboflow_client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="hBljhOwZ15CdLgOj0Kjj"
)
FATIGUE_MODEL = "eyes-bhltc/1"
DRYNESS_MODEL = "dry-eye-prediction/3"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image, target_size=(224, 224)):
    """Preprocess image for model prediction"""
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize image
    image = image.resize(target_size)
    
    # Convert to array and normalize
    img_array = np.array(image)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
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
            
            # 1. Redness Detection (existing model)
            processed_image = preprocess_image(image)
            prediction = model.predict(processed_image, verbose=0)
            
            if prediction.shape[1] == 1:
                redness_score = float(prediction[0][0]) * 100
                normal_score = 100 - redness_score
            else:
                redness_score = float(prediction[0][1]) * 100
                normal_score = float(prediction[0][0]) * 100
            
            # 2. Fatigue Detection (Roboflow)
            temp_path = os.path.join(UPLOAD_FOLDER, 'temp_image.jpg')
            
            # Convert RGBA to RGB if necessary
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
            
            try:
                fatigue_result = roboflow_client.infer(temp_path, model_id=FATIGUE_MODEL)
                
                if isinstance(fatigue_result, dict):
                    predictions = fatigue_result.get('predictions', {})
                    
                    if isinstance(predictions, dict):
                        # Predictions is a dict with class names as keys
                        print(f"Fatigue predictions: {predictions}")
                        
                        # Get confidence for each class
                        normal_confidence = predictions.get('normal', {}).get('confidence', 0) if isinstance(predictions.get('normal'), dict) else 0
                        red_eyes_confidence = predictions.get('red_eyes', {}).get('confidence', 0) if isinstance(predictions.get('red_eyes'), dict) else 0
                        tired_confidence = predictions.get('tired', {}).get('confidence', 0) if isinstance(predictions.get('tired'), dict) else 0
                        fatigue_confidence_val = predictions.get('fatigue', {}).get('confidence', 0) if isinstance(predictions.get('fatigue'), dict) else 0
                        
                        # Calculate fatigue score based on highest problematic class
                        fatigue_score = max(red_eyes_confidence, tired_confidence, fatigue_confidence_val) * 100
                        
                        print(f"Normal: {normal_confidence*100:.1f}%, Red Eyes: {red_eyes_confidence*100:.1f}%, Fatigue Score: {fatigue_score:.1f}%")
                        
                        if fatigue_score > 50:
                            fatigue_status = "Fatigued"
                        else:
                            fatigue_status = "Normal"
                            
                    elif isinstance(predictions, list) and len(predictions) > 0:
                        # Alternative format - predictions as list
                        fatigue_pred = max(predictions, key=lambda x: x.get('confidence', 0) if isinstance(x, dict) else 0)
                        if isinstance(fatigue_pred, dict):
                            fatigue_class = fatigue_pred.get('class', 'normal').lower()
                            fatigue_confidence = fatigue_pred.get('confidence', 0) * 100
                            
                            if 'fatigue' in fatigue_class or 'tired' in fatigue_class or 'red' in fatigue_class:
                                fatigue_score = fatigue_confidence
                                fatigue_status = "Fatigued"
                            else:
                                fatigue_score = 100 - fatigue_confidence
            except Exception as e:
                print(f"Fatigue detection error: {str(e)}")
                import traceback
                traceback.print_exc()
                # Use default values if API fails
            
            # 3. Dryness Detection (Roboflow)
            dryness_score = 0
            dryness_status = "Normal"
            
            try:
                dryness_result = roboflow_client.infer(temp_path, model_id=DRYNESS_MODEL)
                
                if isinstance(dryness_result, dict) and 'predictions' in dryness_result and len(dryness_result['predictions']) > 0:
                    dryness_pred = max(dryness_result['predictions'], key=lambda x: x.get('confidence', 0))
                    dryness_class = dryness_pred.get('class', 'normal').lower()
                    dryness_confidence = dryness_pred.get('confidence', 0) * 100
                    
                    if 'dry' in dryness_class:
                        dryness_score = dryness_confidence
                        dryness_status = "Dry"
                    else:
                        dryness_score = 100 - dryness_confidence
            except Exception as e:
                print(f"Dryness detection error: {str(e)}")
                # Use default values if API fails
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Generate comprehensive diagnosis and recommendations
            diagnosis = generate_diagnosis(
                redness_score, fatigue_score, dryness_score, questionnaire_data
            )
            
            # Convert image to base64 for display
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
    
    else:
        return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, or JPEG'}), 400

def generate_diagnosis(redness_score, fatigue_score, dryness_score, questionnaire):
    """Generate comprehensive diagnosis and recommendations
    
    NOTE: Scores represent MODEL CONFIDENCE (probability of condition being present),
    NOT severity levels. For medical-grade severity assessment, regression models or 
    graded classification (mild/moderate/severe) would be required.
    """
    
    # Calculate overall health score (inverse of average detection confidence)
    overall_score = (100 - redness_score + 100 - fatigue_score + 100 - dryness_score) / 3
    
    # Determine severity levels based on confidence thresholds
    # Note: These thresholds are for confidence, not clinical severity
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
    
    # Generate diagnosis
    if overall_score >= 80:
        status = "Healthy"
        severity = "low"
    elif overall_score >= 60:
        status = "Mild Concerns"
        severity = "moderate"
    else:
        status = "Attention Needed"
        severity = "high"
    
    # Generate specific findings
    findings = []
    
    # Add AI detection findings with confidence clarification
    findings.extend(severity_notes)
    
    # Add questionnaire-based findings
    if questionnaire['burning'] == 'yes':
        findings.append("Reported burning sensation (symptomatic)")
    if questionnaire['itching'] == 'yes':
        findings.append("Reported itching discomfort (symptomatic)")
    if questionnaire['watery_eyes'] == 'yes':
        findings.append("Excessive tearing reported (symptomatic)")
    if questionnaire['sensitivity'] == 'yes':
        findings.append("Light sensitivity present (symptomatic)")
    
    # Clinical note about limitations
    if len(conditions) > 0:
        findings.insert(0, "⚕️ Note: Scores indicate detection confidence, not clinical severity. Professional examination required for accurate severity assessment.")
    
    # Generate recommendations
    recommendations = []
    
    # Medical consultation - ALWAYS recommend for detected conditions
    if len(conditions) > 0:
        recommendations.insert(0, "⚠️ IMPORTANT: Consult an eye care professional for clinical examination and severity assessment")
    
    # Screen time recommendations
    screen_time = int(questionnaire.get('screen_time', 0))
    if screen_time > 6 or fatigue_score > 50:
        recommendations.append("Follow the 20-20-20 rule: Every 20 minutes, look at something 20 feet away for 20 seconds")
        recommendations.append("Consider blue light filtering glasses or screen filters")
    
    # Sleep recommendations
    sleep_hours = int(questionnaire.get('sleep_hours', 0))
    if sleep_hours < 7 or fatigue_score > 50:
        recommendations.append("Aim for 7-9 hours of quality sleep per night")
        recommendations.append("Maintain a consistent sleep schedule")
    
    # Dryness recommendations
    if dryness_score > 50 or questionnaire['burning'] == 'yes':
        recommendations.append("Use preservative-free artificial tears 3-4 times daily")
        recommendations.append("Increase humidity in your environment (use a humidifier)")
        recommendations.append("Stay well-hydrated (drink 8-10 glasses of water daily)")
    
    # Contact lens recommendations
    if questionnaire['contact_lens'] == 'yes':
        recommendations.append("Reduce contact lens wearing time; give eyes a break with glasses")
        recommendations.append("Ensure proper contact lens hygiene and replacement schedule")
    
    # Redness recommendations
    if redness_score > 50:
        recommendations.append("Apply cool compresses to closed eyes for 10 minutes")
        recommendations.append("Avoid rubbing your eyes")
        recommendations.append("Remove potential irritants (smoke, allergens)")
    
    # General recommendations
    recommendations.extend([
        "Maintain a diet rich in Omega-3 fatty acids (fish, flaxseeds, walnuts)",
        "Ensure proper lighting when reading or working",
        "Take regular breaks from screen time and close-up work"
    ])
    
    # Consultation emphasis
    consultation_needed = len(conditions) > 0
    if overall_score < 50 or len(conditions) >= 2:
        consultation_needed = True
        recommendations.insert(0, "🚨 URGENT: Multiple conditions detected - seek immediate professional eye care")
    
    return {
        'status': status,
        'severity': severity,
        'overall_score': round(overall_score, 1),
        'conditions': conditions,
        'findings': findings,
        'recommendations': recommendations,
        'consultation_needed': consultation_needed,
        'medical_note': 'This AI screening tool provides detection confidence scores, not clinical severity measurements. Only a licensed eye care professional can accurately diagnose and assess the severity of eye conditions through comprehensive examination.'
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
