"""
Enhanced NLP URLs for Advanced Sustainability Insights
"""

from django.urls import path
from .views import enhanced_nlp_views

app_name = 'enhanced_nlp'

urlpatterns = [
    # Dashboard
    path('dashboard/', enhanced_nlp_views.nlp_dashboard, name='nlp_dashboard'),
    
    # NLP Query Processing
    path('api/process-query/', enhanced_nlp_views.process_nlp_query, name='process_nlp_query'),
    
    # Chat API
    path('api/chat/', enhanced_nlp_views.chat_api, name='chat_api'),
    
    # Carbon Insights
    path('api/carbon-insights/', enhanced_nlp_views.get_carbon_insights, name='carbon_insights'),
    
    # Sustainability Tips
    path('api/sustainability-tips/', enhanced_nlp_views.get_sustainability_tips, name='sustainability_tips'),
    
    # Environmental Impact
    path('api/environmental-impact/', enhanced_nlp_views.get_environmental_impact, name='environmental_impact'),
]
