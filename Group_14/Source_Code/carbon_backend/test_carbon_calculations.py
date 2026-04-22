#!/usr/bin/env python
"""
Test script to demonstrate the improved carbon credit calculation system.
Run this script to see examples of the new carbon calculation methodology.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from core.utils.improved_carbon_calculator import (
    calculate_trip_emissions,
    calculate_carbon_savings,
    calculate_carbon_credits,
    get_transport_mode_info,
    EMISSION_FACTORS
)

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_calculation_example(title, distance, mode, region='default', passengers=1):
    """Print a detailed calculation example."""
    print(f"\n📊 {title}")
    print("-" * 40)
    print(f"Distance: {distance} km")
    print(f"Transport Mode: {mode}")
    print(f"Region: {region}")
    if passengers > 1:
        print(f"Passengers: {passengers}")
    
    # Calculate emissions
    emissions = calculate_trip_emissions(distance, mode, region, passengers)
    print(f"Trip Emissions: {emissions:.3f} kg CO2")
    
    # Calculate savings
    carbon_saved, carbon_added = calculate_carbon_savings(distance, mode, 'car_average', region, passengers)
    print(f"Carbon Saved: {carbon_saved:.3f} kg CO2")
    if carbon_added > 0:
        print(f"Carbon Added: {carbon_added:.3f} kg CO2")
    
    # Calculate credits
    credits = calculate_carbon_credits(distance, mode, region, passengers)
    print(f"Credits Earned: {credits:.2f} credits")
    
    # Get mode info
    mode_info = get_transport_mode_info(mode)
    print(f"Sustainability Rating: {mode_info['sustainability_rating']:.1f}/100")
    print(f"Description: {mode_info['description']}")

def main():
    """Run the carbon calculation demonstration."""
    
    print_header("🌍 CARBON CREDITS CALCULATION SYSTEM DEMO")
    print("Based on scientific research and international standards")
    print("Data sources: DEFRA 2024, EPA 2024, IPCC Guidelines, IEA Statistics")
    
    print_header("📋 EMISSION FACTORS REFERENCE")
    print("Transport Mode                 | Emission Factor (kg CO2/km)")
    print("-" * 55)
    
    key_modes = [
        ('car_average', 'Average Car'),
        ('car_electric', 'Electric Car'),
        ('carpool_2', 'Carpool (2 people)'),
        ('bus_local', 'Local Bus'),
        ('train_local', 'Local Train'),
        ('bicycle', 'Bicycle'),
        ('walking', 'Walking'),
        ('work_from_home', 'Work from Home'),
    ]
    
    for mode_key, mode_name in key_modes:
        factor = EMISSION_FACTORS.get(mode_key, 0)
        print(f"{mode_name:<30} | {factor:.3f}")
    
    print_header("🚗 CALCULATION EXAMPLES")
    
    # Example 1: Daily bicycle commute
    print_calculation_example(
        "Daily Bicycle Commute",
        distance=12.0,
        mode='bicycle'
    )
    
    # Example 2: Carpool with colleagues
    print_calculation_example(
        "Carpool with 3 Colleagues",
        distance=25.0,
        mode='carpool',
        passengers=3
    )
    
    # Example 3: Public transport in EU
    print_calculation_example(
        "Train Journey in EU (Clean Grid)",
        distance=30.0,
        mode='train_local',
        region='eu'
    )
    
    # Example 4: Work from home
    print_calculation_example(
        "Work from Home Day",
        distance=0.0,  # Will use avg commute distance
        mode='work_from_home'
    )
    
    # Example 5: Electric car
    print_calculation_example(
        "Electric Car Trip",
        distance=15.0,
        mode='car_electric'
    )
    
    # Example 6: Regular car (baseline)
    print_calculation_example(
        "Regular Car Trip (Baseline)",
        distance=15.0,
        mode='car_average'
    )
    
    print_header("🔬 METHODOLOGY HIGHLIGHTS")
    print("""
    ✅ Based on Latest Scientific Data:
       • DEFRA UK Government GHG Conversion Factors 2024
       • EPA Emission Factors for Greenhouse Gas Inventories
       • IPCC Guidelines for National Greenhouse Gas Inventories
       • IEA Transport CO2 Emissions Statistics
    
    ✅ Comprehensive Approach:
       • Well-to-Wheel emissions (includes fuel production)
       • Regional adjustment factors (cleaner grids get bonuses)
       • Accurate carpooling calculations
       • Lifecycle emissions for electric vehicles
    
    ✅ Conservative & Transparent:
       • Conservative estimates when uncertain
       • Complete audit trail for all calculations
       • Configurable parameters via database
       • Backward compatibility maintained
    
    ✅ Industry Standards Compliance:
       • ISO 14064 (GHG accounting and verification)
       • GHG Protocol (corporate accounting standard)
       • VCS (Verified Carbon Standard)
    """)
    
    print_header("💡 KEY INSIGHTS FROM EXAMPLES")
    
    # Calculate some comparative insights
    car_15km = calculate_trip_emissions(15.0, 'car_average')
    bike_15km = calculate_trip_emissions(15.0, 'bicycle')
    train_15km = calculate_trip_emissions(15.0, 'train_local')
    
    print(f"""
    🚗 15km by car:        {car_15km:.3f} kg CO2
    🚲 15km by bicycle:    {bike_15km:.3f} kg CO2 (saves {car_15km:.3f} kg)
    🚊 15km by train:      {train_15km:.3f} kg CO2 (saves {car_15km - train_15km:.3f} kg)
    
    💰 Credit Earnings (15km trip):
    • Bicycle: {calculate_carbon_credits(15.0, 'bicycle'):.2f} credits
    • Train: {calculate_carbon_credits(15.0, 'train_local'):.2f} credits
    • Carpool (3 people): {calculate_carbon_credits(15.0, 'carpool', passengers=3):.2f} credits
    
    🌱 Annual Impact (daily 15km commute, 250 work days):
    • Cycling saves: {car_15km * 250 * 2:.0f} kg CO2/year ({(car_15km * 250 * 2)/1000:.1f} tons)
    • Train saves: {(car_15km - train_15km) * 250 * 2:.0f} kg CO2/year ({((car_15km - train_15km) * 250 * 2)/1000:.1f} tons)
    """)
    
    print_header("🎯 NEXT STEPS")
    print("""
    1. 🔧 Update System Configuration:
       python manage.py update_emission_factors --force
    
    2. 📊 Test New Calculations:
       • Log some test trips in the system
       • Compare old vs new credit calculations
       • Verify accuracy with manual calculations
    
    3. 🌍 Configure Regional Settings:
       python manage.py update_emission_factors --region eu
    
    4. 📈 Monitor Performance:
       • Check calculation speed
       • Verify database queries
       • Monitor credit generation rates
    
    5. 📚 Review Documentation:
       • Read docs/CARBON_CALCULATION_METHODOLOGY.md
       • Understand all configuration options
       • Plan user communication about changes
    """)
    
    print("\n" + "=" * 60)
    print(" 🎉 Carbon Calculation System Ready!")
    print("=" * 60)

if __name__ == "__main__":
    main()






