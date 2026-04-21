"""
Train predictive analytics model using enhanced carbon credits dataset
"""
import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import json
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Train predictive analytics model using enhanced carbon credits dataset'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-file',
            type=str,
            default='enhanced_carbon_credits_250_records.csv',
            help='Path to the CSV data file'
        )
        parser.add_argument(
            '--test-size',
            type=float,
            default=0.2,
            help='Test set proportion (default: 0.2)'
        )

    def handle(self, *args, **options):
        data_file = options['data_file']
        test_size = options['test_size']
        
        self.stdout.write(self.style.SUCCESS(f'Starting model training with {data_file}'))
        
        try:
            # Load data
            df = pd.read_csv(data_file)
            self.stdout.write(f'Loaded dataset: {df.shape[0]} records, {df.shape[1]} features')
            
            # Preprocess data
            X, y = self.preprocess_data(df)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Train models
            models = self.train_models(X_train, y_train)
            
            # Evaluate models
            results = self.evaluate_models(models, X_test, y_test)
            
            # Save best model
            best_model_name = min(results.keys(), key=lambda k: results[k]['mse'])
            best_model = models[best_model_name]
            
            self.save_model(best_model, best_model_name, X.columns.tolist())
            
            # Display results
            self.display_results(results, best_model_name)
            
            self.stdout.write(self.style.SUCCESS('Model training completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during training: {str(e)}'))
            raise

    def preprocess_data(self, df):
        """Preprocess the dataset for training"""
        self.stdout.write('Preprocessing data...')
        
        # Handle missing values
        df = df.fillna(0)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Extract time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week_num'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        
        # Select features for training
        feature_columns = [
            'distance_km', 'trip_duration_minutes', 'average_speed_kmph',
            'seasonal_factor', 'ef_baseline', 'ef_actual', 'emission_difference',
            'peak_factor', 'traffic_multiplier', 'recency_weight', 'time_weight',
            'weather_factor', 'route_factor', 'load_factor', 'aqi_factor',
            'context_factor', 'user_age', 'hour', 'day_of_week_num', 'month'
        ]
        
        # Encode categorical variables
        categorical_columns = ['transport_mode', 'mode_type', 'city', 'season', 
                           'time_period', 'traffic_condition', 'weather_condition', 
                           'route_type', 'aqi_level', 'trip_purpose']
        
        label_encoders = {}
        for col in categorical_columns:
            if col in df.columns:
                le = LabelEncoder()
                df[col + '_encoded'] = le.fit_transform(df[col].astype(str))
                feature_columns.append(col + '_encoded')
                label_encoders[col] = le
        
        # Prepare features and target
        X = df[feature_columns]
        y = df['carbon_credits_earned']
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=X.columns)
        
        # Save preprocessing objects
        preprocessing_data = {
            'label_encoders': {k: v.classes_.tolist() for k, v in label_encoders.items()},
            'feature_columns': feature_columns,
            'scaler_mean': scaler.mean_.tolist(),
            'scaler_scale': scaler.scale_.tolist()
        }
        
        with open('predictive_model_preprocessing.json', 'w') as f:
            json.dump(preprocessing_data, f, indent=2)
        
        self.stdout.write(f'Preprocessing complete. Features: {len(feature_columns)}')
        return X_scaled, y

    def train_models(self, X_train, y_train):
        """Train multiple regression models"""
        self.stdout.write('Training models...')
        
        models = {}
        
        # Random Forest
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        rf.fit(X_train, y_train)
        models['Random Forest'] = rf
        
        # Gradient Boosting
        gb = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=10,
            random_state=42
        )
        gb.fit(X_train, y_train)
        models['Gradient Boosting'] = gb
        
        # Linear Regression
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        models['Linear Regression'] = lr
        
        self.stdout.write(f'Trained {len(models)} models')
        return models

    def evaluate_models(self, models, X_test, y_test):
        """Evaluate all trained models"""
        self.stdout.write('Evaluating models...')
        
        results = {}
        
        for name, model in models.items():
            y_pred = model.predict(X_test)
            
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_test, y_test, cv=5, scoring='neg_mean_squared_error')
            cv_mse = -cv_scores.mean()
            
            results[name] = {
                'mse': mse,
                'mae': mae,
                'r2': r2,
                'cv_mse': cv_mse,
                'rmse': np.sqrt(mse)
            }
            
            self.stdout.write(f'  {name}: MSE={mse:.4f}, MAE={mae:.4f}, R²={r2:.4f}')
        
        return results

    def save_model(self, model, model_name, feature_columns):
        """Save the trained model"""
        model_data = {
            'model': model,
            'model_name': model_name,
            'feature_columns': feature_columns,
            'trained_at': datetime.now().isoformat(),
            'model_type': 'carbon_credits_predictor'
        }
        
        # Save using pickle
        with open('predictive_analytics_model.pkl', 'wb') as f:
            pickle.dump(model_data, f)
        
        self.stdout.write(f'Saved model: {model_name}')

    def display_results(self, results, best_model_name):
        """Display training results"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('MODEL EVALUATION RESULTS'))
        self.stdout.write('='*60)
        
        for name, metrics in results.items():
            status = 'BEST' if name == best_model_name else '  '
            self.stdout.write(f'{status} {name}:')
            self.stdout.write(f'    MSE: {metrics["mse"]:.4f}')
            self.stdout.write(f'    MAE: {metrics["mae"]:.4f}')
            self.stdout.write(f'    R²:  {metrics["r2"]:.4f}')
            self.stdout.write(f'    RMSE: {metrics["rmse"]:.4f}')
            self.stdout.write(f'    CV-MSE: {metrics["cv_mse"]:.4f}')
            self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS(f'Best Model: {best_model_name}'))
        self.stdout.write('='*60)
