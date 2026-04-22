"""
Utilities for calculating distances between geographic coordinates.
Primary: Google Maps API
Fallback: Haversine formula
"""

import os
import math
import logging
import requests
from decimal import Decimal
from django.conf import settings
from core.models import SystemConfig

logger = logging.getLogger(__name__)

def calculate_distance(start_coords, end_coords):
    """
    Calculate distance between two geographical points.
    Primary: Google Maps API
    Fallback: Haversine formula
    
    Args:
        start_coords: Tuple (latitude, longitude) for starting point
        end_coords: Tuple (latitude, longitude) for ending point
        
    Returns:
        Distance in kilometers (decimal)
    """
    # First try using Google Maps API if key is available
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY
    
    if google_maps_api_key:
        try:
            return google_maps_distance_api(start_coords, end_coords, google_maps_api_key)
        except Exception as e:
            logger.warning(f"Google Maps API failed: {str(e)}. Falling back to Haversine.")
    
    # Fallback to Haversine formula
    return haversine_distance(start_coords, end_coords)


def google_maps_distance_api(start_coords, end_coords, api_key):
    """
    Calculate distance using Google Maps Distance Matrix API.
    
    Args:
        start_coords: Tuple (latitude, longitude) for starting point
        end_coords: Tuple (latitude, longitude) for ending point
        api_key: Google Maps API key
        
    Returns:
        Distance in kilometers (decimal)
    """
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    
    # Format coordinates for the API
    origins = f"{start_coords[0]},{start_coords[1]}"
    destinations = f"{end_coords[0]},{end_coords[1]}"
    
    params = {
        "origins": origins,
        "destinations": destinations,
        "mode": "driving",  # Default to driving mode
        "key": api_key
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if data["status"] != "OK":
        raise Exception(f"Google Maps API error: {data['status']}")
    
    # Extract distance in meters and convert to kilometers
    distance_meters = data["rows"][0]["elements"][0]["distance"]["value"]
    distance_km = Decimal(distance_meters) / 1000
    
    return distance_km


def haversine_distance(start_coords, end_coords):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    
    Args:
        start_coords: Tuple (latitude, longitude) for starting point
        end_coords: Tuple (latitude, longitude) for ending point
        
    Returns:
        Distance in kilometers (decimal)
    """
    # Convert decimal degrees to radians
    lat1, lon1 = float(start_coords[0]), float(start_coords[1])
    lat2, lon2 = float(end_coords[0]), float(end_coords[1])
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return Decimal(c * r) 