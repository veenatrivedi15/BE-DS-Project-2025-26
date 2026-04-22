"""
Management command to update emission factors and carbon calculation parameters.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import SystemConfig
from core.utils.improved_carbon_calculator import EMISSION_FACTORS, REGIONAL_FACTORS


class Command(BaseCommand):
    help = 'Update emission factors and carbon calculation parameters in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing values',
        )
        parser.add_argument(
            '--region',
            type=str,
            default='default',
            help='Set default regional factor',
        )

    def handle(self, *args, **options):
        force_update = options['force']
        default_region = options['region']
        
        self.stdout.write(
            self.style.SUCCESS('Starting emission factors update...')
        )
        
        with transaction.atomic():
            # Update emission factors
            updated_count = 0
            created_count = 0
            
            for mode, factor in EMISSION_FACTORS.items():
                config_name = f'emission_factor_{mode}'
                config, created = SystemConfig.objects.get_or_create(
                    name=config_name,
                    defaults={
                        'value': str(factor),
                        'description': f'CO2 emission factor for {mode} (kg CO2 per km per passenger)',
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'Created: {config_name} = {factor}')
                elif force_update:
                    config.value = str(factor)
                    config.save()
                    updated_count += 1
                    self.stdout.write(f'Updated: {config_name} = {factor}')
            
            # Update regional factors
            for region, factor in REGIONAL_FACTORS.items():
                config_name = f'regional_factor_{region}'
                config, created = SystemConfig.objects.get_or_create(
                    name=config_name,
                    defaults={
                        'value': str(factor),
                        'description': f'Regional adjustment factor for {region}',
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'Created: {config_name} = {factor}')
                elif force_update:
                    config.value = str(factor)
                    config.save()
                    updated_count += 1
                    self.stdout.write(f'Updated: {config_name} = {factor}')
            
            # Set default regional factor
            default_regional_config, created = SystemConfig.objects.get_or_create(
                name='default_regional_factor',
                defaults={
                    'value': default_region,
                    'description': 'Default regional factor to use for calculations',
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created: default_regional_factor = {default_region}')
            elif force_update:
                default_regional_config.value = default_region
                default_regional_config.save()
                updated_count += 1
                self.stdout.write(f'Updated: default_regional_factor = {default_region}')
            
            # Set other important configuration values
            other_configs = [
                ('credits_per_kg_co2', '1.0', 'Number of credits per kg CO2 saved'),
                ('avg_commute_distance', '20.0', 'Average commute distance for work from home calculations (km)'),
                ('baseline_transport_mode', 'car_average', 'Baseline transport mode for credit calculations'),
                ('enable_lifecycle_emissions', 'true', 'Include well-to-wheel emissions in calculations'),
                ('carbon_calculation_version', '2.0', 'Version of carbon calculation methodology'),
            ]
            
            for name, value, description in other_configs:
                config, created = SystemConfig.objects.get_or_create(
                    name=name,
                    defaults={
                        'value': value,
                        'description': description,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'Created: {name} = {value}')
                elif force_update:
                    config.value = value
                    config.save()
                    updated_count += 1
                    self.stdout.write(f'Updated: {name} = {value}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Emission factors update completed!\n'
                f'Created: {created_count} configurations\n'
                f'Updated: {updated_count} configurations'
            )
        )
        
        # Display summary of current emission factors
        self.stdout.write('\n' + self.style.WARNING('Current Emission Factors Summary:'))
        self.stdout.write('=' * 60)
        
        transport_modes = [
            ('car_average', 'Average Car'),
            ('carpool_2', 'Carpool (2 people)'),
            ('bus_local', 'Local Bus'),
            ('train_local', 'Local Train'),
            ('bicycle', 'Bicycle'),
            ('walking', 'Walking'),
            ('work_from_home', 'Work from Home'),
        ]
        
        for mode_key, mode_name in transport_modes:
            factor = EMISSION_FACTORS.get(mode_key, 'N/A')
            self.stdout.write(f'{mode_name:<20}: {factor} kg CO2/km')
        
        self.stdout.write('\n' + self.style.WARNING('Regional Factors:'))
        self.stdout.write('=' * 30)
        
        for region, factor in REGIONAL_FACTORS.items():
            self.stdout.write(f'{region.upper():<10}: {factor}x')
        
        self.stdout.write(
            '\n' + self.style.SUCCESS(
                'Use --force flag to update existing values.\n'
                'Use --region <region> to set default regional factor.'
            )
        )






