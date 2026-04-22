import decimal
from django.core.management.base import BaseCommand
from users.models import CustomUser, EmployerProfile, Location
from django.db import transaction

class Command(BaseCommand):
    help = 'Creates sample locations for testing'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Get the employee user
                try:
                    employee_user = CustomUser.objects.get(email='employee@example.com')
                    self.stdout.write(self.style.SUCCESS(f'Found employee user: {employee_user.email}'))
                except CustomUser.DoesNotExist:
                    self.stdout.write(self.style.ERROR('Employee user not found. Please create a user with email employee@example.com first.'))
                    return
                
                # Get the employer profile for ACME Corporation
                try:
                    acme = EmployerProfile.objects.get(company_name__icontains='acme')
                    self.stdout.write(self.style.SUCCESS(f'Found employer: {acme.company_name}'))
                except EmployerProfile.DoesNotExist:
                    self.stdout.write(self.style.ERROR('ACME Corporation employer not found.'))
                    return
                
                # Create home location for employee
                home_location = Location(
                    created_by=employee_user,
                    name="Home",
                    latitude=decimal.Decimal('26.3683'),  # Boca Raton coordinates
                    longitude=decimal.Decimal('-80.1289'),
                    address="5535 N Military Trail, Sanmarco Apartments, Boca Raton, FL 33496",
                    location_type='home'
                )
                home_location.save()
                self.stdout.write(self.style.SUCCESS(f'Created home location for {employee_user.email}'))
                
                # Create first office location for ACME
                office_location1 = Location(
                    created_by=acme.user,
                    employer=acme,
                    name="ACME Headquarters",
                    latitude=decimal.Decimal('26.3470'),  # Boca Raton coordinates
                    longitude=decimal.Decimal('-80.0842'),
                    address="6850 Town Harbour Boulevard, Apartment 3310, Boca Raton, FL 33433",
                    location_type='office',
                    is_primary=True
                )
                office_location1.save()
                self.stdout.write(self.style.SUCCESS(f'Created headquarters for {acme.company_name}'))
                
                # Create second office location for ACME
                office_location2 = Location(
                    created_by=acme.user,
                    employer=acme,
                    name="ACME Secondary Office",
                    latitude=decimal.Decimal('26.3468'),  # Boca Raton coordinates
                    longitude=decimal.Decimal('-80.0840'),
                    address="6789 Town Harbor Blvd, Apartment 2124, Boca Raton, FL 33433",
                    location_type='office',
                    is_primary=False
                )
                office_location2.save()
                self.stdout.write(self.style.SUCCESS(f'Created secondary office for {acme.company_name}'))
                
                self.stdout.write(self.style.SUCCESS('All locations created successfully!'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating locations: {str(e)}')) 