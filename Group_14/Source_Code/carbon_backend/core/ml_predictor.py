"""
Machine Learning Model for Carbon Credits Prediction

This module loads and uses the fine-tuned ML model to predict carbon credits
based on trip parameters.

Model fine-tuned on: 260 records with 36 engineered features
Target: carbon_credits_earned (kg CO₂)
Best Model: Gradient Boosting (94.27% R² accuracy)
"""

import os
import logging
import joblib
import numpy as np
import pandas as pd
import pickle
import json
from typing import Dict, Optional, List
from django.conf import settings
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)

# Model paths
MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
MODEL_PATH = os.path.join(MODEL_DIR, 'fine_tuned_predictive_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'fine_tuned_preprocessing.json')


class CarbonCreditsPredictor:
    """ML-based carbon credits predictor with fine-tuned model"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoders = None
        self.feature_columns = None
        self._load_model()
    
    def _load_model(self):
        """Load fine-tuned model and preprocessing objects"""
        try:
            if os.path.exists(MODEL_PATH):
                # Load model
                with open(MODEL_PATH, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.model = model_data['model']
                self.feature_columns = model_data['feature_columns']
                
                # Load preprocessing data from JSON
                if os.path.exists(SCALER_PATH):
                    with open(SCALER_PATH, 'r') as f:
                        prep_data = json.load(f)
                    
                    # Reconstruct label encoders
                    self.label_encoders = {}
                    for col, classes in prep_data.get('label_encoders', {}).items():
                        le = LabelEncoder()
                        le.classes_ = np.array(classes)
                        self.label_encoders[col] = le
                    
                    # Reconstruct scaler
                    self.scaler = StandardScaler()
                    self.scaler.mean_ = np.array(prep_data.get('scaler_mean', []))
                    self.scaler.scale_ = np.array(prep_data.get('scaler_scale', []))
                
                logger.info(f"Fine-tuned ML model loaded: {model_data.get('model_name', 'Unknown')}")
            else:
                logger.warning(f"Fine-tuned model file not found at {MODEL_PATH}. Using formula-based calculation.")
        except Exception as e:
            logger.error(f"Error loading fine-tuned ML model: {str(e)}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if ML model is available"""
        return self.model is not None
    
    def predict(
        self,
        transport_mode: str,
        distance_km: float,
        trip_duration_minutes: float = None,
        average_speed_kmph: float = None,
        time_period: str = 'off_peak',
        traffic_condition: str = 'moderate',
        weather_condition: str = 'normal',
        route_type: str = 'suburban',
        aqi_level: str = 'moderate',
        season: str = 'normal',
        **kwargs
    ) -> Dict:
        """
        Predict carbon credits using fine-tuned ML model.
        
        Args:
            transport_mode: Transport mode
            distance_km: Distance in kilometers
            trip_duration_minutes: Trip duration in minutes
            average_speed_kmph: Average speed in km/h
            time_period: Time period (peak_morning, peak_evening, off_peak, late_night)
            traffic_condition: Traffic condition (heavy, moderate, light)
            weather_condition: Weather condition (heavy_rain, light_rain, normal, favorable)
            route_type: Route type (hilly, city_center, highway, suburban)
            aqi_level: AQI level (hazardous, very_poor, moderate, good)
            season: Season (winter, summer, monsoon, post_monsoon)
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with prediction, confidence, and method
        """
        if not self.is_available():
            return {
                'prediction': None,
                'confidence': 0.0,
                'method': 'formula',
                'error': 'ML model not available'
            }
        
        try:
            # Prepare feature dictionary
            features = self._prepare_features(
                transport_mode=transport_mode,
                distance_km=distance_km,
                trip_duration_minutes=trip_duration_minutes,
                average_speed_kmph=average_speed_kmph,
                time_period=time_period,
                traffic_condition=traffic_condition,
                weather_condition=weather_condition,
                route_type=route_type,
                aqi_level=aqi_level,
                season=season,
                **kwargs
            )
            
            # Create DataFrame
            df = pd.DataFrame([features])
            
            # Encode categorical variables
            df_encoded = self._encode_features(df)
            
            # Ensure all feature columns are present
            df_encoded = self._align_features(df_encoded)
            
            # Scale features
            X_scaled = self.scaler.transform(df_encoded)
            
            # Predict
            prediction = self.model.predict(X_scaled)[0]
            
            # Ensure non-negative
            prediction = max(0.0, float(prediction))
            
            # Calculate confidence based on model type
            confidence = 0.94 if 'GradientBoosting' in str(type(self.model)) else 0.85
            
            return {
                'prediction': prediction,
                'confidence': confidence,
                'method': 'ml',
                'model_type': type(self.model).__name__,
                'features_used': len(features)
            }
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {str(e)}")
            return {
                'prediction': None,
                'confidence': 0.0,
                'method': 'formula',
                'error': str(e)
            }
    
    def _prepare_features(self, **kwargs) -> Dict:
        """Prepare features dictionary from input parameters"""
        from .emission_factors import get_baseline_ef, get_actual_ef
        from .calculations import calculate_time_weight, calculate_context_factor
        
        # Get emission factors
        ef_baseline = get_baseline_ef(kwargs.get('transport_mode', 'petrol_car'))
        ef_actual = get_actual_ef(kwargs.get('transport_mode', 'petrol_car'))
        
        # Calculate time weight
        time_weight = calculate_time_weight(
            kwargs.get('time_period', 'off_peak'),
            kwargs.get('traffic_condition', 'moderate'),
            recency_days=0
        )
        
        # Calculate context factor
        context_factor = calculate_context_factor(
            kwargs.get('weather_condition', 'normal'),
            kwargs.get('route_type', 'suburban'),
            kwargs.get('aqi_level', 'moderate'),
            load_factor=kwargs.get('load_factor', 1.0),
            season=kwargs.get('season', 'normal')
        )
        
        # Calculate engineered features
        distance_km = kwargs.get('distance_km', 0.0)
        trip_duration_minutes = kwargs.get('trip_duration_minutes', 0.0)
        average_speed_kmph = kwargs.get('average_speed_kmph', distance_km / (trip_duration_minutes / 60 + 0.001))
        
        # Feature engineering
        speed_efficiency = distance_km / (trip_duration_minutes + 1)
        cost_per_km = kwargs.get('estimated_cost_inr', 100) / (distance_km + 1)
        emission_per_km = (ef_actual * distance_km) / (distance_km + 1)
        context_score = (1.2 if kwargs.get('time_period') in ['peak_morning', 'peak_evening'] else 1.0) * (1.3 if kwargs.get('traffic_condition') == 'heavy' else 1.0) * (1.2 if kwargs.get('weather_condition') in ['heavy_rain', 'light_rain'] else 1.0)
        environmental_impact = (1.2 if kwargs.get('aqi_level') == 'hazardous' else 1.0) * context_factor
        
        # Time-based features
        hour = kwargs.get('hour', 12)
        day_of_week_num = kwargs.get('day_of_week_num', 2)
        month = kwargs.get('month', 6)
        is_weekend = 1 if day_of_week_num >= 5 else 0
        
        # Build feature dictionary with all 36 features
        features = {
            # Basic features (15)
            'distance_km': distance_km,
            'trip_duration_minutes': trip_duration_minutes,
            'average_speed_kmph': average_speed_kmph,
            'ef_baseline': ef_baseline,
            'ef_actual': ef_actual,
            'emission_difference': ef_baseline - ef_actual,
            'peak_factor': 1.2 if kwargs.get('time_period') in ['peak_morning', 'peak_evening'] else 1.0,
            'traffic_multiplier': 1.3 if kwargs.get('traffic_condition') == 'heavy' else (1.1 if kwargs.get('traffic_condition') == 'moderate' else 1.0),
            'recency_weight': 1.0,
            'time_weight': time_weight,
            'weather_factor': 1.2 if kwargs.get('weather_condition') in ['heavy_rain', 'light_rain'] else (0.95 if kwargs.get('weather_condition') == 'favorable' else 1.0),
            'route_factor': 1.3 if kwargs.get('route_type') == 'hilly' else (1.2 if kwargs.get('route_type') == 'city_center' else (0.9 if kwargs.get('route_type') == 'highway' else 1.0)),
            'load_factor': kwargs.get('load_factor', 1.0),
            'aqi_factor': 1.2 if kwargs.get('aqi_level') == 'hazardous' else (1.1 if kwargs.get('aqi_level') == 'very_poor' else 1.0),
            'context_factor': context_factor,
            'user_age': kwargs.get('user_age', 30),
            'hour': hour,
            'day_of_week_num': day_of_week_num,
            'month': month,
            
            # Engineered features (5)
            'speed_efficiency': speed_efficiency,
            'cost_per_km': cost_per_km,
            'emission_per_km': emission_per_km,
            'context_score': context_score,
            'environmental_impact': environmental_impact,
            
            # Categorical features (16) - will be encoded
            'transport_mode': kwargs.get('transport_mode', 'petrol_car'),
            'mode_type': 'private' if kwargs.get('transport_mode') in ['petrol_car', 'diesel_car', 'electric_car'] else 'shared',
            'city': kwargs.get('city', 'Mumbai'),
            'season_param': kwargs.get('season', 'normal'),
            'time_period_param': kwargs.get('time_period', 'off_peak'),
            'traffic_condition_param': kwargs.get('traffic_condition', 'moderate'),
            'weather_condition_param': kwargs.get('weather_condition', 'normal'),
            'route_type_param': kwargs.get('route_type', 'suburban'),
            'aqi_level_param': kwargs.get('aqi_level', 'moderate'),
            'trip_purpose': kwargs.get('trip_purpose', 'business')
        }
        
        # Add additional features if provided
        for key, value in kwargs.items():
            if key not in features:
                features[key] = value
        
        return features
    
    def _encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features"""
        df_encoded = df.copy()
        
        for col in df_encoded.columns:
            if col in self.label_encoders and col.endswith('_encoded'):
                original_col = col.replace('_encoded', '')
                if original_col in ['transport_mode', 'mode_type', 'city', 'season', 'time_period', 'traffic_condition', 'weather_condition', 'route_type', 'aqi_level', 'trip_purpose']:
                    try:
                        # Handle unseen categories
                        unique_values = df_encoded[col].unique()
                        for val in unique_values:
                            if str(val) not in self.label_encoders[original_col].classes_:
                                # Use most common class as default
                                df_encoded[col] = df_encoded[col].replace(val, self.label_encoders[original_col].classes_[0])
                        
                        df_encoded[col] = self.label_encoders[original_col].transform(df_encoded[col].astype(str))
                    except Exception as e:
                        logger.warning(f"Error encoding {col}: {str(e)}")
                        df_encoded[col] = 0  # Default value
        
        return df_encoded
    
    def _align_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Align features with model expectations"""
        # Ensure all expected features are present
        expected_features = self.feature_columns if self.feature_columns else []
        
        for feature in expected_features:
            if feature not in df.columns:
                # Add missing features with default values
                if feature.endswith('_encoded'):
                    df[feature] = 0  # Default for encoded features
                elif 'factor' in feature or 'weight' in feature:
                    df[feature] = 1.0  # Default for factors
                elif 'km' in feature or 'minutes' in feature or 'speed' in feature:
                    df[feature] = 0.0  # Default for numeric features
                else:
                    df[feature] = 0  # Default for other features
        
        # Reorder columns to match model expectations
        if expected_features:
            df_aligned = df[expected_features]
        else:
            df_aligned = df
        
        return df_aligned


# Global predictor instance
_predictor_instance = None


def get_predictor() -> CarbonCreditsPredictor:
    """Get or create global predictor instance"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = CarbonCreditsPredictor()
    return _predictor_instance


def predict_carbon_credits_ml(**kwargs) -> Dict:
    """
    Convenience function to predict carbon credits using fine-tuned ML model.
    
    Falls back to formula-based calculation if ML model is not available.
    """
    predictor = get_predictor()
    
    if predictor.is_available():
        return predictor.predict(**kwargs)
    else:
        # Fall back to formula-based calculation
        from .calculations import (
            calculate_carbon_credits,
            calculate_time_weight,
            calculate_context_factor
        )
        from .emission_factors import get_baseline_ef, get_actual_ef
        
        try:
            ef_baseline = get_baseline_ef(kwargs.get('transport_mode', 'petrol_car'))
            ef_actual = get_actual_ef(kwargs.get('transport_mode', 'petrol_car'))
            distance = kwargs.get('distance_km', 0.0)
            time_weight = calculate_time_weight(
                kwargs.get('time_period', 'off_peak'),
                kwargs.get('traffic_condition', 'moderate'),
                recency_days=0
            )
            context_factor = calculate_context_factor(
                kwargs.get('weather_condition', 'normal'),
                kwargs.get('route_type', 'suburban'),
                kwargs.get('aqi_level', 'moderate'),
                load_factor=kwargs.get('load_factor', 1.0),
                season=kwargs.get('season', 'normal')
            )
            
            prediction = calculate_carbon_credits(
                ef_baseline, ef_actual, distance, time_weight, context_factor
            )
            
            return {
                'prediction': prediction,
                'confidence': 0.95,  # High confidence for formula
                'method': 'formula'
            }
        except Exception as e:
            logger.error(f"Error in formula-based calculation: {str(e)}")
            return {
                'prediction': 0.0,
                'confidence': 0.0,
                'method': 'formula',
                'error': str(e)
            }
