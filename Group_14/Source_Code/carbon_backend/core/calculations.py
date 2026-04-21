"""
Robust Carbon Credit Calculation Engine
Based on: WRI India 2015 + IPCC 2006 Guidelines + GHG Protocol

Formula: CC = Σ[(EF_baseline - EF_actual) × Distance × Time_Weight × Context_Factor]

References:
- WRI India 2015: India Specific Road Transport Emission Factors
- IPCC 2006: Guidelines for National Greenhouse Gas Inventories
- GHG Protocol: Scope 3 Category 6 Business Travel
- UNFCCC: Estimation of emissions from road transport
- CRRI India: Evaluation of on-road vehicle fuel consumption
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Mumbai, India coordinates (default location)
MUMBAI_COORDINATES = {
    'lat': 19.0760,
    'lng': 72.8777
}


def calculate_carbon_credits(
    ef_baseline: float,
    ef_actual: float,
    distance: float,
    time_weight: float,
    context_factor: float
) -> float:
    """
    Calculate carbon credits earned for a trip.
    
    Formula: CC = (EF_baseline - EF_actual) × Distance × Time_Weight × Context_Factor
    
    Args:
        ef_baseline: Baseline emission factor (kg CO₂/km)
        ef_actual: Actual emission factor (kg CO₂/km)
        distance: Distance traveled (km)
        time_weight: Time weighting factor
        context_factor: Environmental context factor
    
    Returns:
        Carbon credits earned (kg CO₂)
    
    References:
        - WRI India 2015: India Specific Road Transport Emission Factors
        - IPCC 2006: Guidelines for National GHG Inventories
    """
    try:
        # Calculate emission difference
        emission_difference = Decimal(str(ef_baseline)) - Decimal(str(ef_actual))
        
        # Ensure non-negative
        if emission_difference < 0:
            emission_difference = Decimal('0')
        
        # Calculate credits with all factors
        credits = (
            emission_difference *
            Decimal(str(distance)) *
            Decimal(str(time_weight)) *
            Decimal(str(context_factor))
        )
        
        # Round to 4 decimal places for precision
        credits = float(credits.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
        
        # Ensure non-negative result
        return max(0.0, credits)
    
    except Exception as e:
        logger.error(f"Error calculating carbon credits: {str(e)}")
        return 0.0


def calculate_time_weight(
    time_period: str,
    traffic_condition: str,
    recency_days: int = 0
) -> float:
    """
    Calculate time weight: Peak_Factor × Traffic_Multiplier × Recency_Weight
    
    Reference: IPCC Good Practice Guidance Section 2.3
    
    Args:
        time_period: Time of day (peak_morning, peak_evening, off_peak, late_night)
        traffic_condition: Traffic level (heavy, moderate, light)
        recency_days: Days since trip occurred (0 = today)
    
    Returns:
        Time weight factor
    """
    # Peak hour factors (IPCC-based)
    peak_factors = {
        'peak_morning': Decimal('1.2'),    # 7-10 AM
        'peak_evening': Decimal('1.2'),     # 6-9 PM
        'off_peak': Decimal('1.0'),         # Normal hours
        'late_night': Decimal('0.8'),       # 11 PM - 5 AM
    }
    
    # Traffic multipliers (UNFCCC 2004: 20-40% increase in heavy traffic)
    traffic_multipliers = {
        'heavy': Decimal('1.3'),      # 30% increase
        'moderate': Decimal('1.1'),   # 10% increase
        'light': Decimal('1.0'),      # Baseline
    }
    
    # Recency weight (rewards recent behavior more)
    if recency_days <= 7:
        recency_weight = Decimal('1.0')
    elif recency_days <= 30:
        recency_weight = Decimal('0.9')
    elif recency_days <= 90:
        recency_weight = Decimal('0.7')
    else:
        recency_weight = Decimal('0.5')
    
    # Get factors
    peak_factor = peak_factors.get(time_period, Decimal('1.0'))
    traffic_multiplier = traffic_multipliers.get(traffic_condition, Decimal('1.0'))
    
    # Calculate time weight
    time_weight = peak_factor * traffic_multiplier * recency_weight
    
    return float(time_weight)


def calculate_context_factor(
    weather: str,
    route_type: str,
    aqi_level: str,
    load_factor: float = 1.0,
    season: str = 'normal'
) -> float:
    """
    Calculate context factor: Weather × Route × AQI × Load × Seasonal
    
    References:
        - IPCC 2006 Guidelines
        - CRRI India: Fuel consumption variability study
        - Clean Air Asia: Air Pollution & GHG Emissions
    
    Args:
        weather: Weather condition (heavy_rain, light_rain, normal, favorable)
        route_type: Route type (hilly, city_center, highway, suburban)
        aqi_level: Air quality index level (hazardous, very_poor, moderate, good)
        load_factor: Vehicle load factor (1.1=full, 1.0=normal, 0.95=light)
        season: Season (winter, summer, monsoon, post_monsoon)
    
    Returns:
        Context factor
    """
    # Weather factors (CRRI: 20% increase in heavy rain)
    weather_factors = {
        'heavy_rain': Decimal('1.2'),      # 20% increase
        'light_rain': Decimal('1.1'),       # 10% increase
        'normal': Decimal('1.0'),          # Baseline
        'favorable': Decimal('0.95'),      # 5% reduction
    }
    
    # Route factors (IPCC-based terrain adjustments)
    route_factors = {
        'hilly': Decimal('1.3'),           # 30% increase (gravity work)
        'city_center': Decimal('1.2'),     # 20% increase (frequent stops)
        'suburban': Decimal('1.0'),        # Baseline
        'highway': Decimal('0.9'),         # 10% more efficient
    }
    
    # AQI factors (Clean Air Asia standards)
    aqi_factors = {
        'hazardous': Decimal('1.2'),       # AQI > 300
        'very_poor': Decimal('1.1'),        # AQI 201-300
        'moderate': Decimal('1.0'),        # AQI 101-200
        'good': Decimal('0.95'),           # AQI < 100
    }
    
    # Seasonal factors (India-specific)
    seasonal_factors = {
        'winter': Decimal('0.95'),         # Better efficiency
        'summer': Decimal('1.1'),         # AC usage increases
        'monsoon': Decimal('1.2'),         # Rain impacts
        'post_monsoon': Decimal('1.0'),    # Normal
    }
    
    # Get factors
    weather_factor = weather_factors.get(weather, Decimal('1.0'))
    route_factor = route_factors.get(route_type, Decimal('1.0'))
    aqi_factor = aqi_factors.get(aqi_level, Decimal('1.0'))
    seasonal_factor = seasonal_factors.get(season, Decimal('1.0'))
    load_factor_decimal = Decimal(str(load_factor))
    
    # Calculate context factor
    context_factor = (
        weather_factor *
        route_factor *
        aqi_factor *
        load_factor_decimal *
        seasonal_factor
    )
    
    return float(context_factor)


def calculate_trip_emissions(
    distance_km: float,
    transport_mode: str,
    ef_actual: Optional[float] = None
) -> Tuple[float, float]:
    """
    Calculate actual emissions for a trip.
    
    Args:
        distance_km: Distance in kilometers
        transport_mode: Transport mode
        ef_actual: Actual emission factor (if None, uses default)
    
    Returns:
        Tuple of (emissions_kg_co2, emission_factor)
    """
    from .emission_factors import get_actual_ef
    
    if ef_actual is None:
        ef_actual = get_actual_ef(transport_mode)
    
    emissions = float(Decimal(str(distance_km)) * Decimal(str(ef_actual)))
    
    return emissions, ef_actual


def calculate_carbon_savings(
    distance_km: float,
    ef_baseline: float,
    ef_actual: float
) -> float:
    """
    Calculate carbon savings (difference between baseline and actual).
    
    Args:
        distance_km: Distance in kilometers
        ef_baseline: Baseline emission factor
        ef_actual: Actual emission factor
    
    Returns:
        Carbon savings in kg CO₂
    """
    savings = (Decimal(str(ef_baseline)) - Decimal(str(ef_actual))) * Decimal(str(distance_km))
    return max(0.0, float(savings))


def get_recency_days(trip_date: datetime) -> int:
    """
    Calculate days since trip occurred.
    
    Args:
        trip_date: Date of the trip
    
    Returns:
        Number of days since trip
    """
    if trip_date is None:
        return 0
    
    today = datetime.now().date()
    trip_date_only = trip_date.date() if isinstance(trip_date, datetime) else trip_date
    
    delta = today - trip_date_only
    return max(0, delta.days)


