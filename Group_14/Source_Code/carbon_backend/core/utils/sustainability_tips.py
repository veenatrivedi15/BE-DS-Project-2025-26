"""
Sustainability tips generator using OpenRouter API.
Analyzes user data and provides personalized sustainability tips.
"""
import requests
import json
import logging
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = getattr(settings, 'OPENROUTER_API_KEY', '')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def get_user_trip_analysis(user):
    """
    Analyze user's trip data to generate insights for sustainability tips.
    
    Returns a dictionary with analysis data.
    """
    from trips.models import Trip, CarbonCredit
    from django.db.models import Sum
    
    # Get user's trips from last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    if user.is_employee:
        trips = Trip.objects.filter(
            employee=user.employee_profile,
            created_at__gte=thirty_days_ago
        )
    else:
        # For employers, analyze their employees' trips
        trips = Trip.objects.filter(
            employee__employer=user.employer_profile,
            created_at__gte=thirty_days_ago
        )
    
    # Analyze transport modes
    transport_mode_counts = {}
    total_distance = 0
    total_co2_saved = 0
    car_trips = 0
    single_occupancy_trips = 0
    
    for trip in trips:
        mode = trip.transport_mode
        transport_mode_counts[mode] = transport_mode_counts.get(mode, 0) + 1
        
        if trip.distance_km:
            total_distance += float(trip.distance_km)
        
        # Check if it's a car trip
        if mode == 'car':
            car_trips += 1
            # Assume single occupancy if not specified
            if not hasattr(trip, 'passenger_count') or (hasattr(trip, 'passenger_count') and trip.passenger_count <= 1):
                single_occupancy_trips += 1
    
    # Get total credits earned
    if user.is_employee:
        credits = CarbonCredit.objects.filter(
            owner_type='employee',
            owner_id=user.employee_profile.id,
            status='active'
        ).aggregate(total=Sum('amount'))['total'] or 0
    else:
        credits = 0
    
    # Calculate daily average
    days_active = max(1, (timezone.now() - thirty_days_ago).days)
    daily_distance = total_distance / days_active if days_active > 0 else 0
    
    # Determine primary transport mode
    primary_mode = max(transport_mode_counts.items(), key=lambda x: x[1])[0] if transport_mode_counts else None
    
    return {
        'total_trips': trips.count(),
        'transport_mode_counts': transport_mode_counts,
        'primary_transport_mode': primary_mode,
        'total_distance_km': round(total_distance, 2),
        'daily_average_distance_km': round(daily_distance, 2),
        'car_trips': car_trips,
        'single_occupancy_trips': single_occupancy_trips,
        'total_credits': float(credits),
        'days_active': days_active,
        'has_car_usage': car_trips > 0,
        'has_single_occupancy': single_occupancy_trips > 0,
        'uses_sustainable_modes': any(mode in transport_mode_counts for mode in ['bicycle', 'walking', 'public_transport', 'carpool']),
    }

def generate_single_sustainability_tip(user):
    """
    Generate a single personalized sustainability tip using OpenRouter API.
    
    Args:
        user: The user object (Employee or Employer)
    
    Returns:
        Single personalized sustainability tip string
    """
    if not OPENROUTER_API_KEY:
        logger.warning("OpenRouter API key not configured. Returning default tips.")
        return get_default_tips()
    
    try:
        # Get user trip analysis
        analysis = get_user_trip_analysis(user)
        
        # Build prompt for AI
        prompt = f"""Analyze this user's transportation data and provide ONE highly personalized, actionable sustainability tip.

User Data:
- Total trips in last 30 days: {analysis['total_trips']}
- Primary transport mode: {analysis['primary_transport_mode'] or 'None'}
- Transport modes used: {', '.join(analysis['transport_mode_counts'].keys()) if analysis['transport_mode_counts'] else 'None'}
- Total distance: {analysis['total_distance_km']} km
- Daily average distance: {analysis['daily_average_distance_km']} km
- Car trips: {analysis['car_trips']}
- Single occupancy car trips: {analysis['single_occupancy_trips']}
- Total carbon credits earned: {analysis['total_credits']}

Key Observations:
- Uses car frequently: {analysis['has_car_usage']}
- Single occupancy trips: {analysis['has_single_occupancy']}
- Uses sustainable modes: {analysis['uses_sustainable_modes']}

Please provide:
1. ONE specific, actionable tip based on their actual usage patterns
2. Focus on their primary issue (e.g., if they use cars with single occupancy, suggest carpooling or public transport)
3. Make the tip encouraging and positive
4. Include specific suggestions (e.g., "Try carpooling 2 days a week" instead of generic advice)
5. Keep it concise (1-2 sentences maximum)
6. Return ONLY the tip text, no quotes, no JSON, just the tip itself

Example: "Based on your {analysis['car_trips']} car trips this month, try carpooling with colleagues 2-3 days a week to reduce your carbon footprint by up to 50%." """

        # Call OpenRouter API
        response = requests.post(
            url=OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "x-ai/grok-4.1-fast:free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
            }),
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Clean the response - remove quotes, JSON formatting, etc.
            tip = content.strip()
            # Remove surrounding quotes if present
            if tip.startswith('"') and tip.endswith('"'):
                tip = tip[1:-1]
            elif tip.startswith("'") and tip.endswith("'"):
                tip = tip[1:-1]
            # Remove markdown code blocks
            if '```' in tip:
                tip = tip.split('```')[1].split('```')[0].strip()
            # Remove JSON array brackets if present
            if tip.startswith('[') and tip.endswith(']'):
                try:
                    tip_list = json.loads(tip)
                    if isinstance(tip_list, list) and len(tip_list) > 0:
                        tip = tip_list[0]
                except:
                    pass
            
            if tip and len(tip) > 10:  # Ensure we have a meaningful tip
                return tip
        
        # Fallback to default tip
        logger.warning(f"OpenRouter API returned status {response.status_code}. Using default tip.")
        return get_default_single_tip(analysis)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API request failed: {str(e)}. Using default tip.")
        return get_default_single_tip(analysis)
    except Exception as e:
        logger.error(f"Error generating sustainability tip: {str(e)}. Using default tip.")
        return get_default_single_tip(analysis)

def get_default_single_tip(analysis=None):
    """
    Get a single default sustainability tip when API is unavailable.
    
    Args:
        analysis: Optional user analysis data
    
    Returns:
        Single default tip string
    """
    # Customize based on analysis if available
    if analysis:
        if analysis.get('has_single_occupancy') and analysis.get('car_trips', 0) > 5:
            return f"Based on your {analysis['car_trips']} car trips this month, try carpooling with colleagues 2-3 days a week to reduce your carbon footprint by up to 50%."
        
        if analysis.get('primary_transport_mode') == 'car':
            return "Your primary mode is car travel. Consider switching to public transport or cycling for some trips to earn more carbon credits and reduce emissions!"
        
        if analysis.get('uses_sustainable_modes'):
            return "Great job using sustainable transport modes! Try to increase the frequency to maximize your carbon credit earnings."
        
        if analysis.get('total_trips', 0) == 0:
            return "Start logging your sustainable commutes to earn carbon credits! Every trip counts towards a greener future."
    
    # Generic default tip
    return "Consider using public transportation or carpooling to reduce your carbon footprint and earn more carbon credits."

