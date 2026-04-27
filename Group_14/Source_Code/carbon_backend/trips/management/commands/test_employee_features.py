import os
import requests
import json
import random
import datetime
from decimal import Decimal
from PIL import Image
import io
import base64
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client, TestCase, override_settings
from trips.models import Trip, CarbonCredit
from users.models import EmployeeProfile, EmployerProfile, Location
from django.conf import settings
from django.db import models

User = get_user_model()

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class Command(BaseCommand):
    help = 'Test employee trip features using direct interaction with the trip data model'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting employee features test'))
        
        # Set up test data
        self.setup_test_data()

        # Run tests
        self.test_create_trip()
        self.test_end_trip()
        self.test_upload_proof()
        self.test_trip_stats()
        
        self.stdout.write(self.style.SUCCESS('All tests completed successfully'))

    def setup_test_data(self):
        """Set up test data for the trip creation tests"""
        # Find employee with credentials
        self.email = 'employee@example.com'  
        employee_user = User.objects.filter(email=self.email).first()
        
        if not employee_user:
            self.stdout.write(self.style.ERROR(f'No user found with email {self.email}'))
            raise Exception('Employee user not found')
        
        self.stdout.write(self.style.SUCCESS(f'Found employee user: {employee_user.username}'))
        
        # Get employee profile
        try:
            self.employee_profile = employee_user.employee_profile
            self.employer = self.employee_profile.employer
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting employee profile: {str(e)}'))
            raise Exception('Employee profile not found')
        
        # Find or create home location
        self.home_location = Location.objects.filter(created_by=employee_user, location_type='home').first()
        if not self.home_location:
            self.home_location = Location.objects.create(
                name='Home Location',
                created_by=employee_user,
                latitude=51.5074,
                longitude=-0.1278,
                address='123 Home St, London',
                location_type='home'
            )
            self.stdout.write(self.style.SUCCESS('Created home location'))
        
        # Find or create office location
        self.office_location = Location.objects.filter(
            employer=self.employer, 
            location_type='office'
        ).first()
        
        if not self.office_location:
            self.office_location = Location.objects.create(
                name='Office Location',
                created_by=self.employer.user,
                latitude=51.5074,
                longitude=-0.1378,
                address='456 Office St, London',
                location_type='office',
                employer=self.employer
            )
            self.stdout.write(self.style.SUCCESS('Created office location'))
        
        self.employee_user = employee_user

    def test_create_trip(self):
        """Test creating a new trip directly using the model"""
        self.stdout.write(self.style.NOTICE('Testing trip creation...'))
        
        # Count initial trips
        initial_count = Trip.objects.filter(employee=self.employee_profile).count()
        
        # Create a new trip
        trip = Trip.objects.create(
            employee=self.employee_profile,
            start_location=self.home_location,
            start_time=timezone.now(),
            transport_mode='bicycle'
        )
        
        # Check if the trip was created
        new_count = Trip.objects.filter(employee=self.employee_profile).count()
        if new_count > initial_count:
            self.stdout.write(self.style.SUCCESS('Trip created successfully'))
            self.stdout.write(self.style.SUCCESS(f'Trip ID: {trip.id}'))
            self.trip = trip
        else:
            self.stdout.write(self.style.ERROR('Failed to create trip'))
            raise Exception('Trip creation failed')
    
    def test_end_trip(self):
        """Test ending a trip by updating the model directly"""
        self.stdout.write(self.style.NOTICE(f'Testing ending trip {self.trip.id}...'))
        
        # Update the trip with end details
        self.trip.end_location = self.office_location
        self.trip.end_time = timezone.now() + timezone.timedelta(minutes=30)
        self.trip.distance_km = Decimal('8.5')
        
        # Calculate carbon savings based on mode and distance
        transport_mode = self.trip.transport_mode
        distance_km = float(self.trip.distance_km)
        
        # Basic carbon calculation (simplified version)
        if transport_mode == 'bicycle':
            carbon_saved = distance_km * 0.12  # Assuming 0.12 kg CO2 saved per km vs car
        elif transport_mode == 'public_transport':
            carbon_saved = distance_km * 0.08  # Assuming 0.08 kg CO2 saved per km vs car
        elif transport_mode == 'walking':
            carbon_saved = distance_km * 0.12  # Assuming 0.12 kg CO2 saved per km vs car
        else:
            carbon_saved = 0
        
        self.trip.carbon_savings = Decimal(str(carbon_saved))
        self.trip.credits_earned = Decimal(str(carbon_saved))  # 1:1 ratio for simplicity
        self.trip.save()
        
        # Create carbon credit
        credit = CarbonCredit.objects.create(
            amount=self.trip.credits_earned,
            source_trip=self.trip,
            owner_type='employee',
            owner_id=self.employee_profile.id,
            status='pending',
            expiry_date=timezone.now() + timezone.timedelta(days=365)
        )
        
        # Check if trip was updated successfully
        self.trip.refresh_from_db()
        if self.trip.end_time and self.trip.end_location:
            self.stdout.write(self.style.SUCCESS('Trip ended successfully'))
            self.stdout.write(self.style.SUCCESS(
                f'Trip stats: Distance: {self.trip.distance_km}km, '
                f'Carbon saved: {self.trip.carbon_savings}kg, '
                f'Credits earned: {self.trip.credits_earned}'
            ))
        else:
            self.stdout.write(self.style.ERROR('Failed to end trip'))
            raise Exception('Trip ending failed')
    
    def test_upload_proof(self):
        """Test uploading proof for a trip"""
        self.stdout.write(self.style.NOTICE(f'Testing uploading proof for trip {self.trip.id}...'))
        
        # Simulate proof image (just setting a filename in this case)
        self.trip.proof_image = 'test_proof.jpg'
        self.trip.save()
        
        # Check if trip was updated with proof
        self.trip.refresh_from_db()
        if self.trip.proof_image:
            self.stdout.write(self.style.SUCCESS('Trip proof uploaded successfully'))
        else:
            self.stdout.write(self.style.ERROR('Failed to upload trip proof'))
            raise Exception('Trip proof upload failed')
    
    def test_trip_stats(self):
        """Test retrieving trip statistics and carbon credit calculation"""
        self.stdout.write(self.style.NOTICE('Testing trip statistics...'))
        
        # Get trip statistics for this employee
        trips = Trip.objects.filter(employee=self.employee_profile)
        
        total_trips = trips.count()
        total_distance = sum([float(trip.distance_km or 0) for trip in trips])
        total_carbon_saved = sum([float(trip.carbon_savings or 0) for trip in trips])
        total_credits_earned = sum([float(trip.credits_earned or 0) for trip in trips])
        
        self.stdout.write(self.style.SUCCESS(f'Trip statistics retrieved successfully'))
        self.stdout.write(self.style.SUCCESS(f'Total trips: {total_trips}'))
        self.stdout.write(self.style.SUCCESS(f'Total distance: {total_distance}km'))
        self.stdout.write(self.style.SUCCESS(f'Total carbon saved: {total_carbon_saved}kg'))
        self.stdout.write(self.style.SUCCESS(f'Total credits earned: {total_credits_earned}'))
        
        # Get carbon credit statistics
        pending_credits = CarbonCredit.objects.filter(
            owner_type='employee',
            owner_id=self.employee_profile.id,
            status='pending'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        active_credits = CarbonCredit.objects.filter(
            owner_type='employee',
            owner_id=self.employee_profile.id,
            status='active'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        self.stdout.write(self.style.SUCCESS(f'Carbon credit statistics retrieved successfully'))
        self.stdout.write(self.style.SUCCESS(f'Pending credits: {pending_credits}'))
        self.stdout.write(self.style.SUCCESS(f'Active credits: {active_credits}')) 