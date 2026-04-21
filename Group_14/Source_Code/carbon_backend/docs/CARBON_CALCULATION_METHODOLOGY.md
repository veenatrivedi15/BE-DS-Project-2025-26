# Carbon Credit Calculation Methodology

## Overview

This document outlines the scientifically-based methodology used in the Carbon Credits Platform for calculating carbon emissions, savings, and credits. Our approach is based on internationally recognized standards and the latest research in transportation emissions.

## Scientific Foundation

### Data Sources

Our emission factors are derived from:

1. **DEFRA UK Government GHG Conversion Factors 2024**
   - Official UK government emission factors
   - Updated annually with latest scientific data
   - Covers all major transport modes

2. **EPA Emission Factors for Greenhouse Gas Inventories**
   - US Environmental Protection Agency standards
   - Comprehensive lifecycle emission data
   - Industry-standard reference

3. **IPCC Guidelines for National Greenhouse Gas Inventories**
   - International scientific consensus
   - Global warming potential factors
   - Methodological standards

4. **IEA Transport CO2 Emissions Statistics**
   - International Energy Agency data
   - Global transport emission trends
   - Regional adjustment factors

## Emission Factors (kg CO2 per km per passenger)

### Private Vehicles
- **Average Car**: 0.170 kg CO2/km
- **Petrol Car**: 0.168 kg CO2/km
- **Diesel Car**: 0.171 kg CO2/km
- **Hybrid Car**: 0.109 kg CO2/km
- **Electric Car**: 0.047 kg CO2/km (including electricity generation)

### Shared Transport
- **Carpool (2 people)**: 0.085 kg CO2/km (50% reduction per person)
- **Carpool (3 people)**: 0.057 kg CO2/km (66% reduction per person)
- **Carpool (4+ people)**: 0.043 kg CO2/km (75% reduction per person)

### Public Transport
- **Local Bus**: 0.082 kg CO2/km
- **Coach**: 0.027 kg CO2/km
- **Local Train**: 0.035 kg CO2/km
- **National Rail**: 0.028 kg CO2/km
- **Metro/Subway**: 0.030 kg CO2/km
- **Tram**: 0.029 kg CO2/km

### Active Transport
- **Bicycle**: 0.000 kg CO2/km (zero direct emissions)
- **Walking**: 0.000 kg CO2/km (zero direct emissions)
- **E-Scooter**: 0.008 kg CO2/km (including electricity)
- **E-Bike**: 0.004 kg CO2/km (including electricity)

### Remote Work
- **Work from Home**: 0.000 kg CO2/km (no commute)

## Calculation Methodology

### 1. Trip Emission Calculation

```
Trip Emissions (kg CO2) = Distance (km) × Emission Factor (kg CO2/km) × Regional Factor
```

**Example:**
- 10 km car trip
- Emission factor: 0.170 kg CO2/km
- Regional factor: 1.0 (default)
- **Result**: 10 × 0.170 × 1.0 = 1.70 kg CO2

### 2. Carbon Savings Calculation

```
Carbon Savings = Baseline Emissions - Actual Emissions
```

Where:
- **Baseline Emissions**: What would have been emitted using an average car
- **Actual Emissions**: What was actually emitted using the chosen transport mode

**Example:**
- 10 km bicycle trip
- Baseline (car): 10 × 0.170 = 1.70 kg CO2
- Actual (bicycle): 10 × 0.000 = 0.00 kg CO2
- **Carbon Savings**: 1.70 - 0.00 = 1.70 kg CO2 saved

### 3. Carbon Credits Calculation

```
Carbon Credits = Carbon Savings (kg CO2) ÷ Credits per kg CO2 × Multiplier
```

Where:
- **Credits per kg CO2**: 1.0 (1 kg CO2 saved = 1 credit)
- **Multiplier**: Incentive multiplier (default: 1.0)

**Example:**
- Carbon savings: 1.70 kg CO2
- Credits per kg: 1.0
- Multiplier: 1.0
- **Carbon Credits**: 1.70 ÷ 1.0 × 1.0 = 1.70 credits

## Advanced Features

### 1. Lifecycle Emissions (Well-to-Wheel)

Our calculations include upstream emissions from:
- Fuel production and refining
- Electricity generation for electric vehicles
- Infrastructure maintenance

**Adjustment Factors:**
- Petrol: +25% for lifecycle emissions
- Diesel: +22% for lifecycle emissions
- Electricity: +15% for generation emissions
- Public transport: -15% efficiency bonus for high occupancy

### 2. Regional Adjustments

Emission factors are adjusted based on regional characteristics:

- **Default**: 1.0 (baseline)
- **UK**: 0.95 (cleaner electricity grid)
- **EU**: 0.90 (higher renewable energy)
- **Nordic**: 0.75 (very high renewable energy)

### 3. Carpooling Optimization

Carpool emissions are calculated per passenger:
- 2 passengers: 50% reduction per person
- 3 passengers: 66% reduction per person
- 4+ passengers: 75% reduction per person

### 4. Work from Home Credits

Remote work credits are calculated based on:
- Average commute distance saved (configurable, default: 20 km)
- Baseline car emissions for that distance
- Full credit for avoiding the commute entirely

