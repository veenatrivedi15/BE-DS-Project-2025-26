from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from decimal import Decimal
import uuid
import os
import logging

from users.models import CustomUser, EmployeeProfile, Location
from trips.models import Trip, CarbonCredit
from django.conf import settings

logger = logging.getLogger(__name__)

# Constants for carbon credit calculations
CREDIT_RATES = {
    'car': Decimal('0.5'),  # 0.5 credits per km
    'carpool': Decimal('2.0'),  # 2 credits per km
    'public_transport': Decimal('3.0'),  # 3 credits per km
    'bicycle': Decimal('5.0'),  # 5 credits per km
    'walking': Decimal('6.0'),  # 6 credits per km
    'work_from_home': Decimal('10.0'),  # 10 credits flat
}

# CO2 savings in kg per km by mode
CO2_SAVINGS = {
    'car': Decimal('0.02'),  # Small savings for single occupancy car (more efficient driving)
    'carpool': Decimal('0.12'),  # Savings from multiple people sharing a ride
    'public_transport': Decimal('0.15'),  # Public transportation has lower emissions per passenger
    'bicycle': Decimal('0.20'),  # Cycling has almost no emissions
    'walking': Decimal('0.20'),  # Walking has no emissions
    'work_from_home': Decimal('0.50'),  # Significant savings from not commuting at all
}

# Average speeds in km/h for different transport modes
TRANSPORT_SPEEDS = {
    'car': 50,  # 50 km/h for car
    'carpool': 45,  # 45 km/h for carpool (accounting for pick-ups)
    'public_transport': 30,  # 30 km/h for public transport (including stops)
    'bicycle': 15,  # 15 km/h for bicycle
    'walking': 5,  # 5 km/h for walking
    'work_from_home': 0,  # No travel time for work from home
}

import requests

def get_location_name_from_coordinates(latitude, longitude):
    """
    Get a human-readable location name from coordinates using Google Maps Geocoding API.
    Falls back to a simple name if API fails.
    """
    try:
        from django.conf import settings
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        
        if not api_key:
            # Fallback to simple name
            return f"Location ({latitude:.4f}, {longitude:.4f})"
        
        # Use reverse geocoding to get location name
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{latitude},{longitude}",
            'key': api_key,
            'result_type': 'street_address|route|neighborhood|locality'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                # Get the first result's formatted address
                result = data['results'][0]
                formatted_address = result.get('formatted_address', '')
                
                # Extract a shorter name (first part before comma)
                if formatted_address:
                    name_parts = formatted_address.split(',')
                    if len(name_parts) > 0:
                        # Use first 2 parts for a concise name
                        location_name = ', '.join(name_parts[:2]).strip()
                        return location_name
                
                # Fallback to address components
                address_components = result.get('address_components', [])
                for component in address_components:
                    if 'route' in component.get('types', []):
                        route_name = component.get('long_name', '')
                        if route_name:
                            return route_name
                    elif 'neighborhood' in component.get('types', []):
                        neighborhood = component.get('long_name', '')
                        if neighborhood:
                            return neighborhood
        
        # Fallback to simple name
        return f"Location ({latitude:.4f}, {longitude:.4f})"
        
    except Exception as e:
        logger.debug(f"Error getting location name: {str(e)}")
        # Fallback to simple name
        return f"Location ({latitude:.4f}, {longitude:.4f})"

