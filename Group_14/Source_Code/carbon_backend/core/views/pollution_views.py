"""
Views for pollution awareness and location-based features
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Max, Sum, Q
from django.conf import settings
from decimal import Decimal
import json

from core.pollution_service import (
    PollutionDataService, IndustrialZoneService, 
    PollutionImpactCalculator, PollutionAlertService
)
from core.pollution_models import (
    IndustrialZone, PollutionData, UserPollutionAlert, 
    PollutionImpact
)
from users.models import Location
from trips.models import Trip, CarbonCredit


from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import requests

@login_required
def pollution_dashboard(request):
    """
    Main pollution awareness dashboard for users
    """
    user = request.user
    
    # Get Google Maps API key
    from django.conf import settings
    google_maps_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    # Get user's recent locations
    recent_locations_qs = Location.objects.filter(
        Q(created_by=user) | 
        Q(employer=user.employee_profile.employer if hasattr(user, 'employee_profile') and user.employee_profile else None)
    ).order_by('-created_at')[:5]
    recent_locations = list(recent_locations_qs.values(
        'id', 'name', 'latitude', 'longitude', 'address', 'location_type'
    ))
    
    # Get pollution alerts
    unread_alerts = list(UserPollutionAlert.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:5].values(
        'id', 'title', 'message', 'severity', 'created_at'
    ))
    
    # Get nearby industrial zones
    from core.pollution_models import IndustrialZone
    zones = IndustrialZone.objects.filter(is_active=True)[:10]
    nearby_zones = []
    for zone in zones:
        nearby_zones.append({
            'id': zone.id,
            'name': zone.name,
            'latitude': float(zone.latitude),
            'longitude': float(zone.longitude),
            'zone_type': zone.zone_type,
            'emission_intensity': float(zone.emission_intensity)
        })

    # Recent AQI records for user's locations
    recent_aqi_records = []
    if recent_locations_qs.exists():
        latest_aqi = (
            PollutionData.objects
            .select_related('location')
            .filter(location__in=recent_locations_qs, pollutant_type='aqi')
            .order_by('-timestamp')
        )
        seen_locations = set()
        for record in latest_aqi:
            if record.location_id in seen_locations:
                continue
            seen_locations.add(record.location_id)
            recent_aqi_records.append(record)
            if len(recent_aqi_records) >= 5:
                break

    # Recent pollution data records
    recent_pollution_records = list(
        PollutionData.objects
        .select_related('location')
        .filter(location__in=recent_locations_qs)
        .order_by('-timestamp')[:10]
    )
    
    # Get recent pollution impacts
    recent_impacts = list(PollutionImpact.objects.filter(
        user=user
    ).order_by('-calculation_date')[:10].values(
        'id', 'carbon_savings_kg', 'equivalent_factory_hours',
        'trees_planted_equivalent', 'calculation_date'
    ))
    
    context = {
        'recent_locations': recent_locations,
        'recent_locations_qs': recent_locations_qs,
        'recent_aqi_records': recent_aqi_records,
        'recent_pollution_records': recent_pollution_records,
        'unread_alerts': unread_alerts,
        'nearby_zones': nearby_zones,
        'recent_impacts': recent_impacts,
        'page_title': 'Pollution Awareness Dashboard',
        'google_maps_api_key': google_maps_api_key
    }
    
    return render(request, 'pollution/dashboard.html', context)


@login_required
def location_pollution_analysis(request, location_id):
    """
    Detailed pollution analysis for a specific location
    """
    user = request.user
    location = get_object_or_404(Location, id=location_id)
    
    # Check if user has access to this location
    if user.is_employee and location.created_by != user:
        messages.error(request, "You don't have access to this location.")
        return redirect('pollution_dashboard')
    elif user.is_employer and location.employer != user.employer_profile:
        messages.error(request, "You don't have access to this location.")
        return redirect('pollution_dashboard')
    
    # Get industrial zones nearby
    nearby_zones = IndustrialZoneService.find_nearby_industrial_zones(location, radius_km=15.0)
    active_zones = IndustrialZoneService.get_active_industrial_zones(location, radius_km=15.0)
    industrial_impact = IndustrialZoneService.calculate_industrial_impact(location)
    
    # Get pollution data
    pollution_service = PollutionDataService()
    pollution_data = pollution_service.get_pollution_data_by_coordinates(
        float(location.latitude), 
        float(location.longitude)
    )
    
    if pollution_data:
        stored_data = pollution_service.store_pollution_data(location, pollution_data)
    else:
        stored_data = PollutionData.objects.filter(
            location=location
        ).order_by('-timestamp')[:10]
    
    # Calculate user's carbon impact for this location
    if user.is_employee:
        user_trips = Trip.objects.filter(
            employee=user.employee_profile,
            start_location=location
        ) | Trip.objects.filter(
            employee=user.employee_profile,
            end_location=location
        )
        
        total_carbon_saved = sum(
            float(trip.carbon_savings or 0) for trip in user_trips
            if trip.carbon_savings
        )
        
        if total_carbon_saved > 0:
            equivalents = PollutionImpactCalculator.calculate_carbon_impact_equivalents(total_carbon_saved)
            emotional_message = PollutionImpactCalculator.generate_emotional_message(total_carbon_saved, equivalents)
            
            # Store the impact
            PollutionImpactCalculator.store_pollution_impact(user, location, total_carbon_saved)
        else:
            equivalents = {}
            emotional_message = "Start logging sustainable trips to see your environmental impact!"
    else:
        total_carbon_saved = 0
        equivalents = {}
        emotional_message = "Employee data will be shown here."
    
    context = {
        'location': location,
        'nearby_zones': nearby_zones,
        'active_zones': active_zones,
        'industrial_impact': industrial_impact,
        'pollution_data': stored_data,
        'total_carbon_saved': total_carbon_saved,
        'equivalents': equivalents,
        'emotional_message': emotional_message,
        'page_title': f'Pollution Analysis - {location.name or location.address[:30]}'
    }
    
    return render(request, 'pollution/location_analysis.html', context)


@login_required
def get_real_time_pollution(request):
    """
    API endpoint to get real-time pollution data for a location
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    try:
        data = json.loads(request.body)
        lat = float(data.get('latitude'))
        lng = float(data.get('longitude'))
        
        pollution_service = PollutionDataService()
        pollution_data = pollution_service.get_pollution_data_by_coordinates(lat, lng)
        
        if pollution_data:
            return JsonResponse({
                'success': True,
                'data': pollution_data,
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Unable to fetch pollution data'
            })
    
    except (ValueError, KeyError) as e:
        return JsonResponse({'error': 'Invalid data format'}, status=400)


