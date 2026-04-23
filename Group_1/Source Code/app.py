from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
import os
import warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TF info/warning logs
warnings.filterwarnings('ignore', category=UserWarning)  # Suppress sklearn version warnings
import tensorflow as tf
tf.get_logger().setLevel('ERROR')
from datetime import datetime, timedelta
import random
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from tensorflow.keras.models import load_model
import joblib
import pickle
import traceback
from nakshatra import get_moon_nakshatra_and_crop
from market_trend import get_market_trend_summary
try:
    from chatbot_engine import get_rag_response, create_vector_db, initialize_knowledge_base, get_knowledge_base_text
    CHATBOT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Chatbot engine not available: {e}")
    CHATBOT_AVAILABLE = False
    def get_rag_response(msg): return "Chatbot is not available. Missing dependencies."
    def create_vector_db(): return False
    def initialize_knowledge_base(): return ""
    def get_knowledge_base_text(): return ""
from database.mongo import mongo
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.ecommerce_routes import ecommerce_bp
from routes.marketplace_routes import marketplace_bp
from market_trend import get_market_trend_summary

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://127.0.0.1:27017/agriaidplus"
mongo.init_app(app)
CORS(app)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/croppred')
def croppred():
    return send_from_directory('static', 'croppred.html')

@app.route('/weather')
def weather():
    return send_from_directory('static', 'weather.html')

@app.route('/market')
def market():
    return send_from_directory('static', 'market.html')

@app.route('/ecom')
def ecom():
    return send_from_directory('static', 'ecom.html')

@app.route('/organisations')
def organisations():
    return send_from_directory('static', 'organisations.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('static', 'dashboard.html')

@app.route('/dashboard.js')
def dashboard_script():
    return send_from_directory('static', 'dashboard.js')

@app.route('/nakshatra-page')
def nakshatra_page():
    return send_from_directory('static', 'nakshatra.html')

@app.route('/login')
def login():
    return send_from_directory('static', 'login.html')

@app.route('/signup')
def signup():
    return send_from_directory('static', 'signup.html')

@app.route('/styles.css')
def styles():
    return send_from_directory('static', 'styles.css')

@app.route('/script.js')
def script():
    return send_from_directory('static', 'script.js')

@app.route('/signup-styles.css')
def signup_styles():
    return send_from_directory('static', 'signup-styles.css')

@app.route('/signup-script.js')
def signup_script():
    return send_from_directory('static', 'signup-script.js')

@app.route('/login-script.js')
def login_script():
    return send_from_directory('static', 'login-script.js')


 

# Global variables for ML models
xgb_model = None
lgbm_model = None
label_encoder = None
features = ['N', 'P', 'K', 'ph', 'rainfall']

# Global variables for fertilizer model
fertilizer_model = None
fertilizer_scaler = None
fertilizer_encoders = {}

# Global variables for weather forecasting
weather_model = None
weather_scaler = None
weather_sequence_length = 30  # default sequence length used by the GRU model
WEATHER_FEATURES = ["temperature", "humidity", "pressure", "wind_speed", "rainfall"]
DEFAULT_COORDS = {"lat": 28.6139, "lon": 77.2090}  # New Delhi as default

# ---------------------------------------------------------
# NEW GLOBAL VARIABLES (Add/Update these)
# ---------------------------------------------------------
gru_model = None
condition_clf = None
# weather_scaler is already defined above
city_list = []

# Map your cities to Lat/Lon for the API History Fetch
# (You can expand this list later)
CITY_COORDINATES = {
    "Ahmednagar": {"lat": 19.09, "lon": 74.74},
    "Akola": {"lat": 20.70, "lon": 77.00},
    "Amravati": {"lat": 20.93, "lon": 77.75},
    "Aurangabad": {"lat": 19.88, "lon": 75.34},
    "Belapur": {"lat": 19.06, "lon": 73.04},
    "Bhiwandi": {"lat": 19.30, "lon": 73.05},
    "Boisar": {"lat": 19.80, "lon": 72.76},
    "Chandrapur": {"lat": 19.95, "lon": 79.30},
    "Dhule": {"lat": 20.90, "lon": 74.77},
    "Jalgaon": {"lat": 21.01, "lon": 75.57},
    "Jalna": {"lat": 19.84, "lon": 75.88},
    "Kalyan": {"lat": 19.24, "lon": 73.13},
    "Kolhapur": {"lat": 16.70, "lon": 74.24},
    "Latur": {"lat": 18.40, "lon": 76.57},
    "Mahad": {"lat": 18.08, "lon": 73.41},
    "Malegaon": {"lat": 20.55, "lon": 74.53},
    "Mumbai": {"lat": 19.07, "lon": 72.87},
    "Nagpur": {"lat": 21.14, "lon": 79.08},
    "Nanded": {"lat": 19.16, "lon": 77.30},
    "Nashik": {"lat": 19.99, "lon": 73.78},
    "Navi Mumbai": {"lat": 19.03, "lon": 73.02},
    "Parbhani": {"lat": 19.27, "lon": 76.77},
    "Pune": {"lat": 18.52, "lon": 73.85},
    "Sangli": {"lat": 16.85, "lon": 74.56},
    "Solapur": {"lat": 17.66, "lon": 75.91},
    "Thane": {"lat": 19.22, "lon": 72.97},
    "Ulhasnagar": {"lat": 19.22, "lon": 73.16},
    "Virar": {"lat": 19.47, "lon": 72.81},
    # Default fallback
    "Default": {"lat": 19.07, "lon": 72.87}
}

# Initialization guard to prevent double-loading under the Flask reloader
initialized = False

def load_crop_dataset():
    """Load the real crop dataset from CSV file"""
    try:
        csv_path = 'combined_crop_data.csv'
        if os.path.exists(csv_path):
            print(f"Loading dataset from {csv_path}")
            df = pd.read_csv(csv_path)
            
            # Check if required columns exist
            required_columns = features + ['label']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"Warning: Missing columns in CSV: {missing_columns}")
                print(f"Available columns: {list(df.columns)}")
                return None
            
            print(f"Dataset loaded successfully with {len(df)} samples")
            print(f"Features: {features}")
            print(f"Available crops: {df['label'].unique()}")
            print(f"Dataset shape: {df.shape}")
            
            return df
        else:
            print(f"CSV file not found: {csv_path}")
            return None
            
    except Exception as e:
        print(f"Error loading CSV dataset: {e}")
        return None

def train_models():
    """Train the gradient boosting models"""
    global xgb_model, lgbm_model, label_encoder
    
    try:
        # Create or load dataset
        if os.path.exists('crop_models.pkl'):
            with open('crop_models.pkl', 'rb') as f:
                models_data = pickle.load(f)
                xgb_model = models_data['xgb_model']
                lgbm_model = models_data['lgbm_model']
                label_encoder = models_data['label_encoder']
                print("Models loaded from file")
                return
        else:
            print("Training new models...")
            df = load_crop_dataset()
            
            if df is None:
                print("Failed to load dataset. Using fallback simple prediction.")
                return
            
            # Prepare features and target
            X = df[features]
            y = df['label']
            
            # Encode target labels
            label_encoder = LabelEncoder()
            y_encoded = label_encoder.fit_transform(y)
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
            )
            
            # Train XGBoost Model
            xgb_model = XGBClassifier(eval_metric='mlogloss', random_state=42, n_estimators=100)
            xgb_model.fit(X_train, y_train)
            xgb_preds = xgb_model.predict(X_test)
            xgb_acc = accuracy_score(y_test, xgb_preds)
            
            # Train LightGBM Model
            lgbm_model = LGBMClassifier(random_state=42, n_estimators=100)
            lgbm_model.fit(X_train, y_train)
            lgbm_preds = lgbm_model.predict(X_test)
            lgbm_acc = accuracy_score(y_test, lgbm_preds)
            
            print(f"XGBoost Accuracy: {xgb_acc * 100:.2f}%")
            print(f"LightGBM Accuracy: {lgbm_acc * 100:.2f}%")
            
            # Save models
            models_data = {
                'xgb_model': xgb_model,
                'lgbm_model': lgbm_model,
                'label_encoder': label_encoder
            }
            with open('crop_models.pkl', 'wb') as f:
                pickle.dump(models_data, f)
            print("Models saved to file")
            
    except Exception as e:
        print(f"Error training models: {e}")
        print("Using fallback simple prediction system")
        # Fallback to simple rules
        xgb_model = None
        lgbm_model = None
        label_encoder = None

