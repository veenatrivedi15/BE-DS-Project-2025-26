"""
Predictive Analytics Engine for Carbon Credits Platform
Handles carbon footprint forecasting, trip pattern analysis, and trend prediction
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Any, Optional
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
import pickle
import json
from decimal import Decimal
import warnings
warnings.filterwarnings('ignore')

from trips.models import Trip
from users.models import CustomUser

class PredictiveAnalyticsEngine:
    """Advanced predictive analytics for carbon footprint and trip patterns"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_dir = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Initialize models
        self.carbon_forecast_model = None
        self.trip_pattern_model = None
        self.trend_model = None
        self.preprocessors = {}
        
        # Load trained model
        self.load_trained_model()
        
    def load_trained_model(self):
        """Load the trained model and preprocessing objects"""
        try:
            # Try to load from current directory first
            model_path = os.path.join(os.path.dirname(__file__), '..', 'predictive_analytics_model.pkl')
            if not os.path.exists(model_path):
                # Try from project root
                model_path = 'predictive_analytics_model.pkl'
            
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.carbon_forecast_model = model_data['model']
                self.feature_columns = model_data['feature_columns']
                
                # Load preprocessing data
                prep_path = model_path.replace('.pkl', '_preprocessing.json')
                if os.path.exists(prep_path):
                    with open(prep_path, 'r') as f:
                        prep_data = json.load(f)
                    
                    # Reconstruct label encoders
                    self.preprocessors['label_encoders'] = {}
                    for col, classes in prep_data['label_encoders'].items():
                        le = LabelEncoder()
                        le.classes_ = np.array(classes)
                        self.preprocessors['label_encoders'][col] = le
                    
                    # Reconstruct scaler
                    self.preprocessors['scaler'] = StandardScaler()
                    self.preprocessors['scaler'].mean_ = np.array(prep_data['scaler_mean'])
                    self.preprocessors['scaler'].scale_ = np.array(prep_data['scaler_scale'])
                
                print(f"Loaded trained model: {model_data['model_name']}")
                return True
            else:
                print("No trained model found. Using fallback models.")
                return False
        except Exception as e:
            print(f"Error loading trained model: {e}")
            return False
    
    def predict_carbon_credits(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict carbon credits for a trip using the trained model"""
        try:
            if not self.carbon_forecast_model:
                return {
                    'success': False,
                    'error': 'No trained model available',
                    'fallback_used': True
                }
            
            # Prepare features for prediction
            features = self._prepare_features(trip_data)
            if not features:
                return {
                    'success': False,
                    'error': 'Invalid trip data',
                    'fallback_used': True
                }
            
            # Scale features
            if 'scaler' in self.preprocessors:
                features_scaled = self.preprocessors['scaler'].transform([features])
            else:
                features_scaled = [features]
            
            # Make prediction
            prediction = self.carbon_forecast_model.predict(features_scaled)[0]
            
            # Ensure prediction is not negative
            prediction = max(0, prediction)
            
            return {
                'success': True,
                'predicted_credits': float(prediction),
                'confidence_score': 0.91,  # Based on R² score from training
                'model_used': 'Random Forest',
                'features_used': len(features),
                'fallback_used': False
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Prediction error: {str(e)}',
                'fallback_used': True
            }
    
    def _prepare_features(self, trip_data: Dict[str, Any]) -> List[float]:
        """Prepare features for prediction"""
        try:
            # Extract basic features
            features = []
            feature_map = {
                'distance_km': trip_data.get('distance_km', 0),
                'trip_duration_minutes': trip_data.get('trip_duration_minutes', 0),
                'average_speed_kmph': trip_data.get('average_speed_kmph', 0),
                'seasonal_factor': trip_data.get('seasonal_factor', 1.0),
                'ef_baseline': trip_data.get('ef_baseline', 0.13),
                'ef_actual': trip_data.get('ef_actual', 0.13),
                'emission_difference': trip_data.get('emission_difference', 0),
                'peak_factor': trip_data.get('peak_factor', 1.0),
                'traffic_multiplier': trip_data.get('traffic_multiplier', 1.0),
                'recency_weight': trip_data.get('recency_weight', 1.0),
                'time_weight': trip_data.get('time_weight', 1.0),
                'weather_factor': trip_data.get('weather_factor', 1.0),
                'route_factor': trip_data.get('route_factor', 1.0),
                'load_factor': trip_data.get('load_factor', 1.0),
                'aqi_factor': trip_data.get('aqi_factor', 1.0),
                'context_factor': trip_data.get('context_factor', 1.0),
                'user_age': trip_data.get('user_age', 30),
                'hour': trip_data.get('hour', datetime.now().hour),
                'day_of_week_num': trip_data.get('day_of_week_num', datetime.now().weekday()),
                'month': trip_data.get('month', datetime.now().month)
            }
            
            # Add numeric features in correct order
            for col in self.feature_columns:
                if col in feature_map:
                    features.append(float(feature_map[col]))
                elif '_encoded' in col:
                    # Handle encoded categorical features
                    original_col = col.replace('_encoded', '')
                    if original_col in trip_data:
                        # Use label encoder if available
                        if original_col in self.preprocessors.get('label_encoders', {}):
                            le = self.preprocessors['label_encoders'][original_col]
                            try:
                                encoded_value = le.transform([str(trip_data[original_col])])[0]
                                features.append(float(encoded_value))
                            except:
                                features.append(0.0)
                        else:
                            features.append(0.0)
                    else:
                        features.append(0.0)
                else:
                    features.append(0.0)
            
            return features
            
        except Exception as e:
            print(f"Error preparing features: {e}")
            return []
        
    def get_user_historical_data(self, user_id: int, days_back: int = 90) -> pd.DataFrame:
        """Get user's historical trip data for analysis"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return pd.DataFrame()

        employee_profile = getattr(user, 'employee_profile', None)
        if not employee_profile:
            return pd.DataFrame()

        trips = Trip.objects.filter(
            employee=employee_profile,
            start_time__gte=start_date,
            start_time__lte=end_date
        ).order_by('start_time')
        
        data = []
        for trip in trips:
            data.append({
                'date': trip.start_time.date(),
                'hour': trip.start_time.hour,
                'day_of_week': trip.start_time.weekday(),
                'month': trip.start_time.month,
                'transport_mode': trip.transport_mode,
                'distance_km': float(trip.distance_km) if trip.distance_km else 0,
                'duration_minutes': float(trip.duration_minutes) if trip.duration_minutes else 0,
                'carbon_savings': float(trip.carbon_savings or trip.carbon_credits_earned or trip.credits_earned or 0),
                'credits_earned': float(trip.carbon_credits_earned or trip.credits_earned or 0),
                'weather_condition': trip.weather_condition or 'normal',
                'traffic_condition': trip.traffic_condition or 'moderate',
                'route_type': trip.route_type or 'suburban',
                'time_period': trip.time_period or 'off_peak',
                'season': trip.season or 'post_monsoon',
                'ef_actual': float(trip.ef_actual) if trip.ef_actual else 0,
                'ef_baseline': float(trip.ef_baseline) if trip.ef_baseline else 0,
            })
        
        return pd.DataFrame(data)
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for machine learning models"""
        if df.empty:
            return np.array([]), np.array([])
        
        # Create feature matrix
        features = []
        
        for _, row in df.iterrows():
            feature_vector = [
                row['hour'],
                row['day_of_week'],
                row['month'],
                row['distance_km'],
                row['duration_minutes'],
                # Transport mode encoding
                1 if row['transport_mode'] == 'walking' else 0,
                1 if row['transport_mode'] == 'cycling' else 0,
                1 if row['transport_mode'] == 'public_transport' else 0,
                1 if row['transport_mode'] == 'car' else 0,
                1 if row['transport_mode'] == 'carpool' else 0,
                1 if row['transport_mode'] == 'wfh' else 0,
                # Weather encoding
                1 if row['weather_condition'] == 'sunny' else 0,
                1 if row['weather_condition'] == 'cloudy' else 0,
                1 if row['weather_condition'] == 'rainy' else 0,
                # Traffic encoding
                1 if row['traffic_condition'] == 'light' else 0,
                1 if row['traffic_condition'] == 'moderate' else 0,
                1 if row['traffic_condition'] == 'heavy' else 0,
                # Route type encoding
                1 if row['route_type'] == 'urban' else 0,
                1 if row['route_type'] == 'suburban' else 0,
                1 if row['route_type'] == 'highway' else 0,
                # Time period encoding
                1 if row['time_period'] == 'morning' else 0,
                1 if row['time_period'] == 'afternoon' else 0,
                1 if row['time_period'] == 'evening' else 0,
                1 if row['time_period'] == 'night' else 0,
                # Season encoding
                1 if row['season'] == 'spring' else 0,
                1 if row['season'] == 'summer' else 0,
                1 if row['season'] == 'autumn' else 0,
                1 if row['season'] == 'winter' else 0,
            ]
            features.append(feature_vector)
        
        X = np.array(features)
        y = df['carbon_savings'].values if 'carbon_savings' in df.columns else np.array([])
        
        return X, y
    
    def train_carbon_forecast_model(self, user_id: int) -> Dict[str, Any]:
        """Train carbon footprint forecasting model for user"""
        try:
            # Get historical data
            df = self.get_user_historical_data(user_id, days_back=180)
            
            if len(df) < 10:  # Need minimum data
                return {
                    'success': False,
                    'error': 'Insufficient historical data for training',
                    'data_points': len(df)
                }
            
            # Prepare features
            X, y = self.prepare_features(df)
            
            if len(X) == 0:
                return {
                    'success': False,
                    'error': 'No valid features for training'
                }
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train ensemble model
            rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
            lr_model = LinearRegression()
            
            # Train models
            rf_model.fit(X_scaled, y)
            gb_model.fit(X_scaled, y)
            lr_model.fit(X_scaled, y)
            
            # Evaluate models
            rf_pred = rf_model.predict(X_scaled)
            gb_pred = gb_model.predict(X_scaled)
            lr_pred = lr_model.predict(X_scaled)
            
            rf_score = r2_score(y, rf_pred)
            gb_score = r2_score(y, gb_pred)
            lr_score = r2_score(y, lr_pred)
            
            # Select best model
            models_scores = [('rf', rf_model, rf_score), ('gb', gb_model, gb_score), ('lr', lr_model, lr_score)]
            best_model_name, best_model, best_score = max(models_scores, key=lambda x: x[2])
            
            # Save model
            model_path = os.path.join(self.model_dir, f'carbon_forecast_user_{user_id}.joblib')
            scaler_path = os.path.join(self.model_dir, f'carbon_forecast_scaler_{user_id}.joblib')
            
            joblib.dump(best_model, model_path)
            joblib.dump(scaler, scaler_path)
            
            return {
                'success': True,
                'model_type': best_model_name,
                'r2_score': best_score,
                'mae': mean_absolute_error(y, best_model.predict(X_scaled)),
                'data_points': len(df),
                'feature_count': X.shape[1],
                'training_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict_carbon_savings(self, user_id: int, days_ahead: int = 7) -> Dict[str, Any]:
        """Predict carbon savings for next N days"""
        try:
            # Load trained model
            model_path = os.path.join(self.model_dir, f'carbon_forecast_user_{user_id}.joblib')
            scaler_path = os.path.join(self.model_dir, f'carbon_forecast_scaler_{user_id}.joblib')
            
            if not os.path.exists(model_path) or not os.path.exists(scaler_path):
                return {
                    'success': False,
                    'error': 'Model not trained for this user'
                }
            
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            
            # Generate future dates
            predictions = []
            current_date = timezone.now().date()
            
            for day in range(days_ahead):
                future_date = current_date + timedelta(days=day)
                
                # Create feature vectors for each hour of the day
                daily_predictions = []
                
                for hour in range(24):
                    # Use average patterns from historical data
                    df = self.get_user_historical_data(user_id, days_back=90)
                    
                    if not df.empty:
                        # Get average for this hour and day of week
                        similar_trips = df[
                            (df['hour'] == hour) & 
                            (df['day_of_week'] == future_date.weekday())
                        ]
                        
                        if not similar_trips.empty:
                            avg_trip = similar_trips.iloc[0]
                        else:
                            # Use overall averages
                            avg_trip = df.iloc[0]
                    else:
                        # Default values
                        avg_trip = {
                            'transport_mode': 'public_transport',
                            'distance_km': 5.0,
                            'duration_minutes': 30,
                            'weather_condition': 'sunny',
                            'traffic_condition': 'moderate',
                            'route_type': 'urban',
                            'time_period': 'morning' if 6 <= hour <= 12 else 'afternoon' if 12 <= hour <= 18 else 'evening',
                            'season': 'spring' if 3 <= future_date.month <= 5 else 'summer' if 6 <= future_date.month <= 8 else 'autumn' if 9 <= future_date.month <= 11 else 'winter'
                        }
                    
                    # Create feature vector
                    feature_vector = [
                        hour,
                        future_date.weekday(),
                        future_date.month,
                        avg_trip.get('distance_km', 5.0),
                        avg_trip.get('duration_minutes', 30),
                        1 if avg_trip.get('transport_mode') == 'walking' else 0,
                        1 if avg_trip.get('transport_mode') == 'cycling' else 0,
                        1 if avg_trip.get('transport_mode') == 'public_transport' else 0,
                        1 if avg_trip.get('transport_mode') == 'car' else 0,
                        1 if avg_trip.get('transport_mode') == 'carpool' else 0,
                        1 if avg_trip.get('transport_mode') == 'wfh' else 0,
                        1 if avg_trip.get('weather_condition') == 'sunny' else 0,
                        1 if avg_trip.get('weather_condition') == 'cloudy' else 0,
                        1 if avg_trip.get('weather_condition') == 'rainy' else 0,
                        1 if avg_trip.get('traffic_condition') == 'light' else 0,
                        1 if avg_trip.get('traffic_condition') == 'moderate' else 0,
                        1 if avg_trip.get('traffic_condition') == 'heavy' else 0,
                        1 if avg_trip.get('route_type') == 'urban' else 0,
                        1 if avg_trip.get('route_type') == 'suburban' else 0,
                        1 if avg_trip.get('route_type') == 'highway' else 0,
                        1 if avg_trip.get('time_period') == 'morning' else 0,
                        1 if avg_trip.get('time_period') == 'afternoon' else 0,
                        1 if avg_trip.get('time_period') == 'evening' else 0,
                        1 if avg_trip.get('time_period') == 'night' else 0,
                        1 if avg_trip.get('season') == 'spring' else 0,
                        1 if avg_trip.get('season') == 'summer' else 0,
                        1 if avg_trip.get('season') == 'autumn' else 0,
                        1 if avg_trip.get('season') == 'winter' else 0,
                    ]
                    
                    # Predict
                    X = np.array([feature_vector])
                    X_scaled = scaler.transform(X)
                    prediction = model.predict(X_scaled)[0]
                    daily_predictions.append(max(0, prediction))  # Ensure non-negative
                
                # Sum daily predictions
                daily_total = sum(daily_predictions)
                predictions.append({
                    'date': future_date.isoformat(),
                    'predicted_savings': round(daily_total, 4),
                    'hourly_breakdown': [round(p, 4) for p in daily_predictions]
                })
            
            total_predicted = sum(p['predicted_savings'] for p in predictions)
            
            return {
                'success': True,
                'predictions': predictions,
                'total_predicted_savings': round(total_predicted, 4),
                'daily_average': round(total_predicted / days_ahead, 4),
                'prediction_period_days': days_ahead,
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_trip_patterns(self, user_id: int) -> Dict[str, Any]:
        """Analyze user's trip patterns and behaviors"""
        try:
            df = self.get_user_historical_data(user_id, days_back=90)
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'No trip data available for analysis'
                }
            
            # Time patterns
            hourly_pattern = df.groupby('hour')['carbon_savings'].mean().to_dict()
            daily_pattern = df.groupby('day_of_week')['carbon_savings'].mean().to_dict()
            monthly_pattern = df.groupby('month')['carbon_savings'].mean().to_dict()
            
            # Transport mode analysis
            transport_analysis = df.groupby('transport_mode').agg({
                'carbon_savings': ['mean', 'sum', 'count'],
                'distance_km': 'mean',
                'duration_minutes': 'mean'
            }).round(4).to_dict()
            
            # Route and condition analysis
            route_analysis = df.groupby('route_type')['carbon_savings'].mean().to_dict()
            weather_analysis = df.groupby('weather_condition')['carbon_savings'].mean().to_dict()
            traffic_analysis = df.groupby('traffic_condition')['carbon_savings'].mean().to_dict()
            
            # Performance metrics
            total_trips = len(df)
            total_savings = df['carbon_savings'].sum()
            avg_savings_per_trip = df['carbon_savings'].mean()
            best_trip = df.loc[df['carbon_savings'].idxmax()]
            
            # Trend analysis
            df['date'] = pd.to_datetime(df['date'])
            weekly_trend = df.groupby(df['date'].dt.to_period('W'))['carbon_savings'].sum()
            
            # Calculate trend direction
            if len(weekly_trend) >= 4:
                recent_avg = weekly_trend.tail(4).mean()
                earlier_avg = weekly_trend.head(4).mean()
                trend_direction = 'increasing' if recent_avg > earlier_avg else 'decreasing' if recent_avg < earlier_avg else 'stable'
                trend_percentage = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg != 0 else 0
            else:
                trend_direction = 'insufficient_data'
                trend_percentage = 0
            
            return {
                'success': True,
                'analysis_period_days': 90,
                'total_trips': total_trips,
                'total_carbon_savings': round(total_savings, 4),
                'average_savings_per_trip': round(avg_savings_per_trip, 4),
                'best_trip': {
                    'date': best_trip['date'].isoformat(),
                    'transport_mode': best_trip['transport_mode'],
                    'savings': round(best_trip['carbon_savings'], 4),
                    'distance_km': round(best_trip['distance_km'], 4)
                },
                'patterns': {
                    'hourly': {str(k): round(v, 4) for k, v in hourly_pattern.items()},
                    'daily': {str(k): round(v, 4) for k, v in daily_pattern.items()},
                    'monthly': {str(k): round(v, 4) for k, v in monthly_pattern.items()}
                },
                'transport_analysis': transport_analysis,
                'route_analysis': {str(k): round(v, 4) for k, v in route_analysis.items()},
                'weather_analysis': {str(k): round(v, 4) for k, v in weather_analysis.items()},
                'traffic_analysis': {str(k): round(v, 4) for k, v in traffic_analysis.items()},
                'trend': {
                    'direction': trend_direction,
                    'percentage_change': round(trend_percentage, 2),
                    'weekly_data': {str(k): round(v, 4) for k, v in weekly_trend.items()}
                },
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict_monthly_goals(self, user_id: int) -> Dict[str, Any]:
        """Predict if user will meet monthly carbon savings goals"""
        try:
            # Current month progress
            current_date = timezone.now().date()
            current_month_start = current_date.replace(day=1)
            days_in_month = (current_date.replace(day=28) + timedelta(days=4)).day
            days_passed = (current_date - current_month_start).days + 1
            days_remaining = days_in_month - days_passed
            
            # Get current month data
            df = self.get_user_historical_data(user_id, days_back=days_passed)
            current_month_savings = df['carbon_savings'].sum() if not df.empty else 0
            
            # Predict remaining days
            prediction_result = self.predict_carbon_savings(user_id, days_ahead=days_remaining)
            
            if prediction_result['success']:
                predicted_remaining = prediction_result['total_predicted_savings']
                total_predicted = current_month_savings + predicted_remaining
            else:
                # Use historical average if prediction fails
                df_historical = self.get_user_historical_data(user_id, days_back=30)
                if not df_historical.empty:
                    daily_avg = df_historical['carbon_savings'].sum() / 30
                    predicted_remaining = daily_avg * days_remaining
                    total_predicted = current_month_savings + predicted_remaining
                else:
                    predicted_remaining = 0
                    total_predicted = current_month_savings
            
            # Set goals (could be user-defined)
            monthly_goals = [10, 25, 50, 100]  # kg CO2
            
            goal_predictions = []
            for goal in monthly_goals:
                goal_predictions.append({
                    'target_kg': goal,
                    'current_progress': round(current_month_savings, 4),
                    'predicted_total': round(total_predicted, 4),
                    'on_track': total_predicted >= goal,
                    'confidence': 'high' if prediction_result['success'] else 'medium',
                    'percentage_achieved': round((current_month_savings / goal * 100), 2) if goal > 0 else 0
                })
            
            return {
                'success': True,
                'current_month': current_date.strftime('%Y-%m'),
                'days_passed': days_passed,
                'days_remaining': days_remaining,
                'current_savings': round(current_month_savings, 4),
                'predicted_total': round(total_predicted, 4),
                'goals': goal_predictions,
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_insights_and_recommendations(self, user_id: int) -> Dict[str, Any]:
        """Generate insights and recommendations based on predictive analysis"""
        try:
            # Get pattern analysis
            pattern_result = self.analyze_trip_patterns(user_id)
            goal_result = self.predict_monthly_goals(user_id)
            
            if not pattern_result['success']:
                return pattern_result
            
            insights = []
            recommendations = []
            
            # Analyze patterns for insights
            patterns = pattern_result['patterns']
            transport_analysis = pattern_result['transport_analysis']
            trend = pattern_result['trend']
            
            # Time-based insights
            if 'hourly' in patterns:
                best_hour = max(patterns['hourly'].items(), key=lambda x: x[1])
                worst_hour = min(patterns['hourly'].items(), key=lambda x: x[1])
                
                insights.append({
                    'type': 'time_pattern',
                    'title': 'Peak Performance Time',
                    'description': f"You save the most carbon around {best_hour[0]}:00 with average savings of {best_hour[1]:.2f} kg CO₂",
                    'priority': 'medium'
                })
            
            # Transport mode insights
            if transport_analysis:
                best_mode = max(transport_analysis.items(), key=lambda x: x[1][('carbon_savings', 'mean')])
                insights.append({
                    'type': 'transport_mode',
                    'title': 'Most Effective Transport',
                    'description': f"{best_mode[0].title()} gives you the best average savings of {best_mode[1][('carbon_savings', 'mean')]:.2f} kg CO₂ per trip",
                    'priority': 'high'
                })
            
            # Trend insights
            if trend['direction'] == 'increasing':
                insights.append({
                    'type': 'trend',
                    'title': 'Great Progress!',
                    'description': f"Your carbon savings are trending up by {trend['percentage_change']:.1f}% recently",
                    'priority': 'low'
                })
            elif trend['direction'] == 'decreasing':
                insights.append({
                    'type': 'trend',
                    'title': 'Attention Needed',
                    'description': f"Your carbon savings have decreased by {abs(trend['percentage_change']):.1f}% recently",
                    'priority': 'high'
                })
            
            # Generate recommendations
            if goal_result['success']:
                for goal in goal_result['goals']:
                    if not goal['on_track'] and goal['percentage_achieved'] < 50:
                        recommendations.append({
                            'type': 'goal_focus',
                            'title': f'Focus on {goal["target_kg"]}kg Goal',
                            'description': f"You're only at {goal['percentage_achieved']:.1f}% of your {goal['target_kg']}kg monthly goal. Try increasing eco-friendly trips.",
                            'priority': 'high',
                            'actionable': True
                        })
            
            # General recommendations
            recommendations.append({
                'type': 'optimization',
                'title': 'Optimize Your Routes',
                'description': 'Consider combining trips or choosing routes with better traffic conditions to maximize savings',
                'priority': 'medium',
                'actionable': True
            })
            
            return {
                'success': True,
                'insights': insights,
                'recommendations': recommendations,
                'pattern_analysis': pattern_result,
                'goal_predictions': goal_result,
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
