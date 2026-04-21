"""
Predictive Analytics URLs for Carbon Credits Platform
Handles URL routing for carbon footprint forecasting, trip pattern analysis, and trend prediction
"""

from django.urls import path
from .views import predictive_analytics_views

app_name = 'predictive_analytics'

urlpatterns = [
    # Dashboard
    path('dashboard/', predictive_analytics_views.predictive_analytics_dashboard, name='predictive_dashboard'),
    
    # Model Training
    path('api/train-model/', predictive_analytics_views.train_user_model, name='train_model'),
    
    # Predictions
    path('api/predict-savings/', predictive_analytics_views.predict_carbon_savings, name='predict_savings'),
    path('api/predict-goals/', predictive_analytics_views.predict_monthly_goals, name='predict_goals'),
    
    # Analysis
    path('api/analyze-patterns/', predictive_analytics_views.analyze_trip_patterns, name='analyze_patterns'),
    path('api/insights/', predictive_analytics_views.get_insights_and_recommendations, name='get_insights'),
    
    # Overview
    path('api/overview/', predictive_analytics_views.get_analytics_overview, name='analytics_overview'),
]