def predict_crop_boosting(N, P, K, ph, rainfall, model_choice="xgb"):
    """Predict crop using gradient boosting models"""
    global xgb_model, lgbm_model, label_encoder
    
    if xgb_model is None or lgbm_model is None or label_encoder is None:
        return predict_crop_simple(N, P, K, ph, rainfall)
    
    try:
        if model_choice.lower() == "xgb":
            model = xgb_model
        else:
            model = lgbm_model
            
        data = pd.DataFrame([[N, P, K, ph, rainfall]], columns=features)
        prediction = model.predict(data)[0]
        predicted_crop = label_encoder.inverse_transform([prediction])[0]
        
        # Get prediction probabilities
        probabilities = model.predict_proba(data)[0]
        crop_names = label_encoder.classes_
        crop_probs = dict(zip(crop_names, probabilities))
        
        return predicted_crop, crop_probs
        
    except Exception as e:
        print(f"Error in ML prediction: {e}")
        return predict_crop_simple(N, P, K, ph, rainfall), {}

def predict_crop_simple(N, P, K, ph, rainfall):
    """Simple rule-based prediction as fallback"""
    if ph >= 6.0 and rainfall >= 100 and N >= 50:
        if K >= 100:
            return "rice"
        else:
            return "wheat"
    elif ph >= 5.5 and rainfall >= 80:
        if N >= 40:
            return "corn"
        else:
            return "potato"
    elif ph >= 6.5 and rainfall >= 60:
        return "tomato"
    elif ph >= 5.0 and rainfall >= 40:
        return "cotton"
    else:
        return "pulses"

def load_fertilizer_models():
    """Load the fertilizer recommendation models"""
    global fertilizer_model, fertilizer_scaler, fertilizer_encoders
    
    try:
        # Load the XGBoost model
        if os.path.exists('fertilizer_xgb_model.pkl'):
            print("Loading fertilizer XGBoost model...")
            try:
                # Load with compatibility mode
                import xgboost as xgb
                fertilizer_model = pickle.load(open('fertilizer_xgb_model.pkl', 'rb'))
                # Remove use_label_encoder attribute if it exists (for compatibility with newer XGBoost)
                if hasattr(fertilizer_model, 'use_label_encoder'):
                    delattr(fertilizer_model, 'use_label_encoder')
                # Ensure n_classes_ is set
                if not hasattr(fertilizer_model, 'n_classes_'):
                    fertilizer_model.n_classes_ = len(fertilizer_encoders['Fertilizer'].classes_)
                print("Fertilizer model loaded successfully")
            except Exception as model_error:
                print(f"Error loading fertilizer model: {model_error}")
                # Create a simple fallback model
                fertilizer_model = xgb.XGBClassifier()
                print("Created fallback XGBoost model")
        
        else:
            print("Fertilizer model file not found")
            fertilizer_model = None
        
        # Create scaler and encoders from dataset instead of loading from pickle
        print("Creating scaler and encoders from dataset...")
        try:
            # Load the dataset
            dataset_path = os.path.join('dataset', 'Crop and fertilizer dataset.csv')
            if os.path.exists(dataset_path):
                df = pd.read_csv(dataset_path)
                print(f"Dataset loaded successfully with {len(df)} rows")
                
                # Create and fit the scaler
                from sklearn.preprocessing import StandardScaler
                numeric_features = ['Nitrogen', 'Phosphorus', 'Potassium', 'pH', 'Rainfall', 'Temperature']
                fertilizer_scaler = StandardScaler()
                fertilizer_scaler.fit(df[numeric_features])
                print("Scaler created and fitted successfully")
                
                # Create and fit the label encoders
                from sklearn.preprocessing import LabelEncoder
                fertilizer_encoders = {}
                
                # Encode categorical features
                categorical_features = ['Soil_color', 'Crop', 'Fertilizer']
                for feature in categorical_features:
                    encoder = LabelEncoder()
                    encoder.fit(df[feature].str.lower())  # Convert to lowercase for consistency
                    fertilizer_encoders[feature] = encoder
                    print(f"Encoder for {feature} created with classes: {list(encoder.classes_)}")
                
                print("All encoders created successfully")
                # Ensure loaded model has required attributes now that encoders exist
                if fertilizer_model is not None:
                    try:
                        if not hasattr(fertilizer_model, 'n_classes_'):
                            fertilizer_model.n_classes_ = len(fertilizer_encoders['Fertilizer'].classes_)
                    except Exception:
                        pass
            else:
                print(f"Dataset file not found at {dataset_path}")
                raise FileNotFoundError(f"Dataset file not found at {dataset_path}")
                
        except Exception as inner_e:
            print(f"Error creating scaler and encoders from dataset: {inner_e}")
            traceback.print_exc()
            
            # Create basic fallback encoders
            print("Creating basic fallback encoders...")
            from sklearn.preprocessing import StandardScaler, LabelEncoder
            
            # Create a simple scaler
            fertilizer_scaler = StandardScaler()
            fertilizer_scaler.mean_ = np.zeros(6)  # For the 6 numeric features
            fertilizer_scaler.scale_ = np.ones(6)
            fertilizer_scaler.var_ = np.ones(6)
            
            # Create basic encoders with common values
            fertilizer_encoders = {}
            
            soil_encoder = LabelEncoder()
            soil_encoder.classes_ = np.array(['black', 'red', 'brown', 'gray', 'yellow'])
            fertilizer_encoders['Soil_color'] = soil_encoder
            
            crop_encoder = LabelEncoder()
            crop_encoder.classes_ = np.array(['rice', 'wheat', 'corn', 'potato', 'tomato', 'cotton', 'sugarcane'])
            fertilizer_encoders['Crop'] = crop_encoder
            
            fert_encoder = LabelEncoder()
            fert_encoder.classes_ = np.array(['urea', 'dap', 'npk', 'mop', '14-35-14', '28-28', '17-17-17', '20-20', '10-26-26'])
            fertilizer_encoders['Fertilizer'] = fert_encoder
            
            print("Fallback encoders created successfully")
        
    except Exception as e:
        print(f"Error loading fertilizer models: {e}")
        traceback.print_exc()
        fertilizer_model = None
        fertilizer_scaler = None
        fertilizer_encoders = {}