def get_distance(origin, destination):
    """Get distance between two locations using Google Maps API."""
    try:
        # Get API key from settings
        API_KEY = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        
        if not API_KEY:
            logger.warning("Google Maps API key not configured. Using Haversine distance.")
            # Fallback to Haversine distance calculation
            from core.utils.distance_calculator import haversine_distance
            if isinstance(origin, tuple) and isinstance(destination, tuple):
                return float(haversine_distance(origin, destination))
            else:
                # Convert to tuples if needed
                if isinstance(origin, tuple):
                    origin_tuple = origin
                else:
                    origin_tuple = (float(origin.split(',')[0]), float(origin.split(',')[1]))
                if isinstance(destination, tuple):
                    dest_tuple = destination
                else:
                    dest_tuple = (float(destination.split(',')[0]), float(destination.split(',')[1]))
                return float(haversine_distance(origin_tuple, dest_tuple))
        
        # Format coordinates
        if isinstance(origin, tuple):
            origin_str = f"{origin[0]},{origin[1]}"
        else:
            origin_str = str(origin)
            
        if isinstance(destination, tuple):
            destination_str = f"{destination[0]},{destination[1]}"
        else:
            destination_str = str(destination)
        
        url = f"https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': origin_str,
            'destination': destination_str,
            'key': API_KEY
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('status') == 'OK' and data.get('routes'):
            # Extract the numeric distance value in meters
            distance_meters = data['routes'][0]['legs'][0]['distance']['value']
            # Convert to kilometers and round to 2 decimal places
            distance_km = round(distance_meters / 1000, 2)
            logger.debug(f"Distance calculated: {distance_km} km")
            return distance_km
        else:
            logger.warning(f"Directions API error: {data.get('status')}. Using Haversine fallback.")
            # Fallback to Haversine distance calculation
            from core.utils.distance_calculator import haversine_distance
            if isinstance(origin, tuple) and isinstance(destination, tuple):
                return float(haversine_distance(origin, destination))
            else:
                # Convert to tuples if needed
                if isinstance(origin, tuple):
                    origin_tuple = origin
                else:
                    origin_tuple = (float(origin.split(',')[0]), float(origin.split(',')[1]))
                if isinstance(destination, tuple):
                    dest_tuple = destination
                else:
                    dest_tuple = (float(destination.split(',')[0]), float(destination.split(',')[1]))
                return float(haversine_distance(origin_tuple, dest_tuple))
    except requests.exceptions.RequestException as e:
        logger.warning(f"Directions API request failed: {str(e)}. Using Haversine fallback.")
        # Fallback to Haversine distance calculation
        from core.utils.distance_calculator import haversine_distance
        return haversine_distance(origin, destination)
    except Exception as e:
        logger.error(f"Exception in get_distance: {str(e)}")
        # Fallback to Haversine distance calculation
        from core.utils.distance_calculator import haversine_distance
        return haversine_distance(origin, destination)

