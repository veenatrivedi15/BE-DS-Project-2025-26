"""
API views for frontend AJAX requests
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def get_environment_data(request):
    """
    API endpoint to get automatically detected environment data.
    
    Expected POST data:
    {
        "start_lat": float,
        "start_lng": float,
        "end_lat": float,
        "end_lng": float,
        "trip_time": "ISO datetime string"
    }
    
    Returns:
    {
        "time_period": str,
        "traffic_condition": str,
        "weather_condition": str,
        "route_type": str,
        "aqi_level": str,
        "season": str,
        "data_sources": {...}
    }
    """
    try:
        data = json.loads(request.body)
        
        start_lat = float(data.get('start_lat', 0))
        start_lng = float(data.get('start_lng', 0))
        end_lat = float(data.get('end_lat', 0))
        end_lng = float(data.get('end_lng', 0))
        trip_time_str = data.get('trip_time')
        
        if not all([start_lat, start_lng, end_lat, end_lng]):
            return JsonResponse({
                'error': 'Missing location coordinates'
            }, status=400)
        
        # Parse trip time
        if trip_time_str:
            try:
                trip_time = datetime.fromisoformat(trip_time_str.replace('Z', '+00:00'))
            except:
                trip_time = timezone.now()
        else:
            trip_time = timezone.now()
        
        # Get environment data
        from core.utils.environment_data import get_all_environment_data
        
        env_data = get_all_environment_data(
            start_lat, start_lng, end_lat, end_lng, trip_time
        )
        
        return JsonResponse(env_data)
        
    except Exception as e:
        logger.error(f"Error in get_environment_data: {str(e)}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


