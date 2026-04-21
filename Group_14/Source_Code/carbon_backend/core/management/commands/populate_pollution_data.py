"""
Management command to populate initial industrial zones and environmental metrics
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from core.pollution_models import IndustrialZone, EnvironmentalMetric


class Command(BaseCommand):
    help = 'Populate initial industrial zones and environmental metrics for India'

    def handle(self, *args, **options):
        self.stdout.write('Creating initial industrial zones...')
        
        # Major industrial zones in India (approximate coordinates)
        industrial_zones = [
            {
                'name': 'Mumbai Industrial Belt',
                'zone_type': 'heavy_industry',
                'latitude': Decimal('19.0760'),
                'longitude': Decimal('72.8777'),
                'radius_km': Decimal('15.0'),
                'emission_intensity': Decimal('5000.0'),
                'operating_hours': {'start': '08:00', 'end': '20:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Delhi NCR Industrial Area',
                'zone_type': 'manufacturing',
                'latitude': Decimal('28.7041'),
                'longitude': Decimal('77.1025'),
                'radius_km': Decimal('20.0'),
                'emission_intensity': Decimal('4500.0'),
                'operating_hours': {'start': '09:00', 'end': '19:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Bangalore Electronics City',
                'zone_type': 'manufacturing',
                'latitude': Decimal('12.8442'),
                'longitude': Decimal('77.6781'),
                'radius_km': Decimal('10.0'),
                'emission_intensity': Decimal('2000.0'),
                'operating_hours': {'start': '09:00', 'end': '18:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Chennai Industrial Corridor',
                'zone_type': 'heavy_industry',
                'latitude': Decimal('13.0827'),
                'longitude': Decimal('80.2707'),
                'radius_km': Decimal('25.0'),
                'emission_intensity': Decimal('6000.0'),
                'operating_hours': {'start': '08:00', 'end': '21:00', 'days': [1,2,3,4,5,6]}
            },
            {
                'name': 'Kolkata Industrial Region',
                'zone_type': 'manufacturing',
                'latitude': Decimal('22.5726'),
                'longitude': Decimal('88.3639'),
                'radius_km': Decimal('18.0'),
                'emission_intensity': Decimal('4000.0'),
                'operating_hours': {'start': '08:00', 'end': '20:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Pune Manufacturing Hub',
                'zone_type': 'manufacturing',
                'latitude': Decimal('18.5204'),
                'longitude': Decimal('73.8567'),
                'radius_km': Decimal('12.0'),
                'emission_intensity': Decimal('3000.0'),
                'operating_hours': {'start': '09:00', 'end': '18:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Ahmedabad Industrial Zone',
                'zone_type': 'textile',
                'latitude': Decimal('23.0225'),
                'longitude': Decimal('72.5714'),
                'radius_km': Decimal('15.0'),
                'emission_intensity': Decimal('2500.0'),
                'operating_hours': {'start': '08:00', 'end': '19:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Hyderabad Pharma Hub',
                'zone_type': 'chemical',
                'latitude': Decimal('17.3850'),
                'longitude': Decimal('78.4867'),
                'radius_km': Decimal('10.0'),
                'emission_intensity': Decimal('3500.0'),
                'operating_hours': {'start': '09:00', 'end': '18:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Surat Diamond & Textile',
                'zone_type': 'textile',
                'latitude': Decimal('21.1702'),
                'longitude': Decimal('72.8311'),
                'radius_km': Decimal('12.0'),
                'emission_intensity': Decimal('2200.0'),
                'operating_hours': {'start': '08:00', 'end': '20:00', 'days': [1,2,3,4,5,6]}
            },
            {
                'name': 'Jaipur Manufacturing',
                'zone_type': 'manufacturing',
                'latitude': Decimal('26.9124'),
                'longitude': Decimal('75.7873'),
                'radius_km': Decimal('8.0'),
                'emission_intensity': Decimal('1800.0'),
                'operating_hours': {'start': '09:00', 'end': '18:00', 'days': [1,2,3,4,5]}
            }
        ]
        
        created_zones = 0
        for zone_data in industrial_zones:
            zone, created = IndustrialZone.objects.get_or_create(
                name=zone_data['name'],
                defaults=zone_data
            )
            if created:
                created_zones += 1
                self.stdout.write(f'Created industrial zone: {zone.name}')
            else:
                self.stdout.write(f'Industrial zone already exists: {zone.name}')
        
        self.stdout.write(f'Created {created_zones} new industrial zones')
        
        self.stdout.write('\nCreating environmental metrics...')
        
        # Environmental conversion metrics
        metrics = [
            {
                'metric_name': 'Tree Absorption (per year)',
                'co2_kg_per_unit': Decimal('21.77'),
                'description': 'Amount of CO2 absorbed by one tree per year (IPCC 2006)',
                'source': 'IPCC 2006 Guidelines'
            },
            {
                'metric_name': 'Car Emissions (per day)',
                'co2_kg_per_unit': Decimal('4.6'),
                'description': 'Average CO2 emissions from a passenger car per day',
                'source': 'Indian Automotive Research Institute'
            },
            {
                'metric_name': 'Factory Emissions (per hour)',
                'co2_kg_per_unit': Decimal('1000.0'),
                'description': 'Medium-sized factory CO2 emissions per hour of operation',
                'source': 'Central Pollution Control Board India'
            },
            {
                'metric_name': 'Motorbike Emissions (per day)',
                'co2_kg_per_unit': Decimal('2.3'),
                'description': 'Average CO2 emissions from a motorbike per day',
                'source': 'Indian Automotive Research Institute'
            },
            {
                'metric_name': 'Bus Emissions (per km)',
                'co2_kg_per_unit': Decimal('0.8'),
                'description': 'CO2 emissions from a city bus per kilometer',
                'source': 'WRI India 2015'
            },
            {
                'metric_name': 'Electricity Emissions (per kWh)',
                'co2_kg_per_unit': Decimal('0.82'),
                'description': 'CO2 emissions from electricity generation per kWh (India grid mix)',
                'source': 'Central Electricity Authority India'
            }
        ]
        
        created_metrics = 0
        for metric_data in metrics:
            metric, created = EnvironmentalMetric.objects.get_or_create(
                metric_name=metric_data['metric_name'],
                defaults=metric_data
            )
            if created:
                created_metrics += 1
                self.stdout.write(f'Created metric: {metric.metric_name}')
            else:
                self.stdout.write(f'Metric already exists: {metric.metric_name}')
        
        self.stdout.write(f'Created {created_metrics} new environmental metrics')
        self.stdout.write(self.style.SUCCESS('Initial data population completed successfully!'))