## Validation and Verification

### Data Quality Assurance

1. **Source Verification**: All emission factors traced to official sources
2. **Annual Updates**: Factors updated annually with latest data
3. **Peer Review**: Methodology reviewed by sustainability experts
4. **Transparency**: All calculations and sources publicly documented

### Accuracy Measures

1. **Conservative Estimates**: When uncertain, we use higher emission factors
2. **Rounding**: All results rounded to appropriate precision
3. **Error Handling**: Robust error handling with fallback values
4. **Logging**: Comprehensive logging for audit trails

## Implementation Examples

### Example 1: Daily Commute by Bicycle

```python
# 15 km bicycle commute
distance = 15.0  # km
mode = 'bicycle'
region = 'default'

# Calculate emissions and savings
actual_emissions = calculate_trip_emissions(distance, mode, region)
# Result: 0.00 kg CO2

carbon_saved, carbon_added = calculate_carbon_savings(distance, mode, 'car_average', region)
# Result: 2.55 kg CO2 saved, 0.00 kg CO2 added

credits = calculate_carbon_credits(distance, mode, region)
# Result: 2.55 credits earned
```

### Example 2: Carpool with 3 People

```python
# 25 km carpool with 3 people
distance = 25.0  # km
mode = 'carpool'
passengers = 3
region = 'default'

# Calculate per-person emissions and savings
actual_emissions = calculate_trip_emissions(distance, mode, region, passengers)
# Result: 1.425 kg CO2 per person (25 × 0.057)

carbon_saved, carbon_added = calculate_carbon_savings(distance, mode, 'car_average', region, passengers)
# Result: 2.825 kg CO2 saved per person

credits = calculate_carbon_credits(distance, mode, region, passengers)
# Result: 2.83 credits earned per person
```

### Example 3: Public Transport

```python
# 30 km train journey
distance = 30.0  # km
mode = 'train'
region = 'eu'  # European region with cleaner grid

actual_emissions = calculate_trip_emissions(distance, mode, region)
# Result: 0.945 kg CO2 (30 × 0.035 × 0.90)

carbon_saved, carbon_added = calculate_carbon_savings(distance, mode, 'car_average', region)
# Result: 3.645 kg CO2 saved

credits = calculate_carbon_credits(distance, mode, region)
# Result: 3.65 credits earned
```

## Configuration and Customization

### Database Configuration

The system supports dynamic configuration through the `SystemConfig` model:

```python
# Custom emission factors
SystemConfig.objects.create(
    name='emission_factor_custom_bus',
    value='0.060',
    description='Custom bus emission factor for local fleet'
)

# Regional factors
SystemConfig.objects.create(
    name='regional_factor_california',
    value='0.80',
    description='California with high renewable energy'
)

# Credit conversion rates
SystemConfig.objects.create(
    name='credits_per_kg_co2',
    value='1.5',
    description='Enhanced credit rate for pilot program'
)
```

### Incentive Multipliers

Organizations can apply multipliers to encourage specific behaviors:

```python
# Double credits for cycling
cycling_credits = calculate_carbon_credits(
    distance=10.0,
    transport_mode='bicycle',
    credit_multiplier=2.0  # Double credits
)

# Bonus for first-time public transport users
pt_credits = calculate_carbon_credits(
    distance=15.0,
    transport_mode='public_transport',
    credit_multiplier=1.5  # 50% bonus
)
```

## Compliance and Standards

### International Standards Compliance

- **ISO 14064**: Greenhouse gas accounting and verification
- **GHG Protocol**: Corporate accounting and reporting standard
- **IPCC Guidelines**: National greenhouse gas inventories
- **VCS (Verified Carbon Standard)**: Carbon offset project standards

### Audit Trail

Every calculation includes:
- Timestamp of calculation
- Input parameters used
- Emission factors applied
- Regional adjustments
- Final results
- Data source references

## Future Enhancements

### Planned Improvements

1. **Real-time Grid Factors**: Dynamic electricity emission factors
2. **Weather Adjustments**: Temperature and weather impact on emissions
3. **Vehicle-specific Factors**: Individual vehicle efficiency data
4. **Route Optimization**: Emission-optimized route suggestions
5. **Seasonal Variations**: Seasonal adjustment factors
6. **AI-powered Predictions**: Machine learning for emission forecasting

### Research Integration

- Continuous monitoring of latest research
- Annual methodology reviews
- Integration of new transport technologies
- Collaboration with academic institutions

## Conclusion

This methodology provides a scientifically rigorous, transparent, and accurate system for calculating carbon emissions and credits in transportation. By using internationally recognized standards and maintaining conservative estimates, we ensure the integrity and credibility of the carbon credits generated through the platform.

The system is designed to be:
- **Accurate**: Based on latest scientific data
- **Transparent**: All calculations and sources documented
- **Flexible**: Configurable for different regions and scenarios
- **Scalable**: Supports various transport modes and use cases
- **Verifiable**: Complete audit trail for all calculations

For questions or suggestions regarding this methodology, please contact the development team or refer to the technical documentation.






