"""
Test ML prediction with fine-tuned model
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.core.management.base import BaseCommand
from core.ml_predictor import get_predictor


class Command(BaseCommand):
    help = 'Test ML prediction with fine-tuned model'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing ML prediction with fine-tuned model...'))
        
        # Get predictor
        predictor = get_predictor()
        
        if not predictor.is_available():
            self.stdout.write(self.style.ERROR('ML model not available'))
            return
        
        # Test cases with all required features
        test_cases = [
            {
                'name': 'Short City Commute',
                'transport_mode': 'petrol_car',
                'distance_km': 15.0,
                'trip_duration_minutes': 30.0,
                'average_speed_kmph': 30.0,
                'time_period': 'peak_morning',
                'traffic_condition': 'heavy',
                'weather_condition': 'normal',
                'route_type': 'city_center',
                'aqi_level': 'moderate',
                'season': 'summer',
                'user_age': 30,
                'hour': 8,
                'day_of_week_num': 0,
                'month': 6,
                'city': 'Mumbai',
                'trip_purpose': 'business',
                'load_factor': 1.0
            },
            {
                'name': 'Long Highway Trip',
                'transport_mode': 'electric_car',
                'distance_km': 50.0,
                'trip_duration_minutes': 60.0,
                'average_speed_kmph': 50.0,
                'time_period': 'off_peak',
                'traffic_condition': 'light',
                'weather_condition': 'favorable',
                'route_type': 'highway',
                'aqi_level': 'good',
                'season': 'winter',
                'user_age': 35,
                'hour': 14,
                'day_of_week_num': 2,
                'month': 12,
                'city': 'Bangalore',
                'trip_purpose': 'business',
                'load_factor': 1.0
            },
            {
                'name': 'Eco-friendly Commute',
                'transport_mode': 'bicycle',
                'distance_km': 8.0,
                'trip_duration_minutes': 25.0,
                'average_speed_kmph': 19.2,
                'time_period': 'off_peak',
                'traffic_condition': 'moderate',
                'weather_condition': 'favorable',
                'route_type': 'suburban',
                'aqi_level': 'good',
                'season': 'post_monsoon',
                'user_age': 28,
                'hour': 9,
                'day_of_week_num': 4,
                'month': 10,
                'city': 'Pune',
                'trip_purpose': 'commute',
                'load_factor': 1.0
            }
        ]
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('ML PREDICTION TEST RESULTS'))
        self.stdout.write('='*60)
        
        for i, test_case in enumerate(test_cases, 1):
            result = predictor.predict(**test_case)
            
            self.stdout.write(f'\nTest Case {i}: {test_case["name"]}')
            self.stdout.write(f'  Transport: {test_case["transport_mode"]}')
            self.stdout.write(f'  Distance: {test_case["distance_km"]} km')
            self.stdout.write(f'  Duration: {test_case["trip_duration_minutes"]} min')
            
            if result['prediction'] is not None:
                self.stdout.write(self.style.SUCCESS(f'  Predicted Credits: {result["prediction"]:.4f}'))
                self.stdout.write(f'  Confidence: {result["confidence"]:.2%}')
                self.stdout.write(f'  Method: {result["method"]}')
            else:
                self.stdout.write(self.style.ERROR(f'  Prediction Failed: {result.get("error", "Unknown error")}'))
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('ML prediction test completed!'))
        self.stdout.write('='*60)
