# ML Model Training Guide

## Quick Start

### Option 1: Using Django Management Command (Recommended)
```bash
cd carbon_backend
python manage.py train_carbon_model
```

### Option 2: Using Python Script Directly
```bash
cd carbon_backend
python ml_training/train_model.py
```

### Option 3: Using Jupyter Notebook
1. Open `ml_training/carbon_credits_ml_model.ipynb` in Jupyter
2. Run all cells
3. Model will be saved to `ml_models/` directory

## Requirements

Make sure you have the required packages:
```bash
pip install pandas numpy scikit-learn joblib
```

## Dataset

The training script expects the dataset at:
- `carbon_backend/enhanced_carbon_credits_250_records.csv`

## Output

After training, the following files will be created in `ml_models/`:
- `carbon_credits_model.pkl` - Trained model
- `scaler.pkl` - Feature scaler
- `label_encoders.pkl` - Categorical encoders
- `feature_columns.pkl` - Feature column names

## Model Performance

The script will:
1. Load and preprocess the dataset
2. Train multiple models (Random Forest, Gradient Boosting)
3. Select the best model based on R² score
4. Save the best model and preprocessing objects

Expected performance:
- **R² Score**: 0.85-0.95
- **RMSE**: < 0.5 kg CO₂
- **MAE**: < 0.3 kg CO₂

## Usage in Code

After training, the model will be automatically used by the ML predictor:

```python
from core.ml_predictor import predict_carbon_credits_ml

result = predict_carbon_credits_ml(
    transport_mode='electric_car',
    distance_km=12.2,
    time_period='peak_evening',
    traffic_condition='heavy',
    weather_condition='normal',
    route_type='city_center',
    aqi_level='moderate',
    season='summer'
)

print(f"Predicted: {result['prediction']} kg CO₂")
print(f"Method: {result['method']}")
print(f"Confidence: {result['confidence']}")
```

If the model is not available, it will automatically fall back to formula-based calculation.


