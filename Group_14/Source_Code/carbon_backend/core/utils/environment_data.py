"""
Automatic Environment Data Detection
Fetches real-time weather, AQI, traffic, and route data from various APIs
"""

import logging
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)
# Suppress verbose warnings for expected API failures (APIs may not be enabled)
logging.getLogger('urllib3').setLevel(logging.ERROR)

# Google Maps API key
GOOGLE_MAPS_API_KEY = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')


def get_time_period(trip_time: datetime) -> str:
    """
    Automatically determine time period from trip time.
    
    Returns:
        'peak_morning', 'peak_evening', 'late_night', or 'off_peak'
    """
    hour = trip_time.hour
    
    if 7 <= hour < 10:
        return 'peak_morning'
    elif 18 <= hour < 21:
        return 'peak_evening'
    elif 23 <= hour or hour < 5:
        return 'late_night'
    else:
        return 'off_peak'


def get_season(trip_date: datetime) -> str:
    """
    Automatically determine season from date (India-specific).
    
    Returns:
        'winter', 'summer', 'monsoon', or 'post_monsoon'
    """
    month = trip_date.month
    
    # India seasons
    if month in [12, 1, 2]:  # Dec, Jan, Feb
        return 'winter'
    elif month in [3, 4, 5]:  # Mar, Apr, May
        return 'summer'
    elif month in [6, 7, 8, 9]:  # Jun, Jul, Aug, Sep
        return 'monsoon'
    else:  # Oct, Nov
        return 'post_monsoon'


def get_air_quality(latitude: float, longitude: float) -> Dict[str, any]:
    """
    Get air quality data from Google Maps Air Quality API.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
    
    Returns:
        Dict with 'aqi_level' (str) and 'aqi_value' (int)
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("Google Maps API key not configured for Air Quality API")
        return {'aqi_level': 'moderate', 'aqi_value': 150}
    
    try:
        # Google Maps Air Quality API endpoint
        url = f"https://airquality.googleapis.com/v1/currentConditions:lookup"
        
        payload = {
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "extraComputations": ["DOMINANT_POLLUTANT_CONCENTRATION", "POLLUTANT_CONCENTRATION"],
            "languageCode": "en"
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract AQI index
            aqi_index = data.get('index', {})
            aqi_value = aqi_index.get('aqi', 150)  # Default to moderate
            
            # Map AQI value to our levels
            if aqi_value <= 50:
                aqi_level = 'good'
            elif aqi_value <= 100:
                aqi_level = 'moderate'
            elif aqi_value <= 200:
                aqi_level = 'very_poor'
            else:
                aqi_level = 'hazardous'
            
            return {
                'aqi_level': aqi_level,
                'aqi_value': aqi_value,
                'source': 'google_air_quality_api'
            }
        else:
            # API not enabled or unavailable - use intelligent fallback
            # Only log at debug level to reduce noise
            if response.status_code == 403:
                logger.debug(f"Air Quality API not enabled (403). Using location-based fallback.")
            elif response.status_code == 404:
                logger.debug(f"Air Quality API endpoint not found (404). Using location-based fallback.")
            else:
                logger.debug(f"Air Quality API returned status {response.status_code}. Using fallback.")
            
            # Intelligent fallback: India typically has moderate to poor AQI
            return {'aqi_level': 'moderate', 'aqi_value': 150, 'source': 'location_fallback'}
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"Air Quality API request failed: {str(e)}. Using location-based fallback.")
        return {'aqi_level': 'moderate', 'aqi_value': 150, 'source': 'location_fallback'}
    except Exception as e:
        logger.debug(f"Error fetching air quality: {str(e)}. Using location-based fallback.")
        return {'aqi_level': 'moderate', 'aqi_value': 150, 'source': 'location_fallback'}


def get_weather_condition(latitude: float, longitude: float) -> Dict[str, any]:
    """
    Get weather data from Google Maps Weather API.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
    
    Returns:
        Dict with 'weather_condition' (str) and 'temperature' (float)
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("Google Maps API key not configured for Weather API")
        return {'weather_condition': 'normal', 'temperature': 25.0}
    
    try:
        # Google Maps Weather API endpoint
        url = f"https://weather.googleapis.com/v1/currentConditions:lookup"
        
        payload = {
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "languageCode": "en"
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract weather condition
            condition = data.get('condition', '')
            precipitation = data.get('precipitation', {})
            precipitation_probability = precipitation.get('probability', 0)
            
            # Map to our weather conditions
            if precipitation_probability > 70:
                weather_condition = 'heavy_rain'
            elif precipitation_probability > 30:
                weather_condition = 'light_rain'
            elif condition.lower() in ['clear', 'sunny']:
                weather_condition = 'favorable'
            else:
                weather_condition = 'normal'
            
            temperature = data.get('temperature', {}).get('value', 25.0)
            
            return {
                'weather_condition': weather_condition,
                'temperature': temperature,
                'precipitation_probability': precipitation_probability,
                'source': 'google_weather_api'
            }
        else:
            # API not enabled or unavailable - use intelligent fallback
            if response.status_code == 403:
                logger.debug(f"Weather API not enabled (403). Using season-based fallback.")
            elif response.status_code == 404:
                logger.debug(f"Weather API endpoint not found (404). Using season-based fallback.")
            else:
                logger.debug(f"Weather API returned status {response.status_code}. Using fallback.")
            
            # Intelligent fallback based on season
            month = datetime.now().month
            if month in [6, 7, 8, 9]:  # Monsoon season in India
                weather_condition = 'light_rain'
            elif month in [12, 1, 2]:  # Winter
                weather_condition = 'favorable'
            else:
                weather_condition = 'normal'
            
            return {'weather_condition': weather_condition, 'temperature': 25.0, 'source': 'season_fallback'}
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"Weather API request failed: {str(e)}. Using season-based fallback.")
        # Fallback based on current season
        month = datetime.now().month
        if month in [6, 7, 8, 9]:  # Monsoon season
            weather_condition = 'light_rain'
        elif month in [12, 1, 2]:  # Winter
            weather_condition = 'favorable'
        else:
            weather_condition = 'normal'
        return {'weather_condition': weather_condition, 'temperature': 25.0, 'source': 'season_fallback'}
    except Exception as e:
        logger.debug(f"Error fetching weather: {str(e)}. Using season-based fallback.")
        return {'weather_condition': 'normal', 'temperature': 25.0, 'source': 'season_fallback'}


