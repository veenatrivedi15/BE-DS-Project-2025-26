#!/usr/bin/env python
"""
Script to update all existing employee home locations and employer office locations
with predefined coordinates for Boca Raton and Florida Atlantic University.
"""

import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

# Import models after Django setup
from users.models import CustomUser, EmployeeProfile, EmployerProfile, Location
from decimal import Decimal
from django.db import transaction

# Define exact coordinates
BOCA_RATON_COORDS = {
    'latitude': Decimal('26.351915'),
    'longitude': Decimal('-80.138568'),
    'address': 'Boca Raton, Florida, USA',
    'name': 'Home - Boca Raton'
}

FAU_COORDS = {
    'latitude': Decimal('26.368322'),
    'longitude': Decimal('-80.097404'),
    'address': 'Florida Atlantic University, 777 Glades Rd, Boca Raton, FL 33431, USA',
    'name': 'Office - Florida Atlantic University'
}

def update_employee_home_locations():
    """Update all employees' home locations with the Boca Raton coordinates."""
    print("Updating employee home locations...")
    
    # Get all employees
    employees = EmployeeProfile.objects.all()
    count = 0
    
    for employee in employees:
        with transaction.atomic():
            # Check if employee has a user
            if not employee.user:
                print(f"  Warning: Employee ID {employee.id} has no user account")
                continue
                
            # Get or create home location
            home_location = Location.objects.filter(
                created_by=employee.user,
                location_type='home'
            ).first()
            
            if home_location:
                # Update existing home location
                home_location.latitude = BOCA_RATON_COORDS['latitude']
                home_location.longitude = BOCA_RATON_COORDS['longitude']
                home_location.address = BOCA_RATON_COORDS['address']
                home_location.name = BOCA_RATON_COORDS['name']
                home_location.is_primary = True
                home_location.save()
                print(f"  Updated home location for employee: {employee.user.email}")
            else:
                # Create new home location
                Location.objects.create(
                    created_by=employee.user,
                    location_type='home',
                    latitude=BOCA_RATON_COORDS['latitude'],
                    longitude=BOCA_RATON_COORDS['longitude'],
                    address=BOCA_RATON_COORDS['address'],
                    name=BOCA_RATON_COORDS['name'],
                    is_primary=True
                )
                print(f"  Created new home location for employee: {employee.user.email}")
            
            count += 1
    
    print(f"Updated {count} employee home locations")

def update_employer_office_locations():
    """Update all employers' office locations with the FAU coordinates."""
    print("Updating employer office locations...")
    
    # Get all employers
    employers = EmployerProfile.objects.all()
    count = 0
    
    for employer in employers:
        with transaction.atomic():
            # Check if employer has a user
            if not employer.user:
                print(f"  Warning: Employer ID {employer.id} has no user account")
                continue
            
            # Check if employer already has any office locations
            existing_offices = Location.objects.filter(
                employer=employer,
                location_type='office'
            )
            
            if existing_offices.exists():
                # Update primary office location
                primary_office = existing_offices.filter(is_primary=True).first()
                if primary_office:
                    office_to_update = primary_office
                else:
                    office_to_update = existing_offices.first()
                
                # Update existing office
                office_to_update.latitude = FAU_COORDS['latitude']
                office_to_update.longitude = FAU_COORDS['longitude']
                office_to_update.address = FAU_COORDS['address']
                office_to_update.name = FAU_COORDS['name']
                office_to_update.is_primary = True
                office_to_update.save()
                print(f"  Updated office location for employer: {employer.company_name}")
            else:
                # Create new office location
                Location.objects.create(
                    created_by=employer.user,
                    location_type='office',
                    latitude=FAU_COORDS['latitude'],
                    longitude=FAU_COORDS['longitude'],
                    address=FAU_COORDS['address'],
                    name=FAU_COORDS['name'],
                    is_primary=True,
                    employer=employer
                )
                print(f"  Created new office location for employer: {employer.company_name}")
            
            count += 1
    
    print(f"Updated {count} employer office locations")

if __name__ == "__main__":
    print("Starting location update script...")
    update_employee_home_locations()
    update_employer_office_locations()
    print("Location update completed!") 