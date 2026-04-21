"""
URL patterns for pollution awareness features
"""
from django.urls import path
from .views.pollution_views import (
    pollution_dashboard, location_pollution_analysis, 
    get_real_time_pollution, check_pollution_alerts, 
    mark_alert_read, industrial_zones_map, pollution_impact_history,
    get_pollution_zones
)
from .aqi_views import aqi_tile_proxy

app_name = 'pollution'

urlpatterns = [
    path('dashboard/', pollution_dashboard, name='dashboard'),
    path('location/<int:location_id>/', location_pollution_analysis, name='location_analysis'),
    path('api/real-time-pollution/', get_real_time_pollution, name='real_time_pollution'),
    path('api/check-alerts/', check_pollution_alerts, name='check_alerts'),
    path('api/mark-alert-read/<int:alert_id>/', mark_alert_read, name='mark_alert_read'),
    path('api/zones/', get_pollution_zones, name='zones'),
    path('industrial-zones-map/', industrial_zones_map, name='industrial_zones_map'),
    path('impact-history/', pollution_impact_history, name='impact_history'),
    path('aqi-tiles/<str:layer>/<int:z>/<int:x>/<int:y>.png', aqi_tile_proxy, name='aqi_tile_proxy'),
]