@login_required
def check_pollution_alerts(request):
    """
    Check and create pollution alerts for user's current location
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        # Get or create location
        location, created = Location.objects.get_or_create(
            latitude=Decimal(str(data.get('latitude'))),
            longitude=Decimal(str(data.get('longitude'))),
            defaults={
                'address': data.get('address', 'Current Location'),
                'created_by': request.user,
                'location_type': 'other'
            }
        )
        
        # Check and create alerts
        PollutionAlertService.check_and_create_alerts(request.user, location)
        
        # Get unread alerts
        new_alerts = UserPollutionAlert.objects.filter(
            user=request.user,
            is_read=False,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        
        return JsonResponse({
            'success': True,
            'new_alerts': new_alerts,
            'message': f'Checked for pollution alerts. {new_alerts} new alerts found.'
        })
    
    except (ValueError, KeyError) as e:
        return JsonResponse({'error': 'Invalid data format'}, status=400)


@login_required
def mark_alert_read(request, alert_id):
    """
    Mark a pollution alert as read
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    try:
        alert = get_object_or_404(UserPollutionAlert, id=alert_id, user=request.user)
        alert.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'message': 'Alert marked as read'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def industrial_zones_map(request):
    """
    Map view showing all industrial zones
    """
    zones = IndustrialZone.objects.filter(is_active=True)

    def _get_zone_risk_level(zone):
        intensity = float(zone.emission_intensity)
        if intensity < 100:
            return 'Low'
        if intensity < 500:
            return 'Medium'
        if intensity < 1000:
            return 'High'
        return 'Critical'
    
    # Group zones by type
    zones_by_type = {}
    for zone in zones:
        zone_type = zone.get_zone_type_display()
        if zone_type not in zones_by_type:
            zones_by_type[zone_type] = []
        zones_by_type[zone_type].append(zone)
    
    # Calculate statistics
    total_zones = zones.count()
    safe_zones = sum(1 for zone in zones if _get_zone_risk_level(zone) == 'Low')
    warning_zones = sum(1 for zone in zones if _get_zone_risk_level(zone) == 'Medium')
    high_risk_zones = sum(1 for zone in zones if _get_zone_risk_level(zone) in ['High', 'Critical'])
    
    context = {
        'industrial_zones': zones,
        'zones_by_type': zones_by_type,
        'total_zones': total_zones,
        'safe_zones': safe_zones,
        'warning_zones': warning_zones,
        'high_risk_zones': high_risk_zones,
        'page_title': 'Industrial Zones Map'
    }
    
    return render(request, 'pollution/industrial_zones_map.html', context)