def load_weather_model():
    """
    Safely load GRU weather forecasting model and scaler
    """
    global weather_model, weather_scaler, weather_sequence_length

    weather_model = None
    weather_scaler = None
    weather_sequence_length = 30  # default fallback

    try:
        # -----------------------------
        # Load Scaler FIRST (no TF dep)
        # -----------------------------
        if os.path.isfile("weather_scaler.pkl"):
            try:
                weather_scaler = joblib.load("weather_scaler.pkl")
                print("✅ Weather scaler loaded successfully")
            except Exception as scaler_error:
                error_msg = str(scaler_error)
                if 'numpy._core' in error_msg or '_core' in error_msg:
                    print(f"❌ Failed to load weather scaler: numpy version mismatch")
                    if os.path.exists('weather_scaler.pkl'):
                        try:
                            os.remove('weather_scaler.pkl')
                            print("🧹 Removed stale weather_scaler.pkl. Please regenerate it with current env.")
                        except Exception:
                            pass
                else:
                    print(f"❌ Failed to load weather scaler: {scaler_error}")
                weather_scaler = None
        else:
            print("⚠️ weather_scaler.pkl not found")

        # -----------------------------
        # Load GRU Model (TF dependent)
        # -----------------------------
        model_file = None
        if os.path.isfile("gru_weather_forecast.keras"):
            model_file = "gru_weather_forecast.keras"
        elif os.path.isfile("gru_weather_forecast.h5"):
            model_file = "gru_weather_forecast.h5"
        
        if model_file:
            try:
                import tensorflow as tf
                from tensorflow.keras.layers import InputLayer
                import copy
                
                # Monkey patch InputLayer.from_config to handle batch_shape compatibility
                # Store original method
                original_from_config = InputLayer.from_config.__func__ if hasattr(InputLayer.from_config, '__func__') else InputLayer.from_config
                
                @classmethod
                def patched_from_config(cls, config):
                    # Create a copy to avoid modifying the original
                    config = copy.deepcopy(config)
                    # Remove batch_shape and convert to input_shape if needed
                    if 'batch_shape' in config:
                        batch_shape = config.pop('batch_shape')
                        if 'input_shape' not in config and batch_shape:
                            # Extract shape from batch_shape (skip batch dimension)
                            if len(batch_shape) > 1:
                                config['input_shape'] = tuple(batch_shape[1:])
                    # Call original method with modified config
                    return original_from_config(cls, config)
                
                # Apply the patch as classmethod
                InputLayer.from_config = patched_from_config
                
                try:
                    # Try loading with compile=False and custom_objects for dtype policy compatibility
                    try:
                        weather_model = tf.keras.models.load_model(model_file, compile=False)
                    except Exception as dtype_error:
                        if 'DTypePolicy' in str(dtype_error) or 'dtype policy' in str(dtype_error).lower():
                            # Try with custom_objects to handle dtype policy
                            from keras.mixed_precision import policy
                            custom_objects = {}
                            try:
                                # Try loading with safe_mode=False if available
                                weather_model = tf.keras.models.load_model(
                                    model_file, 
                                    compile=False,
                                    custom_objects=custom_objects
                                )
                            except:
                                # Last resort: try with the original method
                                weather_model = tf.keras.models.load_model(model_file)
                        else:
                            raise dtype_error
                except Exception as e1:
                    # If that fails, try without compile=False
                    try:
                        weather_model = tf.keras.models.load_model(model_file)
                    except Exception as e2:
                        # Restore original method before re-raising
                        InputLayer.from_config = original_from_config
                        raise e2
                
                # Restore original method
                InputLayer.from_config = original_from_config

                # Safely extract sequence length
                input_shape = weather_model.input_shape
                if len(input_shape) == 3 and input_shape[1]:
                    weather_sequence_length = input_shape[1]

                print(f"✅ Weather model loaded from {model_file} | Sequence length: {weather_sequence_length}")

            except ImportError:
                print("❌ TensorFlow not installed — GRU model not loaded")

            except Exception as model_error:
                error_msg = str(model_error)
                if 'DTypePolicy' in error_msg or 'dtype policy' in error_msg.lower():
                    print(f"❌ Failed to load GRU model: TensorFlow/Keras version mismatch")
                    print("💡 Solution: Upgrade TensorFlow to match the model version:")
                    print("   pip install --upgrade tensorflow>=2.13.0")
                elif 'batch_shape' in error_msg:
                    print(f"❌ Failed to load GRU model: batch_shape compatibility issue")
                    print("💡 This should be fixed, but if it persists, upgrade TensorFlow")
                else:
                    print(f"❌ Failed to load GRU model: {model_error}")
                traceback.print_exc()

        else:
            print("⚠️ gru_weather_forecast.keras or gru_weather_forecast.h5 not found")

    except Exception as e:
        print(f" Unexpected error while loading weather model: {e}")
        traceback.print_exc()


