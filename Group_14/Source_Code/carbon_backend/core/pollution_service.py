"""
Pollution Data Service and Location Awareness Utilities
"""
import requests
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Max, Min
from geopy.distance import geodesic
from .pollution_models import (
    IndustrialZone, PollutionData, UserPollutionAlert, 
    PollutionImpact, EnvironmentalMetric
)
from users.models import Location

logger = logging.getLogger(__name__)

# OpenWeatherMap Air Pollution API (free tier)
OPENWEATHER_API_KEY = getattr(settings, 'OPENWEATHER_API_KEY', '')
OPENWEATHER_POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

# Environmental conversion factors (IPCC 2006 standards)
ENVIRONMENTAL_CONVERSIONS = {
    'tree_absorption_per_year': 21.77,  # kg CO2 per tree per year
    'car_emission_per_day': 4.6,        # kg CO2 per car per day (average)
    'factory_emission_per_hour': 1000,  # kg CO2 per hour (medium factory)
    'motorbike_emission_per_day': 2.3,  # kg CO2 per motorbike per day
}


class PollutionDataService:
    """Service for handling pollution data and location awareness."""
    
    def __init__(self):
        self.api_key = OPENWEATHER_API_KEY
        self.base_url = OPENWEATHER_POLLUTION_URL
    
    def get_pollution_data_by_coordinates(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Fetch real-time pollution data from OpenWeatherMap API.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            Pollution data dictionary or None if failed
        """
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
        
        try:
            params = {
                'lat': lat,
                'lon': lng,
                'appid': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._process_pollution_response(data)
            else:
                logger.error(f"OpenWeatherMap API error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Pollution API request failed: {str(e)}")
            return None
    
    def _process_pollution_response(self, data: Dict) -> Dict:
        """Process API response and extract relevant pollution data."""
        if 'list' not in data or not data['list']:
            return {}
        
        current = data['list'][0]
        components = current.get('components', {})
        main = current.get('main', {})
        
        processed_data = {
            'aqi': main.get('aqi', 1),
            'pm25': components.get('pm2_5', 0),
            'pm10': components.get('pm10', 0),
            'co': components.get('co', 0),
            'no': components.get('no', 0),
            'no2': components.get('no2', 0),
            'o3': components.get('o3', 0),
            'so2': components.get('so2', 0),
            'nh3': components.get('nh3', 0),
            'timestamp': datetime.fromtimestamp(current.get('dt', 0))
        }
        
        return processed_data
    
    def store_pollution_data(self, location: Location, pollution_data: Dict) -> List[PollutionData]:
        """
        Store pollution data in the database.
        
        Args:
            location: Location object
            pollution_data: Dictionary with pollution values
            
        Returns:
            List of created PollutionData objects
        """
        stored_data = []
        
        pollutant_mapping = {
            'pm25': 'pm25',
            'pm10': 'pm10',
            'co': 'co',
            'no2': 'no2',
            'o3': 'o3',
            'so2': 'so2'
        }
        
        for api_key, model_key in pollutant_mapping.items():
            if api_key in pollution_data:
                value = pollution_data[api_key]
                aqi_level = self._get_aqi_level(api_key, value)
                
                pollution_record = PollutionData.objects.create(
                    location=location,
                    pollutant_type=model_key,
                    value=Decimal(str(value)),
                    aqi_level=aqi_level,
                    timestamp=pollution_data.get('timestamp', timezone.now()),
                    source='OpenWeatherMap'
                )
                stored_data.append(pollution_record)
        
        return stored_data
    
    def _get_aqi_level(self, pollutant: str, value: float) -> str:
        """Get AQI level based on pollutant type and value."""
        # Simplified AQI calculation (would need proper formula in production)
        if pollutant == 'pm25':
            if value <= 12: return 'good'
            elif value <= 35.4: return 'moderate'
            elif value <= 55.4: return 'unhealthy_sensitive'
            elif value <= 150.4: return 'unhealthy'
            elif value <= 250.4: return 'very_unhealthy'
            else: return 'hazardous'
        
        elif pollutant == 'pm10':
            if value <= 54: return 'good'
            elif value <= 154: return 'moderate'
            elif value <= 254: return 'unhealthy_sensitive'
            elif value <= 354: return 'unhealthy'
            elif value <= 424: return 'very_unhealthy'
            else: return 'hazardous'
        
        # Default to moderate for other pollutants
        return 'moderate'


class IndustrialZoneService:
    """Service for industrial zone proximity detection and analysis."""
    
    @staticmethod
    def find_nearby_industrial_zones(location: Location, radius_km: float = 10.0) -> List[IndustrialZone]:
        """
        Find industrial zones within specified radius of a location.
        
        Args:
            location: Location object
            radius_km: Search radius in kilometers
            
        Returns:
            List of nearby industrial zones
        """
        user_coords = (float(location.latitude), float(location.longitude))
        nearby_zones = []
        
        for zone in IndustrialZone.objects.filter(is_active=True):
            zone_coords = (float(zone.latitude), float(zone.longitude))
            distance = geodesic(user_coords, zone_coords).kilometers
            
            if distance <= radius_km:
                nearby_zones.append(zone)
        
        return nearby_zones
    
    @staticmethod
    def get_active_industrial_zones(location: Location, radius_km: float = 10.0) -> List[IndustrialZone]:
        """
        Get industrial zones that are currently active within radius.
        
        Args:
            location: Location object
            radius_km: Search radius in kilometers
            
        Returns:
            List of active industrial zones
        """
        nearby_zones = IndustrialZoneService.find_nearby_industrial_zones(location, radius_km)
        return [zone for zone in nearby_zones if zone.is_active_now()]
    
    @staticmethod
    def calculate_industrial_impact(location: Location) -> Dict:
        """
        Calculate the industrial impact score for a location.
        
        Args:
            location: Location object
            
        Returns:
            Dictionary with impact metrics
        """
        active_zones = IndustrialZoneService.get_active_industrial_zones(location)
        
        if not active_zones:
            return {
                'impact_score': 0,
                'active_zones': 0,
                'total_emission_intensity': 0,
                'nearest_zone_distance': None,
                'risk_level': 'low'
            }
        
        # Calculate distances and total impact
        user_coords = (float(location.latitude), float(location.longitude))
        distances = []
        total_intensity = 0
        
        for zone in active_zones:
            zone_coords = (float(zone.latitude), float(zone.longitude))
            distance = geodesic(user_coords, zone_coords).kilometers
            distances.append(distance)
            total_intensity += float(zone.emission_intensity)
        
        nearest_distance = min(distances)
        
        # Calculate impact score (higher = more impact)
        impact_score = total_intensity / (nearest_distance + 1)  # +1 to avoid division by zero
        
        # Determine risk level
        if impact_score < 100:
            risk_level = 'low'
        elif impact_score < 500:
            risk_level = 'medium'
        elif impact_score < 1000:
            risk_level = 'high'
        else:
            risk_level = 'critical'
        
        return {
            'impact_score': round(impact_score, 2),
            'active_zones': len(active_zones),
            'total_emission_intensity': total_intensity,
            'nearest_zone_distance': round(nearest_distance, 2),
            'risk_level': risk_level,
            'zones': [
                {
                    'name': zone.name,
                    'type': zone.get_zone_type_display(),
                    'distance': round(geodesic(user_coords, (float(zone.latitude), float(zone.longitude))).kilometers, 2),
                    'emission_intensity': float(zone.emission_intensity)
                }
                for zone in active_zones
            ]
        }


class PollutionImpactCalculator:
    """Calculator for pollution impact and emotional visualizations."""
    
    @staticmethod
    def calculate_carbon_impact_equivalents(carbon_savings_kg: float) -> Dict:
        """
        Calculate various equivalents for carbon savings.
        
        Args:
            carbon_savings_kg: Carbon savings in kg CO2
            
        Returns:
            Dictionary with equivalent metrics
        """
        equivalents = {}
        
        # Factory hours offset
        factory_hours = carbon_savings_kg / ENVIRONMENTAL_CONVERSIONS['factory_emission_per_hour']
        equivalents['factory_hours'] = round(factory_hours, 2)
        
        # Trees planted equivalent
        trees_per_year = carbon_savings_kg / ENVIRONMENTAL_CONVERSIONS['tree_absorption_per_year']
        equivalents['trees_planted'] = round(trees_per_year, 2)
        
        # Cars off road equivalent
        cars_off_road = carbon_savings_kg / ENVIRONMENTAL_CONVERSIONS['car_emission_per_day']
        equivalents['cars_off_road'] = round(cars_off_road, 2)
        
        # Motorbikes off road equivalent
        motorbikes_off_road = carbon_savings_kg / ENVIRONMENTAL_CONVERSIONS['motorbike_emission_per_day']
        equivalents['motorbikes_off_road'] = round(motorbikes_off_road, 2)
        
        return equivalents
    
    @staticmethod
    def generate_emotional_message(carbon_savings_kg: float, equivalents: Dict) -> str:
        """
        Generate emotional visualization messages.
        
        Args:
            carbon_savings_kg: Carbon savings in kg CO2
            equivalents: Dictionary with equivalent metrics
            
        Returns:
            Emotional message string
        """
        messages = []
        
        if equivalents['factory_hours'] >= 1:
            messages.append(f"Your weekly savings offset the pollution from {equivalents['factory_hours']} factory hours! 🏭")
        
        if equivalents['trees_planted'] >= 1:
            tree_msg = f"You saved emissions equal to planting {equivalents['trees_planted']} trees! 🌱"
            if equivalents['trees_planted'] >= 5:
                tree_msg += " That's a small forest!"
            messages.append(tree_msg)
        
        if equivalents['cars_off_road'] >= 1:
            car_msg = f"Your actions took {equivalents['cars_off_road']} cars off the road for a day! 🚗"
            messages.append(car_msg)
        
        if not messages:
            return f"Great job! You saved {carbon_savings_kg:.2f} kg of CO2! 🌍"
        
        return " ".join(messages)
    
    @staticmethod
    def store_pollution_impact(user, location: Location, carbon_savings_kg: float):
        """
        Store pollution impact calculation for a user.
        
        Args:
            user: User object
            location: Location object
            carbon_savings_kg: Carbon savings in kg CO2
        """
        equivalents = PollutionImpactCalculator.calculate_carbon_impact_equivalents(carbon_savings_kg)
        
        impact = PollutionImpact.objects.create(
            user=user,
            location=location,
            carbon_savings_kg=Decimal(str(carbon_savings_kg)),
            equivalent_factory_hours=Decimal(str(equivalents['factory_hours'])),
            trees_planted_equivalent=int(equivalents['trees_planted']),
            cars_off_road_equivalent=Decimal(str(equivalents['cars_off_road']))
        )
        
        return impact


class PollutionAlertService:
    """Service for creating and managing pollution alerts."""
    
    @staticmethod
    def create_pollution_alert(user, alert_type: str, title: str, message: str, 
                             location: Location = None, industrial_zone: IndustrialZone = None,
                             severity: str = 'medium'):
        """
        Create a pollution alert for a user.
        
        Args:
            user: User object
            alert_type: Type of alert
            title: Alert title
            message: Alert message
            location: Related location (optional)
            industrial_zone: Related industrial zone (optional)
            severity: Alert severity
        """
        alert = UserPollutionAlert.objects.create(
            user=user,
            alert_type=alert_type,
            title=title,
            message=message,
            location=location,
            industrial_zone=industrial_zone,
            severity=severity,
            expires_at=timezone.now() + timedelta(hours=24)  # Expire after 24 hours
        )
        
        return alert
    
    @staticmethod
    def check_and_create_alerts(user, location: Location):
        """
        Check conditions and create appropriate pollution alerts.
        
        Args:
            user: User object
            location: Location object
        """
        # Check industrial zone activity
        active_zones = IndustrialZoneService.get_active_industrial_zones(location)
        if active_zones:
            impact = IndustrialZoneService.calculate_industrial_impact(location)
            
            if impact['risk_level'] in ['high', 'critical']:
                PollutionAlertService.create_pollution_alert(
                    user=user,
                    alert_type='industrial_activity',
                    title=f"High Industrial Activity Alert",
                    message=f"There are {impact['active_zones']} active industrial zones near you. Current risk level: {impact['risk_level'].upper()}. Consider avoiding outdoor activities during peak hours.",
                    location=location,
                    severity=impact['risk_level']
                )
        
        # Check pollution levels
        recent_pollution = PollutionData.objects.filter(
            location=location,
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).order_by('-timestamp').first()
        
        if recent_pollution and recent_pollution.aqi_level in ['unhealthy', 'very_unhealthy', 'hazardous']:
            PollutionAlertService.create_pollution_alert(
                user=user,
                alert_type='high_pollution',
                title=f"High Pollution Alert - {recent_pollution.get_aqi_level_display()}",
                message=f"Current {recent_pollution.get_pollutant_type_display()} levels are high ({recent_pollution.value} {recent_pollution.unit}). Limit outdoor activities.",
                location=location,
                severity='high' if recent_pollution.aqi_level == 'unhealthy' else 'critical'
            )