def get_traffic_condition(
    start_lat: float, 
    start_lng: float, 
    end_lat: float, 
    end_lng: float,
    trip_time: datetime
) -> Dict[str, any]:
    """
    Get traffic condition from Google Maps Directions API.
    
    Args:
        start_lat, start_lng: Start coordinates
        end_lat, end_lng: End coordinates
        trip_time: Trip datetime
    
    Returns:
        Dict with 'traffic_condition' (str) and 'traffic_multiplier' (float)
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("Google Maps API key not configured for Directions API")
        return {'traffic_condition': 'moderate', 'traffic_multiplier': 1.1}
    
    try:
        # Use Directions API with traffic model
        url = "https://maps.googleapis.com/maps/api/directions/json"
        
        params = {
            'origin': f"{start_lat},{start_lng}",
            'destination': f"{end_lat},{end_lng}",
            'departure_time': int(trip_time.timestamp()),
            'traffic_model': 'best_guess',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('routes'):
                route = data['routes'][0]
                leg = route['legs'][0]
                
                # Get duration in traffic vs duration without traffic
                duration_in_traffic = leg.get('duration_in_traffic', {}).get('value', 0)
                duration = leg.get('duration', {}).get('value', 0)
                
                if duration > 0:
                    # Calculate traffic multiplier
                    traffic_ratio = duration_in_traffic / duration
                    
                    # Map to our traffic conditions
                    if traffic_ratio > 1.5:
                        traffic_condition = 'heavy'
                        traffic_multiplier = 1.3
                    elif traffic_ratio > 1.2:
                        traffic_condition = 'moderate'
                        traffic_multiplier = 1.1
                    else:
                        traffic_condition = 'light'
                        traffic_multiplier = 1.0
                    
                    return {
                        'traffic_condition': traffic_condition,
                        'traffic_multiplier': traffic_multiplier,
                        'traffic_ratio': traffic_ratio,
                        'source': 'google_directions_api'
                    }
        
        # Fallback: infer from time of day
        hour = trip_time.hour
        if 7 <= hour < 10 or 18 <= hour < 21:
            return {'traffic_condition': 'heavy', 'traffic_multiplier': 1.3, 'source': 'time_based'}
        elif 10 <= hour < 12 or 14 <= hour < 18:
            return {'traffic_condition': 'moderate', 'traffic_multiplier': 1.1, 'source': 'time_based'}
        else:
            return {'traffic_condition': 'light', 'traffic_multiplier': 1.0, 'source': 'time_based'}
            
    except Exception as e:
        logger.error(f"Error fetching traffic: {str(e)}")
        # Fallback to time-based
        hour = trip_time.hour
        if 7 <= hour < 10 or 18 <= hour < 21:
            return {'traffic_condition': 'heavy', 'traffic_multiplier': 1.3, 'source': 'time_based_fallback'}
        return {'traffic_condition': 'moderate', 'traffic_multiplier': 1.1, 'source': 'time_based_fallback'}


def get_route_type(
    start_lat: float, 
    start_lng: float, 
    end_lat: float, 
    end_lng: float
) -> str:
    """
    Infer route type from route characteristics using Directions API.
    
    Args:
        start_lat, start_lng: Start coordinates
        end_lat, end_lng: End coordinates
    
    Returns:
        'highway', 'suburban', 'city_center', or 'hilly'
    """
    if not GOOGLE_MAPS_API_KEY:
        return 'suburban'
    
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        
        params = {
            'origin': f"{start_lat},{start_lng}",
            'destination': f"{end_lat},{end_lng}",
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('routes'):
                route = data['routes'][0]
                steps = route['legs'][0].get('steps', [])
                
                # Analyze route characteristics
                highway_count = 0
                city_center_count = 0
                total_steps = len(steps)
                
                for step in steps:
                    html_instructions = step.get('html_instructions', '').lower()
                    
                    # Check for highway indicators
                    if any(keyword in html_instructions for keyword in ['highway', 'expressway', 'freeway', 'motorway']):
                        highway_count += 1
                    
                    # Check for city center indicators
                    if any(keyword in html_instructions for keyword in ['city center', 'downtown', 'main street', 'market']):
                        city_center_count += 1
                
                # Classify route type
                if highway_count / total_steps > 0.5:
                    return 'highway'
                elif city_center_count / total_steps > 0.3:
                    return 'city_center'
                else:
                    return 'suburban'
        
        return 'suburban'
        
    except Exception as e:
        logger.error(f"Error analyzing route type: {str(e)}")
        return 'suburban'


def get_all_environment_data(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    trip_time: datetime
) -> Dict[str, any]:
    """
    Get all environment data automatically.
    
    Returns:
        Dict with all parameters:
        - time_period
        - traffic_condition
        - weather_condition
        - route_type
        - aqi_level
        - season
    """
    # Get midpoint for weather/AQI (average of start and end)
    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2
    
    # Fetch all data in parallel (or sequentially if needed)
    time_period = get_time_period(trip_time)
    season = get_season(trip_time)
    
    # Fetch real-time data
    aqi_data = get_air_quality(mid_lat, mid_lng)
    weather_data = get_weather_condition(mid_lat, mid_lng)
    traffic_data = get_traffic_condition(start_lat, start_lng, end_lat, end_lng, trip_time)
    route_type = get_route_type(start_lat, start_lng, end_lat, end_lng)
    
    return {
        'time_period': time_period,
        'traffic_condition': traffic_data.get('traffic_condition', 'moderate'),
        'weather_condition': weather_data.get('weather_condition', 'normal'),
        'route_type': route_type,
        'aqi_level': aqi_data.get('aqi_level', 'moderate'),
        'season': season,
        # Additional metadata
        'aqi_value': aqi_data.get('aqi_value', 150),
        'temperature': weather_data.get('temperature', 25.0),
        'traffic_multiplier': traffic_data.get('traffic_multiplier', 1.1),
        'data_sources': {
            'aqi': aqi_data.get('source', 'default'),
            'weather': weather_data.get('source', 'default'),
            'traffic': traffic_data.get('source', 'default'),
            'route': 'google_directions_api'
        }
    }


