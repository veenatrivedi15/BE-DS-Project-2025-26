import os
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import tensorflow as tf
import google.generativeai as genai
from dotenv import load_dotenv
from kindwise import PlantApi, CropHealthApi
import re
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for React Native

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# Get API keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
KINDWISE_API_KEY = os.getenv('KINDWISE_API_KEY')

if not GEMINI_API_KEY:
    raise ValueError(f"GEMINI_API_KEY not found in {env_path}. Please check your .env file.")

print(f"✓ Gemini API Key loaded")
print(f"✓ Kindwise API Key: {'Loaded' if KINDWISE_API_KEY else 'Not found'}")

# Set environment variable for Gemini
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY

# Initialize Gemini
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

# Initialize Kindwise APIs (for disease diagnosis)
plant_api = None
crop_health_api = None

if KINDWISE_API_KEY:
    try:
        # Try CropHealthApi first (from your Colab)
        crop_health_api = CropHealthApi(api_key=KINDWISE_API_KEY)
        print("✓ Kindwise Crop Health API client initialized")
    except Exception as e:
        print(f"✗ CropHealthApi initialization failed: {e}")
        try:
            # Fallback to PlantApi
            plant_api = PlantApi(api_key=KINDWISE_API_KEY)
            print("✓ Kindwise Plant API client initialized")
        except Exception as e2:
            print(f"✗ PlantApi initialization also failed: {e2}")

# Load the crop identification model
model_path = os.path.join(os.path.dirname(__file__), 'model', 'model_vgg16.h5')
model = tf.keras.models.load_model(model_path)
print(f"✓ Crop identification model loaded from: {model_path}")

# Crop class names
CROP_CLASSES = [
    "banana",
    "cashew",
    "coconut",
    "eggplant",
    "maize",
    "mango",
    "ragi",
    "rice",
    "turmeric"
]

# ==========================================
# CROP IDENTIFICATION & RECOMMENDATIONS
# ==========================================

def preprocess_image(image_path, target_size=(224, 224)):
    """Preprocess image for crop identification model"""
    img = Image.open(image_path).convert('RGB')
    img = img.resize(target_size, Image.LANCZOS)
    img_array = np.array(img) / 255.0  # Normalize to [0,1]
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    return img_array

