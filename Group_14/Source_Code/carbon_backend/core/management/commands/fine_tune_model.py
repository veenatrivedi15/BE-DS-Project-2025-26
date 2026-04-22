"""
Fine-tune the predictive analytics model with hyperparameter optimization
"""
import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import json
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Fine-tune predictive analytics model with hyperparameter optimization'

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
        parser.add_argument(
            '--cv-folds',
            type=int,
            default=5,
            help='Cross-validation folds (default: 5)'
        )

    def handle(self, *args, **options):
        data_file = options['data_file']
        test_size = options['test_size']
        cv_folds = options['cv_folds']
        
        self.stdout.write(self.style.SUCCESS(f'Starting model fine-tuning with {data_file}'))
        
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
            
            # Feature selection
            X_train_selected, X_test_selected, selected_features = self.select_features(X_train, X_test, y_train)
            
            # Fine-tune models
            models = self.fine_tune_models(X_train_selected, y_train, cv_folds)
            
            # Evaluate models
            results = self.evaluate_models(models, X_test_selected, y_test)
            
            # Save best model
            best_model_name = min(results.keys(), key=lambda k: results[k]['mse'])
            best_model = models[best_model_name]
            
            self.save_model(best_model, best_model_name, selected_features)
            
            # Display results
            self.display_results(results, best_model_name, selected_features)
            
            self.stdout.write(self.style.SUCCESS('Model fine-tuning completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during fine-tuning: {str(e)}'))
            raise

    def preprocess_data(self, df):
        """Enhanced preprocessing with feature engineering"""
        self.stdout.write('Preprocessing data with feature engineering...')
        
        # Handle missing values
        df = df.fillna(0)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Extract time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week_num'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = (df['timestamp'].dt.dayofweek >= 5).astype(int)
        
        # Feature engineering
        df['speed_efficiency'] = df['distance_km'] / (df['trip_duration_minutes'] + 1)
        df['cost_per_km'] = df['estimated_cost_inr'] / (df['distance_km'] + 1)
        df['emission_per_km'] = (df['ef_actual'] * df['distance_km']) / (df['distance_km'] + 1)
        df['context_score'] = df['peak_factor'] * df['traffic_multiplier'] * df['weather_factor']
        df['environmental_impact'] = df['aqi_factor'] * df['context_factor']
        
        # Select features for training
        feature_columns = [
            'distance_km', 'trip_duration_minutes', 'average_speed_kmph',
            'seasonal_factor', 'ef_baseline', 'ef_actual', 'emission_difference',
            'peak_factor', 'traffic_multiplier', 'recency_weight', 'time_weight',
            'weather_factor', 'route_factor', 'load_factor', 'aqi_factor',
            'context_factor', 'user_age', 'hour', 'day_of_week_num', 'month',
            'is_weekend', 'speed_efficiency', 'cost_per_km', 'emission_per_km',
            'context_score', 'environmental_impact'
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
        
        with open('fine_tuned_preprocessing.json', 'w') as f:
            json.dump(preprocessing_data, f, indent=2)
        
        self.stdout.write(f'Preprocessing complete. Features: {len(feature_columns)}')
        return X_scaled, y

    def select_features(self, X_train, X_test, y_train):
        """Select best features using statistical tests"""
        self.stdout.write('Selecting best features...')
        
        # Use SelectKBest with f_regression
        selector = SelectKBest(score_func=f_regression, k=25)
        X_train_selected = selector.fit_transform(X_train, y_train)
        X_test_selected = selector.transform(X_test)
        
        # Get selected feature names
        selected_features = [X_train.columns[i] for i in selector.get_support(indices=True)]
        
        self.stdout.write(f'Selected {len(selected_features)} best features')
        return X_train_selected, X_test_selected, selected_features

    def fine_tune_models(self, X_train, y_train, cv_folds):
        """Fine-tune models with hyperparameter optimization"""
        self.stdout.write('Fine-tuning models with hyperparameter optimization...')
        
        models = {}
        
        # Random Forest with Grid Search
        rf_param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [10, 15, 20, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', None]
        }
        
        rf = GridSearchCV(
            RandomForestRegressor(random_state=42),
            rf_param_grid,
            cv=cv_folds,
            scoring='neg_mean_squared_error',
            n_jobs=-1,
            verbose=1
        )
        rf.fit(X_train, y_train)
        models['Random Forest'] = rf.best_estimator_
        
        # Gradient Boosting with Grid Search
        gb_param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.01, 0.1, 0.2],
            'max_depth': [5, 10, 15],
            'subsample': [0.8, 0.9, 1.0]
        }
        
        gb = GridSearchCV(
            GradientBoostingRegressor(random_state=42),
            gb_param_grid,
            cv=cv_folds,
            scoring='neg_mean_squared_error',
            n_jobs=-1,
            verbose=1
        )
        gb.fit(X_train, y_train)
        models['Gradient Boosting'] = gb.best_estimator_
        
        self.stdout.write(f'Fine-tuned {len(models)} models')
        return models

    def evaluate_models(self, models, X_test, y_test):
        """Evaluate all fine-tuned models"""
        self.stdout.write('Evaluating fine-tuned models...')
        
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
        """Save the fine-tuned model"""
        model_data = {
            'model': model,
            'model_name': f'{model_name} (Fine-Tuned)',
            'feature_columns': feature_columns,
            'trained_at': datetime.now().isoformat(),
            'model_type': 'carbon_credits_predictor_fine_tuned',
            'fine_tuned': True
        }
        
        # Save using pickle
        with open('fine_tuned_predictive_model.pkl', 'wb') as f:
            pickle.dump(model_data, f)
        
        self.stdout.write(f'Saved fine-tuned model: {model_name}')

    def display_results(self, results, best_model_name, selected_features):
        """Display fine-tuning results"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('FINE-TUNED MODEL RESULTS'))
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
        self.stdout.write(f'Selected Features ({len(selected_features)}): {", ".join(selected_features[:10])}...')
        self.stdout.write('='*60)
