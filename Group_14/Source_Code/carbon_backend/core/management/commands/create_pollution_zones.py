"""
Management command to create sample pollution zones for the map
"""

from django.core.management.base import BaseCommand
from core.pollution_models import IndustrialZone


class Command(BaseCommand):
    help = 'Create sample pollution zones for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample pollution zones...')
        
        # Sample zones around Mumbai
        zones_data = [
            {
                'name': 'Mumbai Industrial Zone',
                'latitude': 19.0760,
                'longitude': 72.8777,
                'zone_type': 'heavy_industry',
                'emission_intensity': 150.5,
                'operating_hours': {'start': '08:00', 'end': '18:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Bandra Manufacturing Area',
                'latitude': 19.0200,
                'longitude': 72.8600,
                'zone_type': 'manufacturing',
                'emission_intensity': 85.2,
                'operating_hours': {'start': '09:00', 'end': '17:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Marine Lines Residential',
                'latitude': 19.1000,
                'longitude': 72.8900,
                'zone_type': 'other',
                'emission_intensity': 25.5,
                'operating_hours': {'start': '08:00', 'end': '18:00', 'days': [1,2,3,4,5]}
            },
            {
                'name': 'Worli Power Plant',
                'latitude': 19.0000,
                'longitude': 72.8200,
                'zone_type': 'power_plant',
                'emission_intensity': 220.8,
                'operating_hours': {'start': '06:00', 'end': '22:00', 'days': [1,2,3,4,5,6]}
            },
            {
                'name': 'Colaba Clean Zone',
                'latitude': 19.0500,
                'longitude': 72.8300,
                'zone_type': 'other',
                'emission_intensity': 15.5,
                'operating_hours': {'start': '09:00', 'end': '17:00', 'days': [1,2,3,4,5]}
            }
        ]
        
        created_count = 0
        for zone_data in zones_data:
            zone, created = IndustrialZone.objects.get_or_create(
                name=zone_data['name'],
                defaults={
                    'latitude': zone_data['latitude'],
                    'longitude': zone_data['longitude'],
                    'radius_km': zone_data.get('radius_km', 5.0),
                    'zone_type': zone_data['zone_type'],
                    'emission_intensity': zone_data.get('emission_intensity', 50.0),
                    'operating_hours': zone_data.get('operating_hours', {'start': '08:00', 'end': '18:00', 'days': [1,2,3,4,5]})
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created zone: {zone_data["name"]}')
            else:
                self.stdout.write(f'  Zone already exists: {zone_data["name"]}')
        
        self.stdout.write(f'\n[SUCCESS] Created {created_count} new pollution zones')
        self.stdout.write('[INFO] Pollution map should now show AQI pins and zones!')