def get_crop_recommendations(predicted_plant):
    """Get farming recommendations for identified crop using Gemini"""
    try:
        print(f"Generating recommendations for: {predicted_plant}")
        
        prompt = f"""Provide farming recommendations for {predicted_plant} in the following EXACT format:

SOIL TYPE: [specify the ideal soil type]
SOIL PH: [specify pH range like 6.0-7.0]
WATERING FREQUENCY: [specify frequency like "Daily" or "2-3 times per week"]
WATERING CAPACITY: [specify as Low/Medium/High]
DESCRIPTION: [brief description about the crop]

Please follow this exact format."""

        response = gemini_model.generate_content(prompt).text
        print(f"Raw response received: {len(response)} characters")
        
        # Initialize with defaults
        recommendations = {
            'soilType': 'N/A',
            'soilPh': 'N/A',
            'wateringFrequency': 'N/A',
            'wateringCapacity': 'Medium',
            'description': f'{predicted_plant} crop identified.'
        }
        
        # Parse response - Strategy 1: Exact format
        soil_type_match = re.search(r'SOIL TYPE:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if soil_type_match:
            recommendations['soilType'] = soil_type_match.group(1).strip()
            
        soil_ph_match = re.search(r'SOIL PH:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if soil_ph_match:
            recommendations['soilPh'] = soil_ph_match.group(1).strip()
            
        water_freq_match = re.search(r'WATERING FREQUENCY:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if water_freq_match:
            recommendations['wateringFrequency'] = water_freq_match.group(1).strip()
            
        water_cap_match = re.search(r'WATERING CAPACITY:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if water_cap_match:
            recommendations['wateringCapacity'] = water_cap_match.group(1).strip()
            
        desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:\n\n|$)', response, re.IGNORECASE | re.DOTALL)
        if desc_match:
            recommendations['description'] = desc_match.group(1).strip()
        
        # Fallback parsing if exact format fails
        if recommendations['soilType'] == 'N/A':
            soil_patterns = [
                r'\*\*Ideal Soil Type:\*\*\s*(.+?)(?:\n|\*|\Z)',
                r'Soil Type:\s*(.+?)(?:\n|\*|\Z)',
                r'thrives in\s+\*\*(.+?soils?)\*\*',
            ]
            for pattern in soil_patterns:
                match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    soil_text = re.sub(r'\*\*', '', match.group(1).strip())
                    recommendations['soilType'] = soil_text[:100].strip()
                    break
        
        if recommendations['wateringCapacity'] == 'Medium':
            response_lower = response.lower()
            if 'drought' in response_lower or 'low water' in response_lower:
                recommendations['wateringCapacity'] = 'Low'
            elif 'high water' in response_lower or 'frequent' in response_lower:
                recommendations['wateringCapacity'] = 'High'
        
        print(f"Parsed recommendations: {recommendations}")
        
        return {
            'cropName': predicted_plant,
            'description': recommendations['description'],
            'wateringFrequency': recommendations['wateringFrequency'],
            'wateringCapacity': recommendations['wateringCapacity'],
            'soilType': recommendations['soilType'],
            'soilPh': recommendations['soilPh']
        }
        
    except Exception as e:
        print(f"Error in get_crop_recommendations: {str(e)}")
        traceback.print_exc()
        return {
            'cropName': predicted_plant,
            'description': f'{predicted_plant} crop identified.',
            'wateringFrequency': 'N/A',
            'wateringCapacity': 'Medium',
            'soilType': 'N/A',
            'soilPh': 'N/A',
            'error': str(e)
        }

@app.route('/predict', methods=['POST'])
def predict_crop():
    """Endpoint for crop identification"""
    try:
        if 'leaf' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['leaf']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        print(f"Processing crop image: {file.filename}")
        
        # Save the uploaded file temporarily
        temp_path = os.path.join('temp', file.filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)
        
        # Preprocess the image
        processed_image = preprocess_image(temp_path)
        
        # Make prediction
        prediction = model.predict(processed_image)
        predicted_class = CROP_CLASSES[np.argmax(prediction)]
        confidence = float(np.max(prediction))
        
        print(f"Predicted crop: {predicted_class} ({confidence:.2%})")
        
        # Fetch recommendations from Gemini API
        result = get_crop_recommendations(predicted_class)
        result['confidence'] = confidence
        
        # Clean up temporary file
        os.remove(temp_path)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in predict_crop: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==========================================
# DISEASE DIAGNOSIS & TREATMENT
# ==========================================

def get_treatment_recommendations(disease_name, crop_name, severity="Unknown"):
    """Get detailed treatment recommendations from Gemini API"""
    try:
        print(f"Generating treatment for: {disease_name} on {crop_name}")
        
        prompt = f"""You are an expert agricultural advisor for Indian farmers.

Disease Detected: {disease_name}
Crop: {crop_name}
Severity: {severity}

Provide clear, actionable treatment recommendations in the following EXACT format:

CHEMICAL_TREATMENT:
Product: [Specific Indian brand name - Bayer/Syngenta/UPL/Dhanuka]
Active Ingredient: [Technical name]
Dosage: [X ml per liter OR Y gm per acre]
Application: [Spray method, timing]
Cost: [₹X per acre approximately]
Where to Buy: [Local agricultural stores]
Results: [X days]

ORGANIC_TREATMENT:
Recipe: [Neem oil / Garlic spray / etc.]
Ingredients: [List with quantities]
Preparation: [Simple steps]
Application: [How often, when to spray]
Cost: [₹X]
Best For: [Early stage / Prevention]

IMMEDIATE_ACTIONS:
- [Action 1]
- [Action 2]
- [Action 3]

PREVENTION:
- [Preventive measure 1]
- [Preventive measure 2]
- [Preventive measure 3]

TIMELINE:
Day 1-3: [What to do]
Day 4-7: [What to expect]
Day 8-14: [Recovery signs]

WARNING_SIGNS:
- [Red flag 1]
- [Red flag 2]
- [Red flag 3]

Keep it simple, practical for Indian farmers."""

        response = gemini_model.generate_content(prompt)
        recommendations_text = response.text
        
        print(f"Treatment recommendations received: {len(recommendations_text)} characters")
        
        # Parse the response
        parsed = parse_treatment_recommendations(recommendations_text)
        return parsed
        
    except Exception as e:
        print(f"Error generating treatment: {str(e)}")
        traceback.print_exc()
        return {
            'chemicalTreatment': 'Consult local agricultural expert for chemical treatment options.',
            'organicTreatment': 'Apply neem oil spray as a general organic remedy.',
            'immediateActions': ['Remove infected leaves', 'Isolate affected plants', 'Improve air circulation'],
            'prevention': ['Regular monitoring', 'Proper spacing', 'Good drainage'],
            'timeline': 'Monitor for 7-14 days and consult expert if condition worsens.',
            'warningSigns': ['Rapid spread to other plants', 'Complete leaf wilting', 'Stem rot'],
            'rawRecommendations': f'Error: {str(e)}'
        }

def parse_treatment_recommendations(text):
    """Parse Gemini's text response into structured format"""
    def extract_section(pattern, text, default="N/A"):
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return default
    
    def extract_list(pattern, text):
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            items_text = match.group(1)
            items = re.findall(r'[-•]\s*(.+?)(?=\n[-•]|\n\n|\Z)', items_text, re.DOTALL)
            return [item.strip() for item in items if item.strip()]
        return []
    
    parsed = {
        'chemicalTreatment': extract_section(
            r'CHEMICAL_TREATMENT:(.+?)(?:ORGANIC_TREATMENT:|$)', 
            text, 
            'Consult local agricultural expert'
        ),
        'organicTreatment': extract_section(
            r'ORGANIC_TREATMENT:(.+?)(?:IMMEDIATE_ACTIONS:|$)', 
            text,
            'Neem oil spray can be used as organic treatment'
        ),
        'immediateActions': extract_list(
            r'IMMEDIATE_ACTIONS:(.+?)(?:PREVENTION:|$)', 
            text
        ) or ['Remove infected parts', 'Isolate affected plants', 'Improve ventilation'],
        'prevention': extract_list(
            r'PREVENTION:(.+?)(?:TIMELINE:|$)', 
            text
        ) or ['Regular monitoring', 'Proper spacing', 'Good drainage'],
        'timeline': extract_section(
            r'TIMELINE:(.+?)(?:WARNING_SIGNS:|$)', 
            text,
            'Monitor for 7-14 days'
        ),
        'warningSigns': extract_list(
            r'WARNING_SIGNS:(.+?)$', 
            text
        ) or ['Rapid spread', 'Severe wilting', 'Plant death'],
        'rawRecommendations': text
    }
    
    return parsed

@app.route('/api/diagnose-disease', methods=['POST'])
def diagnose_disease():
    """Endpoint for plant disease diagnosis using Kindwise API"""
    try:
        if not KINDWISE_API_KEY:
            return jsonify({
                'success': False,
                'error': 'Kindwise API not configured. Please add KINDWISE_API_KEY to .env file'
            }), 500
        
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No selected file'
            }), 400
        
        print(f"Processing disease diagnosis for: {image_file.filename}")
        
        # Read image data
        image_data = image_file.read()
        
        # Initialize Kindwise API client for this request
        print(f"Initializing Kindwise API with key: {KINDWISE_API_KEY[:10]}...")
        
        # Use CropHealthApi (as in your Colab code)
        current_api = CropHealthApi(api_key=KINDWISE_API_KEY)
        print("✓ Using CropHealthApi for disease identification")
        
        # Call Kindwise API
        print("Calling Kindwise Crop Health API...")
        identification = current_api.identify(
            image_data,
            details=['description', 'treatment', 'symptoms', 'severity'],
            language='en'
        )
        
        result = identification.result
        
        # CropHealthApi result structure
        # Get crop and disease suggestions
        crop_suggestions = []
        disease_suggestions = []
        
        if hasattr(result, 'crop') and result.crop:
            crop_suggestions = result.crop.suggestions if hasattr(result.crop, 'suggestions') else []
        
        if hasattr(result, 'disease') and result.disease:
            disease_suggestions = result.disease.suggestions if hasattr(result.disease, 'suggestions') else []
        
        print(f"Found {len(crop_suggestions)} crop suggestions and {len(disease_suggestions)} disease suggestions")
        
        # Debug: print what we got
        if crop_suggestions:
            print(f"Top crop: {crop_suggestions[0].name if crop_suggestions[0] else 'None'}")
        if disease_suggestions:
            print(f"Top disease: {disease_suggestions[0].name if disease_suggestions[0] else 'None'}")
            print(f"Disease probability: {disease_suggestions[0].probability if disease_suggestions[0] else 'None'}")
            # Debug disease details
            top_disease_debug = disease_suggestions[0]
            if hasattr(top_disease_debug, 'details') and top_disease_debug.details:
                print(f"Disease has details object")
                print(f"Details attributes: {dir(top_disease_debug.details)}")
                if hasattr(top_disease_debug.details, 'description'):
                    print(f"Details description: {top_disease_debug.details.description}")
                if hasattr(top_disease_debug.details, 'treatment'):
                    print(f"Details has treatment info")
        
        top_crop = crop_suggestions[0] if crop_suggestions else None
        top_disease = disease_suggestions[0] if disease_suggestions else None
        
        # Check if disease detected
        if not top_disease:
            print("⚠️ RETURNING HEALTHY RESPONSE - No disease detected")
            return jsonify({
                'success': True,
                'data': {
                    'isHealthy': True,
                    'disease': 'Healthy Plant',
                    'confidence': 95.0,
                    'severity': 'None',
                    'description': 'No disease detected. Your plant appears to be healthy!',
                    'crop': top_crop.name if top_crop else 'Unknown plant',
                    'recommendations': {
                        'chemicalTreatment': 'No treatment needed',
                        'organicTreatment': 'Continue regular care',
                        'immediateActions': ['Monitor regularly', 'Maintain good practices'],
                        'prevention': ['Proper watering', 'Good air circulation', 'Regular inspection'],
                        'timeline': 'Continue monitoring weekly',
                        'warningSigns': ['Yellowing leaves', 'Spots appearing', 'Wilting'],
                        'rawRecommendations': 'Plant is healthy. Continue good care practices.'
                    }
                }
            })
        
        # Get crop name
        crop_name = top_crop.name if top_crop else 'Unknown plant'
        disease_name = top_disease.name
        confidence = top_disease.probability
        
        # Get severity - CropHealthApi uses direct attribute
        severity = 'Moderate'
        if hasattr(top_disease, 'severity') and top_disease.severity:
            severity = top_disease.severity
        
        print(f"Severity attribute: {severity}")
        
        # Get description - try multiple ways
        description = f'{disease_name} detected on {crop_name}.'
        
        # Try to get description from various locations
        if hasattr(top_disease, 'description') and top_disease.description:
            description = top_disease.description
            print(f"✓ Got description from top_disease.description")
        elif hasattr(top_disease, 'details'):
            if hasattr(top_disease.details, 'description') and top_disease.details.description:
                description = top_disease.details.description
                print(f"✓ Got description from top_disease.details.description")
            elif hasattr(top_disease.details, 'common_names') and top_disease.details.common_names:
                description = f"Also known as: {', '.join(top_disease.details.common_names)}"
                print(f"✓ Got common names from details")
        
        # Fallback: create a meaningful description
        if description == f'{disease_name} detected on {crop_name}.':
            description = f'{disease_name} has been identified on your {crop_name} plant with {confidence:.1%} confidence.'
        
        print(f"Final description: {description[:100]}..." if len(description) > 100 else f"Final description: {description}")
        # return jsonify({
        #         'success': True,
        #         'data': {
        #             'isHealthy': True,
        #             'disease': 'Healthy Plant',
        #             'confidence': 95.0,
        #             'severity': 'None',
        #             'description': 'No disease detected. Your plant appears to be healthy!',
        #             'recommendations': {
        #                 'chemicalTreatment': 'No treatment needed',
        #                 'organicTreatment': 'Continue regular care',
        #                 'immediateActions': ['Monitor regularly', 'Maintain good practices'],
        #                 'prevention': ['Proper watering', 'Good air circulation', 'Regular inspection'],
        #                 'timeline': 'Continue monitoring weekly',
        #                 'warningSigns': ['Yellowing leaves', 'Spots appearing', 'Wilting'],
        #                 'rawRecommendations': 'Plant is healthy. Continue good care practices.'
        #             }
        #         }
        #     })
        print(f"Disease detected: {disease_name} ({confidence:.1%})")
        print(f"Crop: {crop_name}, Severity: {severity}")
        
        # Get treatment recommendations from Gemini
        print("Getting treatment recommendations from Gemini...")
        recommendations = get_treatment_recommendations(disease_name, crop_name, severity)
        
        print("✓ Recommendations received")
        
        response_data = {
            'isHealthy': False,
            'disease': disease_name,
            'crop': crop_name,
            'confidence': round(confidence * 100, 2),
            'severity': severity.capitalize() if severity else 'Moderate',
            'description': description,
            'recommendations': recommendations,
            'timestamp': str(result.created_at) if hasattr(result, 'created_at') else None
        }
        
        print("\n" + "="*70)
        print("RESPONSE DATA BEING SENT:")
        print(f"isHealthy: {response_data['isHealthy']}")
        print(f"disease: {response_data['disease']}")
        print(f"crop: {response_data['crop']}")
        print(f"confidence: {response_data['confidence']}%")
        print(f"severity: {response_data['severity']}")
        print(f"description: {response_data['description'][:80]}...")
        print("="*70 + "\n")
        
        print("Sending JSON response...")
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        print(f"❌ Error in diagnose_disease: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Diagnosis failed: {str(e)}'
        }), 500