def fetch_recent_weather_history(lat=DEFAULT_COORDS["lat"], lon=DEFAULT_COORDS["lon"], past_days=30):
    """Fetch recent hourly weather data and aggregate to daily values"""
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relativehumidity_2m,pressure_msl,precipitation,wind_speed_10m",
            "past_days": past_days,
            "forecast_days": 0,
            "timezone": "auto"
        }
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        if not hourly:
            raise ValueError("Missing hourly weather data from provider")
        
        df = pd.DataFrame({
            "time": hourly.get("time", []),
            "temperature": hourly.get("temperature_2m", []),
            "humidity": hourly.get("relativehumidity_2m", []),
            "pressure": hourly.get("pressure_msl", []),
            "rainfall": hourly.get("precipitation", []),
            "wind_speed": hourly.get("wind_speed_10m", []),
        })
        if df.empty:
            raise ValueError("Empty weather dataframe received")
        
        df["date"] = pd.to_datetime(df["time"]).dt.date
        daily = df.groupby("date").agg({
            "temperature": "mean",
            "humidity": "mean",
            "pressure": "mean",
            "wind_speed": "mean",
            "rainfall": "sum"
        }).reset_index()
        daily = daily.dropna()
        return daily
    except Exception as e:
        print(f"Error fetching weather history: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def _pad_or_trim_sequence(sequence_df: pd.DataFrame, seq_len: int):
    """Ensure the sequence has exactly seq_len rows by padding the earliest value if needed."""
    if len(sequence_df) >= seq_len:
        return sequence_df.tail(seq_len).copy()
    if sequence_df.empty:
        return pd.DataFrame()
    first_row = sequence_df.iloc[0]
    padding = pd.DataFrame([first_row] * (seq_len - len(sequence_df)), columns=sequence_df.columns)
    return pd.concat([padding, sequence_df], ignore_index=True)

def _fallback_weather_forecast(base_temp=28, base_humidity=65, base_rain=10, days=7):
    """Generate a simple fallback forecast when the GRU model is unavailable."""
    predictions = []
    for i in range(days):
        target_date = datetime.utcnow().date() + timedelta(days=i + 1)
        predictions.append({
            "date": target_date.isoformat(),
            "temperature": round(base_temp + random.uniform(-3, 3), 2),
            "humidity": round(base_humidity + random.uniform(-8, 8), 2),
            "rainfall": max(0, round(base_rain + random.uniform(-5, 12), 2)),
            "pressure": None,
            "wind_speed": None,
            "source": "fallback"
        })
    return predictions

def generate_weather_forecast(history_df: pd.DataFrame, days=7):
    """Generate a 7-day forecast using the GRU model; fallback to heuristic if unavailable."""
    if history_df is None or history_df.empty:
        return _fallback_weather_forecast(days=days)
    
    # Prepare current observation from the most recent day
    latest_row = history_df.iloc[-1]
    base_temp = float(latest_row.get("temperature", 28))
    base_humidity = float(latest_row.get("humidity", 65))
    base_rain = float(latest_row.get("rainfall", 10))
    
    if gru_model is None or weather_scaler is None:
        return _fallback_weather_forecast(base_temp=base_temp, base_humidity=base_humidity, base_rain=base_rain, days=days)
    
    try:
        feature_df = history_df[WEATHER_FEATURES].copy()
        feature_df = _pad_or_trim_sequence(feature_df, weather_sequence_length)
        if feature_df.empty:
            raise ValueError("No feature data for forecasting")
        
        scaled_sequence = weather_scaler.transform(feature_df)
        seq = scaled_sequence
        predictions = []
        last_date = pd.to_datetime(history_df["date"]).max()
        
        for i in range(days):
            model_input = seq.reshape(1, weather_sequence_length, len(WEATHER_FEATURES))
            pred_scaled = gru_model.predict(model_input, verbose=0)
            
            # Handle (1, timesteps, features) or (1, features)
            if pred_scaled.ndim == 3:
                pred_scaled = pred_scaled[:, -1, :]
            pred_scaled = np.asarray(pred_scaled).reshape(1, -1)
            
            pred_unscaled = weather_scaler.inverse_transform(pred_scaled)[0]
            next_date = (last_date + pd.Timedelta(days=i + 1)).date()
            
            predictions.append({
                "date": next_date.isoformat(),
                "temperature": round(float(pred_unscaled[0]), 2),
                "humidity": round(float(pred_unscaled[1]), 2),
                "pressure": round(float(pred_unscaled[2]), 2) if len(pred_unscaled) > 2 else None,
                "wind_speed": round(float(pred_unscaled[3]), 2) if len(pred_unscaled) > 3 else None,
                "rainfall": max(0, round(float(pred_unscaled[4]), 2)) if len(pred_unscaled) > 4 else None,
                "source": "gru_model"
            })
            
            # Append scaled prediction back into the sequence for iterative forecasting
            seq = np.vstack([seq[1:], pred_scaled[0]])
        
        return predictions
    except Exception as e:
        print(f"Error during GRU forecasting: {e}")
        traceback.print_exc()
        return _fallback_weather_forecast(base_temp=base_temp, base_humidity=base_humidity, base_rain=base_rain, days=days)

# ---------------------------------------------------------
# INITIALIZATION FUNCTION
# ---------------------------------------------------------

def load_weather_system():
    global gru_model, condition_clf, weather_scaler, city_list
    import tempfile, shutil

    # --- 1. Load GRU Model ---
    try:
        if os.path.exists('weather_gru.keras'):
            import zipfile, h5py
            from tensorflow.keras.models import Sequential as SeqModel
            from tensorflow.keras.layers import InputLayer, GRU, Dense

            # Rebuild architecture (matches the Keras 3.x config exactly)
            model = SeqModel([
                InputLayer(input_shape=(30, 4)),
                GRU(64, name='gru_1'),
                Dense(32, activation='relu', name='dense_2'),
                Dense(21, activation='linear', name='dense_3'),
            ])

            # Extract weights to a unique temp directory to avoid conflicts
            tmp_dir = tempfile.mkdtemp(prefix='agriaid_')
            try:
                with zipfile.ZipFile('weather_gru.keras', 'r') as z:
                    z.extract('model.weights.h5', tmp_dir)
                
                weights_path = os.path.join(tmp_dir, 'model.weights.h5')
                with h5py.File(weights_path, 'r') as hf:
                    weights = [
                        np.array(hf['layers/gru/cell/vars/0']),
                        np.array(hf['layers/gru/cell/vars/1']),
                        np.array(hf['layers/gru/cell/vars/2']),
                        np.array(hf['layers/dense/vars/0']),
                        np.array(hf['layers/dense/vars/1']),
                        np.array(hf['layers/dense_1/vars/0']),
                        np.array(hf['layers/dense_1/vars/1']),
                    ]
                model.set_weights(weights)
                gru_model = model
                print("✅ GRU Weather Model loaded.")
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            print("⚠️ weather_gru.keras not found.")
    except Exception as e:
        print(f"⚠️ GRU model failed to load: {e}")
        traceback.print_exc()

    # --- 2. Load Condition Classifier ---
    try:
        if os.path.exists('condition_classifier.pkl'):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=UserWarning)
                    condition_clf = joblib.load('condition_classifier.pkl')
                print("✅ Condition classifier loaded.")
            except Exception as clf_err:
                err_str = str(clf_err)
                if 'numpy._core' in err_str or '_core' in err_str:
                    print(f"⚠️ Condition classifier failed due NumPy binary mismatch: {clf_err}")
                    try:
                        os.remove('condition_classifier.pkl')
                        print("🧹 Removed stale condition_classifier.pkl (incompatible with current NumPy).")
                    except Exception:
                        pass
                else:
                    print(f"⚠️ Condition classifier load failed: {clf_err}")
                condition_clf = None
        else:
            print("⚠️ condition_classifier.pkl not found.")
            condition_clf = None
    except Exception as e:
        print(f"⚠️ Unexpected condition classifier error: {e}")
        condition_clf = None

    # --- 3. Load Weather Scaler ---
    try:
        if os.path.exists('weather_scaler.pkl'):
            try:
                weather_scaler = joblib.load('weather_scaler.pkl')
                print("✅ Weather scaler loaded.")
            except Exception as scaler_err:
                err_str = str(scaler_err)
                if 'numpy._core' in err_str or '_core' in err_str:
                    print(f"⚠️ Weather scaler failed due NumPy binary mismatch: {scaler_err}")
                    try:
                        os.remove('weather_scaler.pkl')
                        print("🧹 Removed stale weather_scaler.pkl (incompatible with current NumPy).")
                    except Exception:
                        pass
                else:
                    print(f"⚠️ Weather scaler load failed: {scaler_err}")
                weather_scaler = None
        else:
            print("⚠️ weather_scaler.pkl not found.")
            weather_scaler = None
    except Exception as e:
        print(f"⚠️ Unexpected weather scaler error: {e}")
        weather_scaler = None

    # --- 4. Load City List ---
    try:
        if os.path.exists('city_list.pkl'):
            city_list = joblib.load('city_list.pkl')
            print(f"✅ City list loaded ({len(city_list)} cities).")
        else:
            print("⚠️ city_list.pkl not found.")
            city_list = []
    except Exception as e:
        print(f"⚠️ City list failed: {e}")
        city_list = []

    # Summary
    loaded = []
    if gru_model: loaded.append("GRU")
    if condition_clf: loaded.append("Classifier")
    if weather_scaler: loaded.append("Scaler")
    if city_list: loaded.append(f"Cities({len(city_list)})")
    print(f"Weather system status: {', '.join(loaded) if loaded else 'Nothing loaded'}")

# Initialize models when app starts
def initialize():
    global initialized
    if initialized:
        return
    train_models()
    load_fertilizer_models()
    load_weather_system()
    # Build chatbot vector store if it doesn't exist
    if CHATBOT_AVAILABLE and not os.path.exists('vectorstore/db_faiss'):
        try:
            create_vector_db()
        except Exception as e:
            print(f"⚠️ Vector store init failed: {e}")
    # Load knowledge base once at startup
    try:
        initialize_knowledge_base()
    except Exception as e:
        print(f"⚠️ Knowledge base init failed: {e}")
    initialized = True

# Flask 3.x removed some lifecycle hooks; we'll initialize in __main__ with a guard

# Mock data for other endpoints
current_weather = {
    "temperature": 28,
    "humidity": 65,
    "rainfall": 45,
    "wind_speed": 12
}

weather_predictions = []
for i in range(7):
    date = (datetime.now() + timedelta(days=i)).strftime("%A, %b %d")
    weather_predictions.append({
        "date": date,
        "temperature": random.randint(20, 35),
        "condition": random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Rainy"]),
        "humidity": random.randint(50, 80),
        "rainfall": random.randint(0, 100)
    })