@login_required
@user_passes_test(lambda u: u.is_employee)
def create_trip(request):
    """Create a new trip for an employee."""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('employee_trip_log')
    
    try:
        # Get form data
        start_location_id = request.POST.get('start_location')
        end_location_id = request.POST.get('end_location')
        transport_mode = request.POST.get('transport_mode')
        trip_date_str = request.POST.get('trip_date')
        
        # Validate required fields
        if not all([start_location_id, end_location_id, transport_mode, trip_date_str]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('employee_trip_log')
        
        # Get employee profile
        employee = request.user.employee_profile
        
        # Handle custom locations (marked as 'other' in dropdown)
        start_location = None
        end_location = None
        distance_km = None
        
        # Process start location
        if start_location_id == 'home':
            # Use employee's home location
            start_location = Location.objects.filter(
                created_by=request.user,
                location_type='home'
            ).first()
            
            if not start_location:
                messages.error(request, "Home location not found. Please set your home location first.")
                return redirect('employee_trip_log')
        elif start_location_id == 'other':
            # Create a custom location for this trip
            lat = request.POST.get('custom_latitude')
            lng = request.POST.get('custom_longitude')
            address = request.POST.get('custom_address', 'Custom location')
            
            if not lat or not lng:
                messages.error(request, "Custom location coordinates are required.")
                return redirect('employee_trip_log')
            
            # Get proper location name using reverse geocoding
            location_name = get_location_name_from_coordinates(float(lat), float(lng))
            
            # Create a temporary location (not saved to database)
            start_location = Location(
                name=location_name,
                latitude=Decimal(lat),
                longitude=Decimal(lng),
                address=address,
                location_type='custom',
                created_by=request.user
            )
            start_location.save()
        else:
            # Use an existing location from database
            try:
                start_location = Location.objects.get(id=start_location_id)
            except Location.DoesNotExist:
                messages.error(request, "Selected start location does not exist.")
                return redirect('employee_trip_log')
        
        # Process end location
        if end_location_id == 'home':
            # Use employee's home location
            end_location = Location.objects.filter(
                created_by=request.user,
                location_type='home'
            ).first()
            
            if not end_location:
                messages.error(request, "Home location not found. Please set your home location first.")
                return redirect('employee_trip_log')
        elif end_location_id == 'other':
            # Create a custom location for this trip
            lat = request.POST.get('custom_latitude')
            lng = request.POST.get('custom_longitude')
            address = request.POST.get('custom_address', 'Custom location')
            
            if not lat or not lng:
                messages.error(request, "Custom location coordinates are required.")
                return redirect('employee_trip_log')
            
            # Get proper location name using reverse geocoding
            location_name = get_location_name_from_coordinates(float(lat), float(lng))
            
            # Create a temporary location (not saved to database)
            end_location = Location(
                name=location_name,
                latitude=Decimal(lat),
                longitude=Decimal(lng),
                address=address,
                location_type='custom',
                created_by=request.user
            )
            end_location.save()
        else:
            # Use an existing location from database
            try:
                end_location = Location.objects.get(id=end_location_id)
            except Location.DoesNotExist:
                messages.error(request, "Selected end location does not exist.")
                return redirect('employee_trip_log')
        
        # For work from home, set distance to 0 immediately
        if transport_mode == 'work_from_home':
            distance_km = 0
        else:
            # Get distance from form or calculate
            distance_km = request.POST.get('distance_km')
            
            # If distance not provided or is 0, calculate it
            if not distance_km or distance_km == '0' or distance_km == '':
                try:
                    calculated_distance = get_distance(
                        (start_location.latitude, start_location.longitude),
                        (end_location.latitude, end_location.longitude),
                    )
                    distance_km = calculated_distance
                    logger.info(f"Calculated distance: {distance_km} km")
                except Exception as e:
                    logger.error(f"Error calculating distance: {str(e)}")
                    messages.error(request, "Could not calculate route. Please try different locations or ensure both locations are selected on the map.")
                    return redirect('employee_trip_log')
            
            # Convert to float for processing
            try:
                distance_km = float(distance_km)
                if distance_km <= 0:
                    messages.error(request, "Trip distance must be greater than 0.")
                    return redirect('employee_trip_log')
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid distance value: {distance_km}, error: {str(e)}")
                messages.error(request, "Invalid distance value. Please ensure the route is calculated correctly.")
                return redirect('employee_trip_log')
        
        # Create the trip with start time only (this means trip is in progress)
        distance_decimal = Decimal(distance_km) if distance_km else Decimal('0')
        
        # Parse trip date
        trip_date = datetime.strptime(trip_date_str, "%Y-%m-%d").date()
        
        # Set trip time to current time, but with the selected date
        trip_start = timezone.now().replace(
            year=trip_date.year,
            month=trip_date.month,
            day=trip_date.day
        )
        
        # For completed trips, set end time 30 minutes later
        trip_end = trip_start + timezone.timedelta(minutes=30)
        
        # Create the trip
        trip = Trip(
            employee=employee,
            start_location=start_location,
            end_location=end_location,
            start_time=trip_start,
            end_time=trip_end,
            transport_mode=transport_mode,
            distance_km=distance_decimal,
            # status='completed'
        )
        
        # Use new calculation engine (WRI 2015 + IPCC 2006)
        from core.calculations import (
            calculate_carbon_credits,
            calculate_time_weight,
            calculate_context_factor,
            get_recency_days
        )
        from core.emission_factors import get_baseline_ef, get_actual_ef
        from core.ml_predictor import predict_carbon_credits_ml
        
        # Get emission factors
        ef_baseline = get_baseline_ef(transport_mode)
        ef_actual = get_actual_ef(transport_mode)
        emission_difference = ef_baseline - ef_actual
        
        # Automatically detect environment data if coordinates are available
        auto_detect = request.POST.get('auto_detect_environment', 'true') == 'true'
        
        # Get location coordinates
        start_lat = float(start_location.latitude) if start_location else None
        start_lng = float(start_location.longitude) if start_location else None
        end_lat = float(end_location.latitude) if end_location else None
        end_lng = float(end_location.longitude) if end_location else None
        
        # Try custom coordinates if available
        custom_lat = request.POST.get('custom_latitude')
        custom_lng = request.POST.get('custom_longitude')
        if custom_lat and custom_lng:
            if not start_lat:
                start_lat = float(custom_lat)
                start_lng = float(custom_lng)
            elif not end_lat:
                end_lat = float(custom_lat)
                end_lng = float(custom_lng)
        
        # Auto-detect all parameters if coordinates available
        if auto_detect and start_lat and start_lng and end_lat and end_lng:
            try:
                from core.utils.environment_data import get_all_environment_data
                
                env_data = get_all_environment_data(
                    start_lat, start_lng, end_lat, end_lng, trip_start
                )
                
                # Use auto-detected values, but allow manual override from POST
                time_period = request.POST.get('time_period') or env_data['time_period']
                traffic_condition = request.POST.get('traffic_condition') or env_data['traffic_condition']
                weather_condition = request.POST.get('weather_condition') or env_data['weather_condition']
                route_type = request.POST.get('route_type') or env_data['route_type']
                aqi_level = request.POST.get('aqi_level') or env_data['aqi_level']
                season = request.POST.get('season') or env_data['season']
                
                logger.info(f"Auto-detected environment data: {env_data.get('data_sources', {})}")
                
            except Exception as e:
                logger.error(f"Error auto-detecting environment data: {str(e)}")
                auto_detect = False
        
        # Fallback to manual/default values
        if not auto_detect or not (start_lat and start_lng and end_lat and end_lng):
            # Determine time period from trip time
            hour = trip_start.hour
            if 7 <= hour < 10:
                time_period = request.POST.get('time_period', 'peak_morning')
            elif 18 <= hour < 21:
                time_period = request.POST.get('time_period', 'peak_evening')
            elif 23 <= hour or hour < 5:
                time_period = request.POST.get('time_period', 'late_night')
            else:
                time_period = request.POST.get('time_period', 'off_peak')
            
            # Get season from date
            from core.utils.environment_data import get_season
            season = request.POST.get('season') or get_season(trip_start)
            
            # Default values (manual input or defaults)
            traffic_condition = request.POST.get('traffic_condition', 'moderate')
            weather_condition = request.POST.get('weather_condition', 'normal')
            route_type = request.POST.get('route_type', 'suburban')
            aqi_level = request.POST.get('aqi_level', 'moderate')
        
        # Calculate time weight
        recency_days = get_recency_days(trip_start)
        time_weight = calculate_time_weight(time_period, traffic_condition, recency_days)
        
        occupancy = request.POST.get('occupancy')
        load_factor = 1.0
        if transport_mode == 'two_wheeler_single':
            load_factor = 0.95
        elif transport_mode == 'two_wheeler_double':
            if occupancy and str(occupancy) != '2':
                messages.error(request, "Two Wheeler (Carpool) requires 2 passengers.")
                return redirect('employee_trip_log')
            load_factor = 1.02

        # Calculate context factor
        context_factor = calculate_context_factor(
            weather_condition, route_type, aqi_level,
            load_factor=load_factor, season=season
        )
        
        # Try ML prediction first, fallback to formula
        ml_result = predict_carbon_credits_ml(
            transport_mode=transport_mode,
            distance_km=float(distance_decimal),
            trip_duration_minutes=None,
            average_speed_kmph=None,
            time_period=time_period,
            traffic_condition=traffic_condition,
            weather_condition=weather_condition,
            route_type=route_type,
            aqi_level=aqi_level,
            season=season
        )
        
        if ml_result['prediction'] is not None and ml_result['method'] == 'ml':
            # Use ML prediction
            carbon_credits_earned = ml_result['prediction']
            calculation_method = 'ml'
            ml_confidence = ml_result.get('confidence', 0.0)
        else:
            # Use formula-based calculation
            carbon_credits_earned = calculate_carbon_credits(
                ef_baseline, ef_actual, float(distance_decimal),
                time_weight, context_factor
            )
            calculation_method = 'formula'
            ml_confidence = None
        
        # Calculate carbon savings (emission difference * distance)
        carbon_savings = emission_difference * float(distance_decimal) if distance_decimal > 0 else 0
        
        # Save all calculation data
        trip.ef_baseline = ef_baseline
        trip.ef_actual = ef_actual
        trip.emission_difference = emission_difference
        trip.time_period = time_period
        trip.traffic_condition = traffic_condition
        trip.weather_condition = weather_condition
        trip.route_type = route_type
        trip.aqi_level = aqi_level
        trip.season = season
        trip.time_weight = time_weight
        trip.context_factor = context_factor
        trip.carbon_credits_earned = carbon_credits_earned
        trip.calculation_method = calculation_method
        trip.ml_prediction_confidence = ml_confidence
        
        # Save carbon savings and credits as Decimal
        trip.carbon_savings = Decimal(str(carbon_savings))
        trip.credits_earned = Decimal(str(carbon_credits_earned))
        
        # Handle trip proof
        proof_image = request.FILES.get('proof_image')
        proof_data = request.POST.get('proof_image')
        proof_file_path = request.POST.get('proof_file_path')
        
        if proof_image:
            # Handle traditional file upload
            # Generate a unique filename
            filename = f"{uuid.uuid4()}.{proof_image.name.split('.')[-1]}"
            
            # Save the proof image
            trip.proof_image = proof_image
            trip.verification_status = 'pending'
        elif proof_data and proof_data.startswith('data:'):
            # Handle base64 data from the enhanced file upload component
            import base64
            from django.core.files.base import ContentFile
            
            # Extract the data type and base64 content
            format, imgstr = proof_data.split(';base64,')
            ext = format.split('/')[-1]
            
            # Use the provided path or generate a unique filename
            if proof_file_path:
                filename = os.path.basename(proof_file_path)
            else:
                filename = f"{uuid.uuid4()}.{ext}"
            
            # Convert base64 to file and save
            data = ContentFile(base64.b64decode(imgstr), name=filename)
            trip.proof_image = data
            trip.verification_status = 'pending'
            
            # Log the file path for debugging
            print(f"Saved proof image to: {trip.proof_image.path}")
        else:
            # All trips require employer approval
            trip.verification_status = 'pending'
        
        # Save the trip
        trip.save()
        
        # Create carbon credits
        if trip.verification_status == 'verified':
            # Create active credits for verified trips
            CarbonCredit.objects.create(
                amount=trip.credits_earned,
                source_trip=trip,
                owner_type='employee',
                owner_id=employee.id,
                status='active',
                expiry_date=timezone.now() + timezone.timedelta(days=365)
            )
        else:
            # Create pending credits for trips needing verification
            CarbonCredit.objects.create(
                amount=trip.credits_earned,
                source_trip=trip,
                owner_type='employee',
                owner_id=employee.id,
                status='pending',
                expiry_date=timezone.now() + timezone.timedelta(days=365)
            )
        
        messages.success(
            request, 
            f"Trip logged successfully! You've earned {trip.credits_earned} carbon credits."
        )
        return redirect('employee_dashboard')
        
    except Exception as e:
        messages.error(request, f"Error creating trip: {str(e)}")
        return redirect('employee_trip_log')

# For GET requests, redirect to the trip_log page
# return redirect('employee_trip_log') 