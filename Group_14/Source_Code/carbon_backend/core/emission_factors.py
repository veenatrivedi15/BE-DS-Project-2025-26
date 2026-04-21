"""
India-Specific Emission Factors
Source: WRI India 2015 - "India Specific Road Transport Emission Factors"

Documentation:
- Methodology: IPCC Tier 3 (activity-based)
- Validation: Tata Motors, Hero MotoCorp, Mahindra, Bajaj, ACC Limited, Ashok Leyland, NTPC
- URL: https://indiaghgp.org/road-transport-emission-factors
"""

from typing import Dict, Optional

# India-Specific Emission Factors (kg CO₂/km or kg CO₂/passenger-km)
# Source: WRI India 2015
INDIA_EMISSION_FACTORS = {
    'vehicle_baseline': {
        # Baseline factors (what user would typically use)
        'petrol_car_hatchback': 0.130,      # <1400cc, Gasoline
        'petrol_car_sedan': 0.142,          # >1400cc, Gasoline
        'diesel_car_hatchback': 0.117,      # <1400cc, Diesel
        'motorcycle_125cc': 0.029,          # <125cc, Gasoline
        'two_wheeler_single': 0.130,        # Baseline comparison uses petrol car
        'two_wheeler_double': 0.130,        # Baseline comparison uses petrol car
        'autorickshaw_petrol': 0.1135,      # Petrol auto-rickshaw
        'autorickshaw_cng': 0.10768,        # CNG auto-rickshaw
        'bus_city': 0.015161,               # City bus (per passenger-km)
        'metro_subway': 0.008,              # Metro/Subway (per passenger-km)
    },
    'transport_actual': {
        # Actual emission factors for chosen transport modes
        'walking': 0.000,                   # Zero emissions
        'cycling': 0.000,                   # Zero emissions
        'electric_scooter': 0.020,          # Considering Indian grid emissions
        'electric_car': 0.085,              # Grid emission factor (Indian grid)
        'hybrid_car': 0.095,                # Hybrid vehicle
        'bus_city': 0.015161,               # City bus (per passenger-km)
        'metro_subway': 0.008,              # Metro/Subway (per passenger-km)
        'shared_taxi': 0.071,               # Assuming 2 passengers
        'motorcycle': 0.029,                # Motorcycle
        'two_wheeler_single': 0.029,        # Two Wheeler (Solo)
        'two_wheeler_double': 0.0145,       # Two Wheeler (Carpool - per person)
        'petrol_car': 0.130,                # Petrol car (no savings)
        'diesel_car': 0.117,                # Diesel car
        'autorickshaw_petrol': 0.1135,      # Petrol auto-rickshaw
        'autorickshaw_cng': 0.10768,        # CNG auto-rickshaw
    }
}

# Transport mode mapping (for backward compatibility)
TRANSPORT_MODE_MAPPING = {
    'car': 'petrol_car',
    'carpool': 'shared_taxi',
    'two_wheeler_single': 'two_wheeler_single',
    'two_wheeler_double': 'two_wheeler_double',
    'public_transport': 'bus_city',
    'bicycle': 'cycling',
    'walking': 'walking',
    'work_from_home': 'walking',  # Treated as zero emissions
}

# References and validation
REFERENCES = {
    'WRI_2015': {
        'title': 'India Specific Road Transport Emission Factors',
        'year': 2015,
        'organization': 'World Resources Institute (WRI)',
        'validation': [
            'Tata Motors',
            'Hero MotoCorp',
            'Mahindra',
            'Bajaj',
            'ACC Limited',
            'Ashok Leyland',
            'NTPC'
        ],
        'methodology': 'IPCC Tier 3 (activity-based)',
        'url': 'https://indiaghgp.org/road-transport-emission-factors',
        'document': 'WRI-2015-India-Specific-Road-Transport-Emission-Factors.pdf'
    },
    'IPCC_2006': {
        'title': '2006 IPCC Guidelines for National Greenhouse Gas Inventories',
        'volume': 'Volume 2: Energy, Chapter 3: Mobile Combustion',
        'url': 'https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_3_Ch3_Mobile_Combustion.pdf'
    },
    'GHG_Protocol': {
        'title': 'GHG Protocol Scope 3 Calculation Guidance',
        'category': 'Category 6: Business Travel',
        'url': 'https://ghgprotocol.org/sites/default/files/2022-12/Chapter6.pdf'
    }
}


def get_baseline_ef(transport_mode: str) -> float:
    """
    Get baseline emission factor for transport mode.
    
    This represents what the user would typically use (e.g., petrol car).
    
    Args:
        transport_mode: Transport mode identifier
    
    Returns:
        Baseline emission factor (kg CO₂/km)
    """
    # Map old transport modes to new ones
    mapped_mode = TRANSPORT_MODE_MAPPING.get(transport_mode, transport_mode)
    
    # Try to get from baseline factors
    baseline_ef = INDIA_EMISSION_FACTORS['vehicle_baseline'].get(
        mapped_mode,
        INDIA_EMISSION_FACTORS['vehicle_baseline'].get('petrol_car_hatchback', 0.130)
    )
    
    return baseline_ef


def get_actual_ef(transport_mode: str) -> float:
    """
    Get actual emission factor for transport mode.
    
    This represents the emissions of the chosen transport mode.
    
    Args:
        transport_mode: Transport mode identifier
    
    Returns:
        Actual emission factor (kg CO₂/km)
    """
    # Map old transport modes to new ones
    mapped_mode = TRANSPORT_MODE_MAPPING.get(transport_mode, transport_mode)
    
    # Try to get from actual factors
    actual_ef = INDIA_EMISSION_FACTORS['transport_actual'].get(
        mapped_mode,
        0.0  # Default to zero if not found
    )
    
    return actual_ef


def get_emission_factor_info(transport_mode: str) -> Dict:
    """
    Get comprehensive emission factor information.
    
    Args:
        transport_mode: Transport mode identifier
    
    Returns:
        Dictionary with baseline_ef, actual_ef, and savings
    """
    baseline_ef = get_baseline_ef(transport_mode)
    actual_ef = get_actual_ef(transport_mode)
    savings = baseline_ef - actual_ef
    
    return {
        'transport_mode': transport_mode,
        'baseline_ef': baseline_ef,
        'actual_ef': actual_ef,
        'savings_per_km': max(0.0, savings),
        'references': REFERENCES
    }