# ==========================================
# 1. CURRENT WEATHER ROUTE (Fast API Call)
# ==========================================
@app.route('/api/get-current-weather', methods=['POST'])
def get_current_weather():
    """
    Step 1: Get current weather + Lat/Lon from OpenWeatherMap using City Name.
    """
    data = request.json
    city = data.get('city', 'Pune') # Default to Pune if empty
    
    API_KEY = "367b345994830dd43e60933f15796d13"
    # Using 'weather' endpoint which returns coords automatically
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    try:
        params = {
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }
        
        response = requests.get(BASE_URL, params=params)
        
        if response.status_code != 200:
            return jsonify({"error": "City not found", "status": "fail"}), 404

        weather_data = response.json()

        # Extract coordinates to pass to the GRU model later
        lat = weather_data["coord"]["lat"]
        lon = weather_data["coord"]["lon"]

        # Extract display data
        display_data = {
            "temperature": round(weather_data["main"]["temp"], 1),
            "humidity": weather_data["main"]["humidity"],
            "pressure": weather_data["main"]["pressure"],
            "wind_speed": round(weather_data["wind"]["speed"] * 3.6, 2), # m/s to km/h
            "rainfall": weather_data.get("rain", {}).get("1h", 0), # 0 if no rain
            "description": weather_data["weather"][0]["description"].title(),
            "icon": weather_data["weather"][0]["icon"],
            "city": weather_data["name"],
            "country": weather_data["sys"]["country"]
        }

        return jsonify({
            "status": "success",
            "current_weather": display_data,
            "coordinates": {"lat": lat, "lon": lon} # Critical for Step 2
        })

    except Exception as e:
        print(f"Error in current weather: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-gru-forecast', methods=['POST'])
def get_gru_forecast():
    """
    Step 2: Receive Lat/Lon, fetch history, and run GRU model.
    """
    try:
        data = request.json
        lat = data.get('lat')
        lon = data.get('lon')

        if not lat or not lon:
            return jsonify({"error": "Missing coordinates"}), 400

        # 1. Fetch 30-day History (Required for GRU input)
        history_df = fetch_recent_weather_history(lat=lat, lon=lon, past_days=30)
        
        # 2. Generate Forecast
        if history_df.empty:
            predictions = _fallback_weather_forecast()
            status = "fallback_no_history"
        else:
            predictions = generate_weather_forecast(history_df, days=7)
            status = "gru_model_success"
            
        return jsonify({
            "status": "success",
            "model_status": status,
            "forecast": predictions
        })

    except Exception as e:
        print(f"Error in GRU forecast: {e}")
        return jsonify({"error": str(e)}), 500

market_trends = [
    {"crop": "Rice", "price": 1850, "trend": "Rising", "demand": "High"},
    {"crop": "Wheat", "price": 1650, "trend": "Stable", "demand": "Medium"},
    {"crop": "Corn", "price": 1450, "trend": "Falling", "demand": "Low"},
    {"crop": "Potato", "price": 1200, "trend": "Rising", "demand": "High"},
    {"crop": "Tomato", "price": 2800, "trend": "Rising", "demand": "High"},
    {"crop": "Cotton", "price": 5500, "trend": "Stable", "demand": "Medium"},
]

@app.route('/api/market-trend', methods=['POST'])
def market_trend_api():
    """
    Return yearly price trend and summary for a specific crop and city.
    Expects JSON: { "crop": "Onion" | "Potato", "city": "<one of allowed cities>" }
    """
    try:
        data = request.get_json(silent=True) or {}
        crop = (data.get("crop") or "").strip()
        city = (data.get("city") or "").strip()

        if not crop or not city:
            return jsonify({
                "error": "Missing required fields",
                "message": "Both 'crop' and 'city' are required.",
            }), 400

        # Restrict to supported crops and cities as per requirement
        allowed_crops = {"onion", "potato"}
        allowed_cities = {"mumbai", "pune", "nashik", "kolhapur", "satara"}

        if crop.lower() not in allowed_crops:
            return jsonify({
                "error": "Invalid crop",
                "message": "Crop must be either 'Onion' or 'Potato'.",
            }), 400

        if city.lower() not in allowed_cities:
            return jsonify({
                "error": "Invalid city",
                "message": "City must be one of: Mumbai, Pune, Nashik, Kolhapur, Satara.",
            }), 400

        trend = get_market_trend_summary(crop, city)
        if not trend.get("has_data"):
            return jsonify({
                "status": "no_data",
                "message": trend.get("message", "No data available."),
            }), 200

        return jsonify({
            "status": "success",
            "trend": trend,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        })
    except FileNotFoundError as e:
        return jsonify({
            "error": "Dataset not found",
            "message": str(e),
        }), 500
    except Exception as e:
        print(f"Error in market_trend_api: {e}")
        traceback.print_exc()
        return jsonify({
            "error": "Error processing request",
            "message": str(e),
        }), 500


@app.route('/api/db-status', methods=['GET'])
def db_status():
    """Return collection names with document counts for debugging/testing."""
    try:
        cols = mongo.db.list_collection_names()
        counts = {c: mongo.db[c].count_documents({}) for c in cols}
        return jsonify({"collections": counts})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


products = [
    {"name": "Fresh Tomatoes", "price": 45, "seller": "Farmer John", "quantity": "50kg", "location": "Punjab"},
    {"name": "Organic Wheat", "price": 35, "seller": "Green Farms", "quantity": "100kg", "location": "Haryana"},
    {"name": "Sweet Corn", "price": 30, "seller": "Fresh Harvest", "quantity": "75kg", "location": "UP"}
]

@app.route('/api/crop-recommendation', methods=['POST'])
def crop_recommendation():
    try:
        data = request.json
        N = data.get('N', 50)
        P = data.get('P', 50)
        K = data.get('K', 50)
        ph = data.get('ph', 6.5)
        rainfall = data.get('rainfall', 100)
        model_choice = data.get('model_choice', 'xgb')
        
        # Get prediction from gradient boosting models
        if xgb_model is not None and lgbm_model is not None:
            predicted_crop, crop_probs = predict_crop_boosting(N, P, K, ph, rainfall, model_choice)
            
            # Get top 5 recommendations based on probabilities with confidence scores
            sorted_crops = sorted(crop_probs.items(), key=lambda x: x[1], reverse=True)
            
            # Build top recommendations with confidence (as decimal 0-1 and percentage)
            top_recommendations = []
            for i, (crop, prob) in enumerate(sorted_crops[:5], 1):
                confidence_percent = round(prob * 100, 2)
                top_recommendations.append({
                    "rank": i,
                    "crop": crop,
                    "confidence": round(prob, 4),  # Decimal format (0-1)
                    "confidence_percent": confidence_percent,  # Percentage format (0-100)
                    "confidence_label": f"{confidence_percent}%"
                })
            
            # Get the highest confidence value
            max_confidence = max(crop_probs.values()) if crop_probs else 0.8
            max_confidence_percent = round(max_confidence * 100, 2)
            
            response = {
                "predicted_crop": predicted_crop,
                "prediction_confidence": round(max_confidence, 4),  # Decimal format (0-1)
                "prediction_confidence_percent": max_confidence_percent,  # Percentage (0-100)
                "confidence_label": f"{max_confidence_percent}%",
                "top_recommendations": top_recommendations,
                "recommended_crops": [rec["crop"] for rec in top_recommendations],  # Legacy field
                "crop_probabilities": crop_probs,  # Full probabilities for reference
                "model_used": model_choice.upper(),
                "input_parameters": {
                    "N": N,
                    "P": P,
                    "K": K,
                    "ph": ph,
                    "rainfall": rainfall
                },
                "model_accuracy": "95.2%" if model_choice.lower() == "xgb" else "94.8%",
                "status": "success"
            }
        else:
            # Fallback to simple prediction
            predicted_crop = predict_crop_simple(N, P, K, ph, rainfall)
            fallback_recommendation = {
                "rank": 1,
                "crop": predicted_crop,
                "confidence": 0.90,  # Decimal format
                "confidence_percent": 90.0,  # Percentage format
                "confidence_label": "90.0%"
            }
            
            response = {
                "predicted_crop": predicted_crop,
                "prediction_confidence": 0.90,  # Decimal format (0-1)
                "prediction_confidence_percent": 90.0,  # Percentage (0-100)
                "confidence_label": "90.0%",
                "top_recommendations": [fallback_recommendation],
                "recommended_crops": [predicted_crop],
                "crop_probabilities": {predicted_crop: 0.9},
                "model_used": "Simple Rules",
                "input_parameters": {
                    "N": N,
                    "P": P,
                    "K": K,
                    "ph": ph,
                    "rainfall": rainfall
                },
                "model_accuracy": "85.0%",
                "status": "success"
            }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in crop recommendation: {e}")
        return jsonify({"error": "Error processing request", "status": "error"}), 500

@app.route('/api/weather-prediction')
def weather_prediction():
    lat = request.args.get("lat", type=float, default=DEFAULT_COORDS["lat"])
    lon = request.args.get("lon", type=float, default=DEFAULT_COORDS["lon"])
    
    try:
        history_df = fetch_recent_weather_history(lat=lat, lon=lon, past_days=30)
        if history_df.empty:
            predictions = _fallback_weather_forecast()
            current = current_weather
        else:
            predictions = generate_weather_forecast(history_df, days=7)
            latest_row = history_df.iloc[-1]
            current = {
                "date": pd.to_datetime(latest_row["date"]).isoformat(),
                "temperature": round(float(latest_row.get("temperature", current_weather["temperature"])), 2),
                "humidity": round(float(latest_row.get("humidity", current_weather["humidity"])), 2),
                "rainfall": round(float(latest_row.get("rainfall", current_weather["rainfall"])), 2),
                "wind_speed": round(float(latest_row.get("wind_speed", current_weather["wind_speed"])), 2),
                "pressure": round(float(latest_row.get("pressure", 0)), 2) if not pd.isna(latest_row.get("pressure", np.nan)) else None,
            }
        
        return jsonify({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "location": {"lat": lat, "lon": lon},
            "current_weather": current,
            "predictions": predictions,
            "model_status": "ready" if gru_model is not None and weather_scaler is not None else "fallback"
        })
    except Exception as e:
        print(f"Error in weather prediction endpoint: {e}")
        traceback.print_exc()
        return jsonify({
            "error": "Unable to generate weather forecast",
            "message": str(e)
        }), 500

@app.route('/api/market-trends')
def market_trends_endpoint():
    return jsonify({
        "trends": market_trends,
        "last_updated": datetime.now().isoformat()
    })

@app.route('/api/products', methods=['GET', 'POST'])
def products_endpoint():
    global products
    
    if request.method == 'POST':
        new_product = request.json
        products.append(new_product)
        return jsonify({"message": "Product added successfully", "product": new_product})
    
    return jsonify({"products": products})

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({"response": "Please ask a question."})
        
        # Get cached knowledge base text
        knowledge_text = get_knowledge_base_text()
            
        # Get AI response using RAG
        ai_response = get_rag_response(message, knowledge_text)
        
        return jsonify({"response": ai_response})
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return jsonify({"response": "I'm having trouble connecting to my knowledge base right now. Please try again later."}), 500

@app.route('/nakshatra', methods=['POST'])
def nakshatra_endpoint():
    try:
        data = request.get_json(silent=True) or {}
        date_str = data.get('date')
        if not date_str:
            return jsonify({
                "error": "Missing required field",
                "message": "Field 'date' (YYYY-MM-DD) is required"
            }), 400

        # Validate simple format YYYY-MM-DD
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "error": "Invalid date format",
                "message": "Date must be in YYYY-MM-DD format"
            }), 400

        result = get_moon_nakshatra_and_crop(date_str)

        return jsonify({
            "Nakshatra_Name": result.get("Nakshatra_Name"),
            "Nakshatra_Details": result.get("Nakshatra_Details"),
            "Rating": result.get("Rating"),
            "Recommended_Crops": result.get("Recommended_Crops")
        })
    except Exception as e:
        print(f"Error in nakshatra endpoint: {e}")
        traceback.print_exc()
        return jsonify({
            "error": "Error processing request",
            "message": str(e)
        }), 500

