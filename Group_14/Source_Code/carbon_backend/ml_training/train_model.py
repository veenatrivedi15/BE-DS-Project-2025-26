"""
Carbon Credits ML Model Training Script

Run this script to train the ML model:
python manage.py shell < ml_training/train_model.py
Or: python ml_training/train_model.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

def train_model():
    """Train carbon credits prediction model"""
    
    # Load dataset
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'enhanced_carbon_credits_250_records.csv')
    
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at: {dataset_path}")
        print("Please ensure the dataset file exists.")
        return
    
    print("Loading dataset...")
    df = pd.read_csv(dataset_path)
    print(f"Dataset shape: {df.shape}")
    
    # Prepare features
    exclude_cols = ['trip_id', 'carbon_credits_earned', 'timestamp']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    X = df[feature_cols].copy()
    y = df['carbon_credits_earned'].copy()
    
    print(f"Features: {len(feature_cols)}")
    
    # Encode categorical variables
    categorical_cols = X.select_dtypes(include=['object']).columns
    label_encoders = {}
    X_encoded = X.copy()
    
    for col in categorical_cols:
        le = LabelEncoder()
        X_encoded[col] = le.fit_transform(X[col].astype(str))
        label_encoders[col] = le
    
    X_encoded = X_encoded.select_dtypes(include=[np.number])
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_encoded, y, test_size=0.2, random_state=42
    )
    
    print(f"Training set: {X_train.shape}")
    print(f"Test set: {X_test.shape}")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train models
    models = {
        'Random Forest': RandomForestRegressor(n_estimators=200, max_depth=20, random_state=42, n_jobs=-1),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42)
    }
    
    best_model = None
    best_name = None
    best_score = -np.inf
    
    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train_scaled, y_train)
        
        y_test_pred = model.predict(X_test_scaled)
        test_r2 = r2_score(y_test, y_test_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        test_mae = mean_absolute_error(y_test, y_test_pred)
        
        print(f"  Test R²: {test_r2:.4f}")
        print(f"  Test RMSE: {test_rmse:.4f}")
        print(f"  Test MAE: {test_mae:.4f}")
        
        if test_r2 > best_score:
            best_score = test_r2
            best_model = model
            best_name = name
    
    print(f"\nBest Model: {best_name} (R² = {best_score:.4f})")
    
    # Save model and preprocessing objects
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_models')
    os.makedirs(model_dir, exist_ok=True)
    
    joblib.dump(best_model, os.path.join(model_dir, 'carbon_credits_model.pkl'))
    joblib.dump(scaler, os.path.join(model_dir, 'scaler.pkl'))
    joblib.dump(label_encoders, os.path.join(model_dir, 'label_encoders.pkl'))
    joblib.dump(feature_cols, os.path.join(model_dir, 'feature_columns.pkl'))
    
    print(f"\nModel saved to: {model_dir}/carbon_credits_model.pkl")
    print("Training completed successfully!")

if __name__ == '__main__':
    train_model()