@login_required
def pollution_impact_history(request):
    """
    Show user's pollution impact history
    """
    user = request.user
    
    # Get user's pollution impacts
    impacts = PollutionImpact.objects.filter(user=user).order_by('-calculation_date')
    
    # Calculate totals
    total_carbon_saved = sum(float(impact.carbon_savings_kg) for impact in impacts)
    total_factory_hours = sum(float(impact.equivalent_factory_hours) for impact in impacts)
    total_trees_planted = sum(impact.trees_planted_equivalent for impact in impacts)
    
    # Calculate additional metrics
    total_sustainable_trips = impacts.count()
    total_factory_hours_offset = int(total_factory_hours)
    impact_score = int(total_carbon_saved * 10)  # Simple scoring system
    
    # Monthly aggregation
    monthly_data = {}
    for impact in impacts:
        month_key = impact.calculation_date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'carbon_saved': 0,
                'factory_hours': 0,
                'trees_planted': 0,
                'count': 0
            }
        
        monthly_data[month_key]['carbon_saved'] += float(impact.carbon_savings_kg)
        monthly_data[month_key]['factory_hours'] += float(impact.equivalent_factory_hours)
        monthly_data[month_key]['trees_planted'] += impact.trees_planted_equivalent
        monthly_data[month_key]['count'] += 1
    
    context = {
        'impact_history': impacts,
        'total_carbon_saved': total_carbon_saved,
        'total_factory_hours': total_factory_hours,
        'total_trees_planted': total_trees_planted,
        'total_sustainable_trips': total_sustainable_trips,
        'total_factory_hours_offset': total_factory_hours_offset,
        'impact_score': impact_score,
        'monthly_data': monthly_data,
        'page_title': 'Your Environmental Impact History'
    }
    
    return render(request, 'pollution/impact_history.html', context)

@csrf_exempt
@require_http_methods(["GET"])
def get_pollution_zones(request):
    """
    API endpoint to get pollution zones data for map
    """
    try:
        zones = IndustrialZone.objects.all().values(
            'id', 'name', 'latitude', 'longitude', 
            'radius_km', 'zone_type', 'emission_intensity'
        )
        
        zone_list = []
        for zone in zones:
            # Determine color based on emission intensity
            intensity = float(zone.get('emission_intensity', 50))
            if intensity < 50:
                color = '#10b981'  # Low pollution
                pollution_level = 'low'
            elif intensity < 100:
                color = '#f59e0b'  # Moderate pollution
                pollution_level = 'moderate'
            elif intensity < 200:
                color = '#ef4444'  # High pollution
                pollution_level = 'high'
            else:
                color = '#991b1b'  # Very high pollution
                pollution_level = 'very_high'
            
            zone_list.append({
                'id': zone['id'],
                'name': zone['name'],
                'latitude': float(zone['latitude']),
                'longitude': float(zone['longitude']),
                'radius': float(zone.get('radius_km', 5.0)) * 1000,  # Convert km to meters
                'color': color,
                'pollution_level': pollution_level,
                'zone_type': zone['zone_type']
            })
        
        return JsonResponse({
            'success': True,
            'zones': zone_list
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