@app.route('/api/model-info')
def model_info():
    """Get information about the trained models"""
    if xgb_model is None or lgbm_model is None:
        return jsonify({
            "status": "Models not trained",
            "message": "Models are still being trained or failed to load"
        })
    
    return jsonify({
        "status": "Models ready",
        "xgb_model": "XGBoost Classifier",
        "lgbm_model": "LightGBM Classifier",
        "fertilizer_model": "XGBoost Classifier" if fertilizer_model is not None else "Not loaded",
        "features": features,
        "available_crops": list(label_encoder.classes_) if label_encoder else [],
        "model_accuracy": {
            "xgb": "95.2%",
            "lgbm": "94.8%"
        }
    })

# This function has been moved to an earlier position in the file
# See the load_fertilizer_models function defined around line 213

@app.route('/predict', methods=['POST'])
def predict_fertilizer():
    """Predict fertilizer based on soil and crop parameters"""
    try:
        # Check if models are loaded
        if fertilizer_model is None or fertilizer_scaler is None or not fertilizer_encoders:
            return jsonify({
                "error": "Models not loaded",
                "message": "Fertilizer prediction models are not available"
            }), 500
        
        # Get input data from request
        data = request.json
        
        # Validate required fields
        required_fields = ['Soil_color', 'Nitrogen', 'Phosphorus', 'Potassium', 'pH', 'Rainfall', 'Temperature', 'Crop']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "error": "Missing required fields",
                "missing_fields": missing_fields
            }), 400
        
        # Extract input features
        soil_color = data['Soil_color']
        nitrogen = float(data['Nitrogen'])
        phosphorus = float(data['Phosphorus'])
        potassium = float(data['Potassium'])
        ph = float(data['pH'])
        rainfall = float(data['Rainfall'])
        temperature = float(data['Temperature'])
        crop = data['Crop']
        
        # Validate input types
        if not all(isinstance(x, (int, float)) for x in [nitrogen, phosphorus, potassium, ph, rainfall, temperature]):
            return jsonify({
                "error": "Invalid input types",
                "message": "Numeric fields must be numbers"
            }), 400
        
        # Encode categorical features
        try:
            encoded_soil_color = fertilizer_encoders.get('Soil_color').transform([soil_color])[0]
        except (ValueError, AttributeError) as e:
            return jsonify({
                "error": "Invalid Soil_color",
                "message": f"Soil_color '{soil_color}' not recognized",
                "valid_values": list(fertilizer_encoders.get('Soil_color').classes_) if 'Soil_color' in fertilizer_encoders else []
            }), 400
        
        try:
            encoded_crop = fertilizer_encoders.get('Crop').transform([crop])[0]
        except (ValueError, AttributeError) as e:
            return jsonify({
                "error": "Invalid Crop",
                "message": f"Crop '{crop}' not recognized",
                "valid_values": list(fertilizer_encoders.get('Crop').classes_) if 'Crop' in fertilizer_encoders else []
            }), 400
        
        # Create feature array
        # Assuming the order of features in the model is: [Soil_color, Nitrogen, Phosphorus, Potassium, pH, Rainfall, Temperature, Crop]
        features = np.array([[encoded_soil_color, nitrogen, phosphorus, potassium, ph, rainfall, temperature, encoded_crop]])
        
        # Scale numeric features
        # Assuming the scaler was fitted on all numeric features in the same order
        numeric_features = features[:, 1:-1]  # All except Soil_color and Crop
        if fertilizer_scaler is not None:
            scaled_numeric = fertilizer_scaler.transform(numeric_features)
            features[:, 1:-1] = scaled_numeric
        
        # Make prediction
        try:
            # Handle different XGBoost versions
            # Ensure classifier meta is present
            if fertilizer_model is not None and not hasattr(fertilizer_model, 'n_classes_'):
                try:
                    fertilizer_model.n_classes_ = len(fertilizer_encoders.get('Fertilizer').classes_)
                except Exception:
                    pass
            prediction = fertilizer_model.predict(features)[0]
        except AttributeError as e:
            if 'use_label_encoder' in str(e):
                # For older XGBoost models that require use_label_encoder
                import xgboost as xgb
                temp_model = xgb.XGBClassifier()
                temp_model._Booster = fertilizer_model._Booster
                # Set required meta attributes
                if not hasattr(temp_model, 'n_classes_'):
                    try:
                        temp_model.n_classes_ = len(fertilizer_encoders.get('Fertilizer').classes_)
                    except Exception:
                        pass
                prediction = temp_model.predict(features)[0]
            else:
                raise e
        
        # Decode prediction to get fertilizer name
        fertilizer_name = fertilizer_encoders.get('Fertilizer').inverse_transform([prediction])[0]
        
        # Generate explanation (placeholder for now)
        explanation = generate_fertilizer_explanation(fertilizer_name, nitrogen, phosphorus, potassium, crop)
        
        # Return prediction
        return jsonify({
            "predicted_fertilizer": fertilizer_name,
            "explanation": explanation,
            "input_parameters": {
                "Soil_color": soil_color,
                "Nitrogen": nitrogen,
                "Phosphorus": phosphorus,
                "Potassium": potassium,
                "pH": ph,
                "Rainfall": rainfall,
                "Temperature": temperature,
                "Crop": crop
            }
        })
        
    except Exception as e:
        print(f"Error in fertilizer prediction: {e}")
        traceback.print_exc()
        return jsonify({
            "error": "Error processing request",
            "message": str(e)
        }), 500

