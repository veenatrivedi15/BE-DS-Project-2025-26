import os
import tensorflow as tf

# Path to your model
MODEL_PATH = os.path.join("static", "models", "eye_disease_finalV2.keras")

print("🔍 Checking model file...")
if not os.path.exists(MODEL_PATH):
    print(f"❌ Model file not found at: {MODEL_PATH}")
    exit(1)

print("✅ Model file found!")

print("🔄 Trying to load model...")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print("✅ Model loaded successfully!")
    print("Model summary:")
    model.summary()
except Exception as e:
    print("❌ Failed to load model.")
    print("Error details:")
    print(e)
