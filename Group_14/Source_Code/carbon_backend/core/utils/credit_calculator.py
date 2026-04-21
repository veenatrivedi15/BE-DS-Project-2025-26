"""
Utilities for calculating carbon credits based on 
distance traveled and transport mode.

DEPRECATED: This module is maintained for backward compatibility.
New implementations should use improved_carbon_calculator.py
"""

import logging
from decimal import Decimal
from core.models import SystemConfig

# Import the new improved calculator
try:
    from .improved_carbon_calculator import (
        calculate_carbon_credits as new_calculate_carbon_credits,
        calculate_carbon_savings as new_calculate_carbon_savings,
        get_transport_mode_info
    )
    NEW_CALCULATOR_AVAILABLE = True
except ImportError:
    NEW_CALCULATOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default transport mode multipliers
DEFAULT_MODE_MULTIPLIERS = {
    'car': 0,  # No credits for single-occupancy car
    'carpool': 1.5,
    'public_transport': 2.0,
    'bicycle': 3.0,
    'walking': 3.5,
    'work_from_home': 2.0  # Credits for not commuting at all
}

# Default base rate (credits per km)
DEFAULT_BASE_RATE = 0.1


def get_mode_multiplier(transport_mode):
    """
    Get the multiplier for a specific transport mode.
    Attempts to get from database config, falls back to defaults.
    
    Args:
        transport_mode: String representing the transport mode
        
    Returns:
        Decimal multiplier value
    """
    try:
        # Try to get from database
        config_key = f"multiplier_{transport_mode}"
        db_value = SystemConfig.get_value(config_key)
        
        if db_value:
            return Decimal(db_value)
        
        # Fall back to defaults
        return Decimal(DEFAULT_MODE_MULTIPLIERS.get(transport_mode, 0))
    except Exception as e:
        logger.warning(f"Error getting mode multiplier: {str(e)}")
        return Decimal(DEFAULT_MODE_MULTIPLIERS.get(transport_mode, 0))


def get_base_rate():
    """
    Get the base rate for credit calculation.
    Attempts to get from database config, falls back to default.
    
    Returns:
        Decimal base rate value
    """
    try:
        # Try to get from database
        db_value = SystemConfig.get_value("base_credit_rate")
        
        if db_value:
            return Decimal(db_value)
        
        # Fall back to default
        return Decimal(DEFAULT_BASE_RATE)
    except Exception as e:
        logger.warning(f"Error getting base rate: {str(e)}")
        return Decimal(DEFAULT_BASE_RATE)


def calculate_carbon_credits(distance_km, transport_mode):
    """
    Calculate carbon credits based on distance and transport mode.
    
    DEPRECATED: Use improved_carbon_calculator.calculate_carbon_credits() for new implementations.
    This function is maintained for backward compatibility.
    
    Args:
        distance_km: Decimal distance in kilometers
        transport_mode: String representing the transport mode
        
    Returns:
        Decimal amount of carbon credits earned
    """
    # Use new calculator if available
    if NEW_CALCULATOR_AVAILABLE:
        try:
            return new_calculate_carbon_credits(float(distance_km), transport_mode)
        except Exception as e:
            logger.warning(f"New calculator failed, falling back to legacy: {str(e)}")
    
    # Legacy calculation (fallback)
    # Get multiplier for the transport mode
    multiplier = get_mode_multiplier(transport_mode)
    
    # Get base rate per kilometer
    base_rate = get_base_rate()
    
    # Calculate credits
    credits = Decimal(distance_km) * multiplier * base_rate
    
    # Round to 2 decimal places
    return round(credits, 2)


def calculate_carbon_savings(distance_km, transport_mode):
    """
    Calculate carbon savings in kg of CO2 based on distance and transport mode.
    
    DEPRECATED: Use improved_carbon_calculator.calculate_carbon_savings() for new implementations.
    This function is maintained for backward compatibility.
    
    Args:
        distance_km: Decimal distance in kilometers
        transport_mode: String representing the transport mode
        
    Returns:
        Decimal amount of carbon savings in kg of CO2
    """
    # Use new calculator if available
    if NEW_CALCULATOR_AVAILABLE:
        try:
            carbon_saved, _ = new_calculate_carbon_savings(float(distance_km), transport_mode)
            return carbon_saved
        except Exception as e:
            logger.warning(f"New calculator failed, falling back to legacy: {str(e)}")
    
    # Legacy calculation (fallback)
    # Average car emissions per km (in kg of CO2)
    car_emissions_per_km = Decimal('0.192')
    
    # Emissions by transport mode (in kg of CO2 per km)
    emissions_by_mode = {
        'car': car_emissions_per_km,
        'carpool': car_emissions_per_km / 2,  # Assumes 2 people in carpool
        'public_transport': Decimal('0.041'),
        'bicycle': Decimal('0'),
        'walking': Decimal('0'),
        'work_from_home': car_emissions_per_km  # Savings from not driving at all
    }
    
    # Get emissions for selected mode
    mode_emissions = emissions_by_mode.get(transport_mode, Decimal('0'))
    
    # Calculate savings (car emissions minus mode emissions)
    if transport_mode == 'car':
        savings = Decimal('0')
    else:
        savings = (car_emissions_per_km - mode_emissions) * Decimal(distance_km)
    
    # Round to 2 decimal places
    return round(savings, 2) 