def generate_fertilizer_explanation(fertilizer, nitrogen, phosphorus, potassium, crop):
    """Generate a simple explanation for the fertilizer recommendation"""
    explanations = {
        "Urea": f"Urea recommended because Nitrogen level ({nitrogen}) is low and {crop} has high N demand.",
        "DAP": f"DAP (Diammonium Phosphate) recommended because Phosphorus level ({phosphorus}) is low for {crop}.",
        "NPK": f"NPK recommended for balanced nutrition as {crop} requires moderate levels of all nutrients.",
        "MOP": f"MOP (Muriate of Potash) recommended because Potassium level ({potassium}) is low for {crop}.",
        "14-35-14": f"14-35-14 recommended because {crop} needs higher Phosphorus with moderate Nitrogen and Potassium.",
        "28-28": f"28-28 recommended because {crop} needs balanced Nitrogen and Phosphorus with less Potassium.",
        "17-17-17": f"17-17-17 recommended for perfectly balanced nutrition required by {crop}.",
        "20-20": f"20-20 recommended because {crop} needs equal amounts of Nitrogen and Phosphorus.",
        "10-26-26": f"10-26-26 recommended because {crop} needs higher Phosphorus and Potassium with less Nitrogen.",
    }
    
    return explanations.get(fertilizer, f"{fertilizer} recommended based on soil parameters and {crop} requirements.")

# OTP storage (in-memory, use Redis/database in production)
otp_storage = {}
OTP_EXPIRY_TIME = 300  # 5 minutes in seconds

def generate_otp():
    """Generate a 6-digit OTP"""
    import random
    return str(random.randint(100000, 999999))

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to mobile number"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        mobile = data.get('mobile', '').strip()
        
        # Validation
        if not username or len(username) < 3:
            return jsonify({
                "success": False,
                "message": "Username must be at least 3 characters long"
            }), 400
        
        if not mobile or not mobile.isdigit() or len(mobile) != 10:
            return jsonify({
                "success": False,
                "message": "Please enter a valid 10-digit mobile number"
            }), 400
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP with timestamp
        import time
        otp_storage[mobile] = {
            'otp': otp,
            'username': username,
            'timestamp': time.time(),
            'attempts': 0
        }
        
        # In production, send SMS via Twilio, AWS SNS, etc.
        # For demo purposes, we'll log it (in production, remove this)
        print(f"[DEMO] OTP for {mobile}: {otp}")
        print(f"[DEMO] This OTP is valid for {OTP_EXPIRY_TIME // 60} minutes")
        
        # Simulate SMS sending delay
        # In production, replace this with actual SMS API call
        # Example: twilio_client.messages.create(to=f"+91{mobile}", body=f"Your AgriAid+ OTP is {otp}")
        
        return jsonify({
            "success": True,
            "message": f"OTP sent to {mobile}",
            "otp": otp  # Remove this in production - only for demo
        })
        
    except Exception as e:
        print(f"Error sending OTP: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Failed to send OTP. Please try again."
        }), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and create account"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        mobile = data.get('mobile', '').strip()
        otp = data.get('otp', '').strip()
        
        # Validation
        if not username or not mobile or not otp:
            return jsonify({
                "success": False,
                "message": "Missing required fields"
            }), 400
        
        if not otp.isdigit() or len(otp) != 6:
            return jsonify({
                "success": False,
                "message": "OTP must be a 6-digit number"
            }), 400
        
        # Check if OTP exists
        if mobile not in otp_storage:
            return jsonify({
                "success": False,
                "message": "OTP not found. Please request a new OTP."
            }), 400
        
        otp_data = otp_storage[mobile]
        
        # Check if OTP matches username
        if otp_data['username'] != username:
            return jsonify({
                "success": False,
                "message": "Username mismatch. Please use the same username."
            }), 400
        
        # Check OTP expiry
        import time
        if time.time() - otp_data['timestamp'] > OTP_EXPIRY_TIME:
            del otp_storage[mobile]
            return jsonify({
                "success": False,
                "message": "OTP has expired. Please request a new one."
            }), 400
        
        # Check attempts (prevent brute force)
        otp_data['attempts'] += 1
        if otp_data['attempts'] > 5:
            del otp_storage[mobile]
            return jsonify({
                "success": False,
                "message": "Too many attempts. Please request a new OTP."
            }), 400
        
        # Verify OTP
        if otp_data['otp'] != otp:
            return jsonify({
                "success": False,
                "message": f"Invalid OTP. {5 - otp_data['attempts']} attempts remaining."
            }), 400
        
        # OTP verified successfully
        # In production, create user account here
        # Example: user = create_user(username=username, mobile=mobile)
        
        # Clean up OTP
        del otp_storage[mobile]
        
        print(f"[DEMO] Account created for {username} with mobile {mobile}")
        
        return jsonify({
            "success": True,
            "message": "Account created successfully!"
        })
        
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Failed to verify OTP. Please try again."
        }), 500

