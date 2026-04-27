"""
Improved Carbon Credits Calculator based on scientific research and industry standards.

This module implements accurate carbon emission calculations and credit generation
based on:
- IPCC Guidelines for National Greenhouse Gas Inventories
- DEFRA UK Government GHG Conversion Factors 2024
- EPA Emission Factors for Greenhouse Gas Inventories
- IEA Transport CO2 Emissions Factors

References:
- https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
- https://www.epa.gov/climateleadership/ghg-emission-factors-hub
- https://www.iea.org/data-and-statistics/data-tools/co2-emissions-from-fuel-combustion-statistics
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple
from core.models import SystemConfig

logger = logging.getLogger(__name__)

# OFFICIAL EMISSION FACTORS (kg CO2 per km per passenger)
# Based on DEFRA 2024 and EPA 2024 data
EMISSION_FACTORS = {
    # Private Vehicles (average passenger car)
    'car_petrol': Decimal('0.168'),      # Petrol car (average)
    'car_diesel': Decimal('0.171'),      # Diesel car (average)
    'car_hybrid': Decimal('0.109'),      # Hybrid car
    'car_electric': Decimal('0.047'),    # Electric car (including electricity generation)
    'car_average': Decimal('0.170'),     # Average car (mixed fuel types)
    
    # Shared Transport
    'carpool_2': Decimal('0.085'),       # Car with 2 people (50% reduction)
    'carpool_3': Decimal('0.057'),       # Car with 3 people (66% reduction)
    'carpool_4': Decimal('0.043'),       # Car with 4 people (75% reduction)
    
    # Public Transport
    'bus_local': Decimal('0.082'),       # Local bus (average occupancy)
    'bus_coach': Decimal('0.027'),       # Long-distance coach
    'train_local': Decimal('0.035'),     # Local/regional train
    'train_national': Decimal('0.028'),  # National rail
    'metro_subway': Decimal('0.030'),    # Underground/metro
    'tram': Decimal('0.029'),            # Tram/light rail
    
    # Active Transport
    'bicycle': Decimal('0.000'),         # Bicycle (zero direct emissions)
    'walking': Decimal('0.000'),         # Walking (zero direct emissions)
    'e_scooter': Decimal('0.008'),       # Electric scooter (including electricity)
    'e_bike': Decimal('0.004'),          # Electric bicycle
    
    # Remote Work
    'work_from_home': Decimal('0.000'),  # No commute emissions
    
    # Motorcycle
    'motorcycle_small': Decimal('0.084'), # Small motorcycle (<125cc)
    'motorcycle_medium': Decimal('0.103'), # Medium motorcycle (125-500cc)
    'motorcycle_large': Decimal('0.146'),  # Large motorcycle (>500cc)
}

# BASELINE EMISSION FACTOR (what we compare against)
# Using average car emissions as the baseline for credit calculation
BASELINE_EMISSION_FACTOR = EMISSION_FACTORS['car_average']

# CARBON CREDIT CONVERSION FACTORS
# How much CO2 savings equals 1 carbon credit
KG_CO2_PER_CREDIT = Decimal('1.0')  # 1 kg CO2 saved = 1 credit (adjustable)

# ADDITIONAL FACTORS FOR ACCURATE CALCULATION
LIFECYCLE_FACTORS = {
    # Well-to-Wheel factors (includes fuel production, distribution, etc.)
    'petrol_wtw_factor': Decimal('1.25'),    # 25% higher for lifecycle emissions
    'diesel_wtw_factor': Decimal('1.22'),    # 22% higher for lifecycle emissions
    'electricity_wtw_factor': Decimal('1.15'), # 15% higher for electricity generation
    'public_transport_efficiency': Decimal('0.85'), # 15% efficiency bonus for high occupancy
}

# REGIONAL ADJUSTMENT FACTORS (can be configured per region)
REGIONAL_FACTORS = {
    'default': Decimal('1.0'),
    'us': Decimal('1.0'),
    'uk': Decimal('0.95'),      # Slightly lower due to cleaner electricity grid
    'eu': Decimal('0.90'),      # Lower due to renewable energy
    'nordic': Decimal('0.75'),  # Much lower due to high renewable energy
}

def get_emission_factor(transport_mode: str, include_lifecycle: bool = True) -> Decimal:
    """
    Get the emission factor for a specific transport mode.
    
    Args:
        transport_mode: String representing the transport mode
        include_lifecycle: Whether to include well-to-wheel emissions
        
    Returns:
        Decimal emission factor in kg CO2 per km per passenger
    """
    try:
        # Try to get custom factor from database first
        config_key = f"emission_factor_{transport_mode}"
        db_value = SystemConfig.get_value(config_key)
        
        if db_value:
            return Decimal(db_value)
        
        # Map common transport modes to our detailed factors
        mode_mapping = {
            'car': 'car_average',
            'carpool': 'carpool_2',  # Default to 2-person carpool
            'public_transport': 'bus_local',  # Default to local bus
            'bus': 'bus_local',
            'train': 'train_local',
            'bicycle': 'bicycle',
            'walking': 'walking',
            'work_from_home': 'work_from_home',
            'motorcycle': 'motorcycle_medium',
        }
        
        # Get the mapped mode or use the original if it exists in EMISSION_FACTORS
        mapped_mode = mode_mapping.get(transport_mode, transport_mode)
        base_factor = EMISSION_FACTORS.get(mapped_mode, BASELINE_EMISSION_FACTOR)
        
        # Apply lifecycle factors if requested
        if include_lifecycle:
            if 'petrol' in mapped_mode or transport_mode == 'car':
                base_factor *= LIFECYCLE_FACTORS['petrol_wtw_factor']
            elif 'diesel' in mapped_mode:
                base_factor *= LIFECYCLE_FACTORS['diesel_wtw_factor']
            elif 'electric' in mapped_mode:
                base_factor *= LIFECYCLE_FACTORS['electricity_wtw_factor']
            elif any(pt in mapped_mode for pt in ['bus', 'train', 'metro', 'tram']):
                base_factor *= LIFECYCLE_FACTORS['public_transport_efficiency']
        
        return base_factor
        
    except Exception as e:
        logger.warning(f"Error getting emission factor for {transport_mode}: {str(e)}")
        return BASELINE_EMISSION_FACTOR

def get_regional_factor(region: str = 'default') -> Decimal:
    """Get regional adjustment factor for emissions."""
    try:
        config_key = f"regional_factor_{region}"
        db_value = SystemConfig.get_value(config_key)
        
        if db_value:
            return Decimal(db_value)
        
        return REGIONAL_FACTORS.get(region.lower(), REGIONAL_FACTORS['default'])
    except Exception as e:
        logger.warning(f"Error getting regional factor for {region}: {str(e)}")
        return REGIONAL_FACTORS['default']

def calculate_trip_emissions(distance_km: float, transport_mode: str, 
                           region: str = 'default', passengers: int = 1) -> Decimal:
    """
    Calculate CO2 emissions for a specific trip.
    
    Args:
        distance_km: Distance traveled in kilometers
        transport_mode: Mode of transport used
        region: Regional location for adjustment factors
        passengers: Number of passengers (for carpooling calculations)
        
    Returns:
        Decimal CO2 emissions in kg
    """
    try:
        distance = Decimal(str(distance_km))
        
        # Get base emission factor
        emission_factor = get_emission_factor(transport_mode)
        
        # Adjust for carpooling if applicable
        if transport_mode == 'carpool' and passengers > 1:
            # Use more specific carpool factors based on passenger count
            if passengers == 2:
                emission_factor = EMISSION_FACTORS['carpool_2']
            elif passengers == 3:
                emission_factor = EMISSION_FACTORS['carpool_3']
            elif passengers >= 4:
                emission_factor = EMISSION_FACTORS['carpool_4']
            else:
                emission_factor = emission_factor / Decimal(str(passengers))
        
        # Apply regional adjustment
        regional_factor = get_regional_factor(region)
        
        # Calculate total emissions
        total_emissions = distance * emission_factor * regional_factor
        
        return total_emissions.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        
    except Exception as e:
        logger.error(f"Error calculating trip emissions: {str(e)}")
        return Decimal('0')

def calculate_carbon_savings(distance_km: float, transport_mode: str, 
                           baseline_mode: str = 'car_average', 
                           region: str = 'default', passengers: int = 1) -> Tuple[Decimal, Decimal]:
    """
    Calculate carbon savings compared to baseline transport mode.
    
    Args:
        distance_km: Distance traveled in kilometers
        transport_mode: Actual mode of transport used
        baseline_mode: Baseline mode to compare against (default: average car)
        region: Regional location for adjustment factors
        passengers: Number of passengers for carpooling
        
    Returns:
        Tuple of (carbon_saved_kg, carbon_added_kg)
    """
    try:
        # Calculate emissions for chosen transport mode
        actual_emissions = calculate_trip_emissions(distance_km, transport_mode, region, passengers)
        
        # Calculate baseline emissions (what would have been emitted)
        baseline_emissions = calculate_trip_emissions(distance_km, baseline_mode, region, 1)
        
        # Calculate savings (positive) or additional emissions (negative)
        carbon_difference = baseline_emissions - actual_emissions
        
        if carbon_difference >= 0:
            # Saved carbon (sustainable choice)
            carbon_saved = carbon_difference
            carbon_added = Decimal('0')
        else:
            # Added carbon (less sustainable choice)
            carbon_saved = Decimal('0')
            carbon_added = abs(carbon_difference)
        
        return (
            carbon_saved.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            carbon_added.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        )
        
    except Exception as e:
        logger.error(f"Error calculating carbon savings: {str(e)}")
        return (Decimal('0'), Decimal('0'))

def calculate_carbon_credits(distance_km: float, transport_mode: str, 
                           region: str = 'default', passengers: int = 1,
                           credit_multiplier: float = 1.0) -> Decimal:
    """
    Calculate carbon credits earned based on carbon savings.
    
    Args:
        distance_km: Distance traveled in kilometers
        transport_mode: Mode of transport used
        region: Regional location for adjustment factors
        passengers: Number of passengers for carpooling
        credit_multiplier: Multiplier for credit calculation (for incentives)
        
    Returns:
        Decimal amount of carbon credits earned
    """
    try:
        # Calculate carbon savings
        carbon_saved, _ = calculate_carbon_savings(distance_km, transport_mode, 'car_average', region, passengers)
        
        # Get credits per kg CO2 saved
        credits_per_kg = Decimal('1') / KG_CO2_PER_CREDIT
        
        # Apply credit multiplier for incentives
        multiplier = Decimal(str(credit_multiplier))
        
        # Calculate total credits
        credits = carbon_saved * credits_per_kg * multiplier
        
        # Special handling for work from home (fixed credit amount)
        if transport_mode == 'work_from_home':
            # Award credits based on average commute distance saved
            avg_commute_distance = SystemConfig.get_value('avg_commute_distance') or '20'  # 20km default
            avg_distance = Decimal(avg_commute_distance)
            wfh_savings, _ = calculate_carbon_savings(float(avg_distance), 'work_from_home', 'car_average', region)
            credits = wfh_savings * credits_per_kg * multiplier
        
        return credits.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
    except Exception as e:
        logger.error(f"Error calculating carbon credits: {str(e)}")
        return Decimal('0')

def get_transport_mode_info(transport_mode: str) -> Dict:
    """
    Get comprehensive information about a transport mode.
    
    Args:
        transport_mode: Mode of transport
        
    Returns:
        Dictionary with emission factor, sustainability rating, and description
    """
    emission_factor = get_emission_factor(transport_mode)
    baseline_factor = BASELINE_EMISSION_FACTOR
    
    # Calculate sustainability rating (0-100, higher is better)
    if emission_factor == 0:
        sustainability_rating = 100
    else:
        reduction_percentage = ((baseline_factor - emission_factor) / baseline_factor) * 100
        sustainability_rating = max(0, min(100, reduction_percentage))
    
    # Mode descriptions
    descriptions = {
        'car': 'Private car (single occupancy)',
        'carpool': 'Shared car ride (2+ passengers)',
        'public_transport': 'Bus, train, or metro',
        'bicycle': 'Bicycle (zero emissions)',
        'walking': 'Walking (zero emissions)',
        'work_from_home': 'Remote work (no commute)',
        'motorcycle': 'Motorcycle or scooter',
    }
    
    return {
        'emission_factor_kg_per_km': float(emission_factor),
        'sustainability_rating': float(sustainability_rating),
        'description': descriptions.get(transport_mode, f'{transport_mode.title()} transport'),
        'is_sustainable': emission_factor < baseline_factor,
        'baseline_comparison': float(baseline_factor - emission_factor),
    }

# Backward compatibility functions
def calculate_carbon_credits_legacy(distance_km, transport_mode):
    """Legacy function for backward compatibility."""
    return calculate_carbon_credits(distance_km, transport_mode)

def calculate_carbon_savings_legacy(distance_km, transport_mode):
    """Legacy function for backward compatibility."""
    carbon_saved, carbon_added = calculate_carbon_savings(distance_km, transport_mode)
    return carbon_saved  # Return only savings for compatibility






