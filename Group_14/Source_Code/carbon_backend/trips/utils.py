"""Utility functions for the trips app."""

import math
import googlemaps
from datetime import datetime
from django.conf import settings

def calculate_distance_haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    using the Haversine formula.
    
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def calculate_distance_google_maps(origin_lat, origin_lon, dest_lat, dest_lon, mode='driving'):
    """
    Calculate distance between two points using Google Maps API.
    
    Args:
        origin_lat (float): Latitude of origin point
        origin_lon (float): Longitude of origin point
        dest_lat (float): Latitude of destination point
        dest_lon (float): Longitude of destination point
        mode (str): Mode of transport (driving, walking, bicycling, transit)
        
    Returns:
        float: Distance in kilometers
    """
    try:
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        
        # Convert transport mode to Google Maps format
        google_mode = mode
        if mode not in ['driving', 'walking', 'bicycling', 'transit']:
            # Default to driving for modes not supported by Google Maps
            if mode == 'car' or mode == 'carpool':
                google_mode = 'driving'
            elif mode == 'bicycle':
                google_mode = 'bicycling'
            elif mode == 'walking':
                google_mode = 'walking'
            elif mode == 'public_transport':
                google_mode = 'transit'
            else:
                google_mode = 'driving'
        
        directions_result = gmaps.directions(
            (origin_lat, origin_lon),
            (dest_lat, dest_lon),
            mode=google_mode,
            departure_time=datetime.now()
        )
        
        if directions_result:
            # Get distance in meters and convert to kilometers
            distance_meters = directions_result[0]['legs'][0]['distance']['value']
            return round(distance_meters / 1000, 2)
        
        # If Google Maps API fails, fall back to Haversine formula
        return calculate_distance_haversine(origin_lat, origin_lon, dest_lat, dest_lon)
    
    except Exception as e:
        # If Google Maps API fails, fall back to Haversine formula
        return calculate_distance_haversine(origin_lat, origin_lon, dest_lat, dest_lon)

def calculate_carbon_savings(distance_km, transport_mode):
    """
    Calculate the carbon savings for a trip based on transport mode and distance.
    
    Args:
        distance_km (float): Distance in kilometers
        transport_mode (str): Mode of transport
        
    Returns:
        tuple: (carbon_saved, credits_earned) in kg of CO2
    """
    # Define carbon emission factors for different transport modes (kg CO2 per km)
    carbon_factors = {
        'car': 0.12,               # kg CO2 per km (baseline)
        'carpool': 0.07,           # kg CO2 per km (assumes ~2 people)
        'two_wheeler_single': 0.029,  # kg CO2 per km (solo)
        'two_wheeler_double': 0.0145, # kg CO2 per km per person (2 riders)
        'public_transport': 0.03,  # kg CO2 per km (average for buses/trains)
        'bicycle': 0,              # No emissions
        'walking': 0,              # No emissions
        'work_from_home': 0,       # No emissions for commuting
    }
    
    # Calculate carbon saved compared to car travel (baseline)
    baseline_emissions = distance_km * carbon_factors['car']
    actual_emissions = distance_km * carbon_factors.get(transport_mode, 0)
    carbon_saved = baseline_emissions - actual_emissions
    
    # Calculate credits (1 credit per kg CO2 saved)
    credits = carbon_saved
    
    return carbon_saved, credits 