# ==========================================
# HEALTH CHECK & INFO ENDPOINTS
# ==========================================

@app.route('/')
def index():
    """API information endpoint"""
    return jsonify({
        'status': 'Smart Farming API Running',
        'version': '2.0',
        'endpoints': {
            'crop_identification': '/predict',
            'disease_diagnosis': '/api/diagnose-disease',
            'health_check': '/health'
        },
        'apis_configured': {
            'gemini': GEMINI_API_KEY is not None,
            'kindwise': KINDWISE_API_KEY is not None,
            'crop_model': os.path.exists(model_path)
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'gemini_api': 'configured' if GEMINI_API_KEY else 'missing',
        'kindwise_api': 'configured' if KINDWISE_API_KEY else 'missing',
        'kindwise_api_key_length': len(KINDWISE_API_KEY) if KINDWISE_API_KEY else 0,
        'crop_model': 'loaded' if model else 'error'
    })

@app.route('/test-kindwise')
def test_kindwise():
    """Test Kindwise API key validity"""
    if not KINDWISE_API_KEY:
        return jsonify({
            'status': 'error',
            'message': 'Kindwise API key not configured'
        }), 500
    
    try:
        # Try to initialize the API
        test_api = PlantApi(api_key=KINDWISE_API_KEY)
        return jsonify({
            'status': 'success',
            'message': 'Kindwise API key is valid and loaded',
            'api_key_preview': KINDWISE_API_KEY[:10] + '...' + KINDWISE_API_KEY[-5:] if len(KINDWISE_API_KEY) > 15 else 'too_short'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to initialize Kindwise API: {str(e)}',
            'api_key_preview': KINDWISE_API_KEY[:10] + '...' if len(KINDWISE_API_KEY) > 10 else KINDWISE_API_KEY
        }), 500

# ==========================================
# RUN SERVER
# ==========================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "="*70)
    print("🚀 Smart Farming API Server Starting...")
    print("="*70)
    print(f"📡 Port: {port}")
    print(f"🔑 Gemini API: {'✓ Configured' if GEMINI_API_KEY else '✗ Missing'}")
    print(f"🔑 Kindwise API: {'✓ Configured' if KINDWISE_API_KEY else '✗ Missing'}")
    print(f"🤖 Crop Model: {'✓ Loaded' if model else '✗ Error'}")
    print("\n📋 Available Endpoints:")
    print("   • POST /predict - Crop Identification")
    print("   • POST /api/diagnose-disease - Disease Diagnosis")
    print("   • GET  /health - Health Check")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=True)