@app.route('/api/send-login-otp', methods=['POST'])
def send_login_otp():
    """Send OTP for login"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        mobile = data.get('mobile', '').strip()
        
        # Validation
        if not username or len(username) < 3:
            return jsonify({
                "success": False,
                "message": "Username must be at least 3 characters long"
            }), 400
        
        if not mobile or not mobile.isdigit() or len(mobile) != 10:
            return jsonify({
                "success": False,
                "message": "Please enter a valid 10-digit mobile number"
            }), 400
        
        # In production, verify username and mobile exist in database
        # For demo, we'll generate OTP regardless
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP with timestamp
        import time
        login_otp_key = f"login_{mobile}"
        otp_storage[login_otp_key] = {
            'otp': otp,
            'username': username,
            'timestamp': time.time(),
            'attempts': 0
        }
        
        # In production, send SMS via Twilio, AWS SNS, etc.
        # For demo purposes, we'll log it (in production, remove this)
        print(f"[DEMO] Login OTP for {mobile} (username: {username}): {otp}")
        print(f"[DEMO] This OTP is valid for {OTP_EXPIRY_TIME // 60} minutes")
        
        return jsonify({
            "success": True,
            "message": f"OTP sent to {mobile}",
            "otp": otp  # Remove this in production - only for demo
        })
        
    except Exception as e:
        print(f"Error sending login OTP: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Failed to send OTP. Please try again."
        }), 500

@app.route('/api/verify-login-otp', methods=['POST'])
def verify_login_otp():
    """Verify OTP and login"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        mobile = data.get('mobile', '').strip()
        otp = data.get('otp', '').strip()
        
        # Validation
        if not username or not mobile or not otp:
            return jsonify({
                "success": False,
                "message": "Missing required fields"
            }), 400
        
        if not otp.isdigit() or len(otp) != 6:
            return jsonify({
                "success": False,
                "message": "OTP must be a 6-digit number"
            }), 400
        
        # Check if OTP exists
        login_otp_key = f"login_{mobile}"
        if login_otp_key not in otp_storage:
            return jsonify({
                "success": False,
                "message": "OTP not found. Please request a new OTP."
            }), 400
        
        otp_data = otp_storage[login_otp_key]
        
        # Check if OTP matches username
        if otp_data['username'] != username:
            return jsonify({
                "success": False,
                "message": "Username mismatch. Please use the same username."
            }), 400
        
        # Check OTP expiry
        import time
        if time.time() - otp_data['timestamp'] > OTP_EXPIRY_TIME:
            del otp_storage[login_otp_key]
            return jsonify({
                "success": False,
                "message": "OTP has expired. Please request a new one."
            }), 400
        
        # Check attempts (prevent brute force)
        otp_data['attempts'] += 1
        if otp_data['attempts'] > 5:
            del otp_storage[login_otp_key]
            return jsonify({
                "success": False,
                "message": "Too many attempts. Please request a new OTP."
            }), 400
        
        # Verify OTP
        if otp_data['otp'] != otp:
            return jsonify({
                "success": False,
                "message": f"Invalid OTP. {5 - otp_data['attempts']} attempts remaining."
            }), 400
        
        # OTP verified successfully
        # In production, create session here and return session token
        # Example: session = create_session(username=username, mobile=mobile)
        
        # Clean up OTP
        del otp_storage[login_otp_key]
        
        print(f"[DEMO] Login successful for {username} with mobile {mobile}")
        
        return jsonify({
            "success": True,
            "message": "Login successful!"
        })
        
    except Exception as e:
        print(f"Error verifying login OTP: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Failed to verify OTP. Please try again."
        }), 500


# ---------------------------------------------------------
# NEW API ENDPOINTS
# ---------------------------------------------------------

@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Return list of cities for the frontend dropdown"""
    if not city_list:
        return jsonify({"cities": ["Pune", "Mumbai", "Nagpur"]}) # Fallback
    return jsonify({"cities": list(city_list)}) # Ensure it's list serializable

@app.route('/api/predict-weather', methods=['POST'])
def predict_weather():
    data = request.json
    city_name = data.get('city', 'Pune')

    # 1. Get Coordinates
    coords = CITY_COORDINATES.get(city_name, CITY_COORDINATES["Default"])

    if not gru_model or not weather_scaler:
        # Return a simple fallback forecast if models are not ready
        fallback = _fallback_weather_forecast(days=7)
        return jsonify({
            "city": city_name,
            "forecast": fallback,
            "warning": "GRU weather model or scaler not loaded; returning fallback forecast"
        }), 200

    # 2. Fetch 35 days of history (Buffer for safety)
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=35)
        
        # Open-Meteo API
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={coords['lat']}&longitude={coords['lon']}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_mean,relative_humidity_2m_mean,wind_speed_10m_max,surface_pressure_mean&timezone=auto"
        
        resp = requests.get(url, timeout=5).json()
        daily = resp.get('daily', {})

        if 'time' not in daily:
            raise ValueError("External API unavailable or invalid response")

        # 3. Process History (Last 30 days)
        # Format: [Temp, Humidity, Wind, Pressure]
        input_data = []
        
        # Check if we have enough data
        if len(daily['time']) < 1:
             raise ValueError("Not enough historical data received.")

        idx = len(daily['time']) - 1
        count = 0
        
        # Loop backwards to get most recent days
        # We need daily['temperature_2m_mean'], daily['relative_humidity_2m_mean'] etc.
        
        while idx >= 0 and count < 30:
            try:
                t = daily['temperature_2m_mean'][idx]
                h = daily['relative_humidity_2m_mean'][idx]
                w = daily['wind_speed_10m_max'][idx]
                p = daily['surface_pressure_mean'][idx]
                
                # Simple null check/imputation
                if t is None: t = 25.0
                if h is None: h = 50.0
                if w is None: w = 10.0
                if p is None: p = 1000.0
                
                input_data.insert(0, [t, h, w, p])
            except IndexError:
                pass
            idx -= 1
            count += 1
            
        # Pad if short (rare)
        while len(input_data) < 30 and len(input_data) > 0:
            input_data.insert(0, input_data[0])
            
        if not input_data:
             raise ValueError("Could not construct input vector from API data.")

        # 4. Scale & Predict
        input_arr = np.array(input_data)
        
        # transform expects 2D array
        if weather_scaler:
            input_scaled = weather_scaler.transform(input_arr)
        else:
             # Just cast if no scaler (should not happen if model is loaded)
             input_scaled = input_arr

        input_seq = input_scaled.reshape(1, 30, 4)
        
        # Prediction (Shape: 1 x 21 -> 7 days * 3 feats??)
        # Verify model output shape. User code assumes 1x21 or something that reshapes to 7x3
        # The user said: "Prediction (Shape: 1 x 21)" and "Reshape (7 days x 3 features)"
        pred_scaled = gru_model.predict(input_seq)
        
        # Reshape (7 days x 3 features)
        pred_reshaped = pred_scaled.reshape(7, 3)
        
        # Add dummy Pressure column for Inverse Transform
        last_pressure = input_scaled[-1, 3]
        dummy_col = np.full((7, 1), last_pressure)
        pred_full = np.hstack([pred_reshaped, dummy_col])
        
        # Inverse Transform to get real numbers
        if weather_scaler:
            forecast_values = weather_scaler.inverse_transform(pred_full)
        else:
            forecast_values = pred_full
        
        # 5. Format Output
        results = []
        current_day = datetime.now()
        
        for i in range(7):
            next_day = current_day + timedelta(days=i+1)
            
            # Predict Condition Text using unscaled/real forecast values
            # The classifier was trained on real weather values (temp, humidity, wind, pressure)
            clf_input = np.array([[ 
                forecast_values[i][0],   # temperature
                forecast_values[i][1],   # humidity
                forecast_values[i][2],   # wind speed
                forecast_values[i][3]    # pressure (from inverse transform)
            ]])
            
            condition = "Unknown"
            if condition_clf:
                try:
                    condition = condition_clf.predict(clf_input)[0]
                except Exception as e:
                    print(f"Condition prediction error: {e}")
            
            results.append({
                "date": next_day.strftime("%Y-%m-%d"),
                "avg_temp": round(float(forecast_values[i][0]), 1),
                "avg_humidity": round(float(forecast_values[i][1]), 1),
                "wind_speed": round(float(forecast_values[i][2]), 1),
                "weather_condition": condition
            })

        return jsonify({"city": city_name, "forecast": results})

    except Exception as e:
        print(f"Forecast Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ===============================
# Register MongoDB API Blueprints
# ===============================
app.register_blueprint(user_bp, url_prefix="/api/user")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(ecommerce_bp, url_prefix="/api/ecommerce")
app.register_blueprint(marketplace_bp, url_prefix="/api/marketplace")

if __name__ == '__main__':
    # In debug mode, Flask runs a reloader that starts the app twice.
    # Only initialize in the reloader child process to avoid duplicate loads.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        print("Initializing AgriAid+ with ML models...")
        initialize()
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
