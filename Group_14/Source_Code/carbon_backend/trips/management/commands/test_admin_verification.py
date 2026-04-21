import os
import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from trips.models import Trip, CarbonCredit
from users.models import EmployeeProfile, EmployerProfile, Location

User = get_user_model()

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class Command(BaseCommand):
    help = 'Test trip verification functionality by admin users'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting admin verification test'))
        
        # Create a test client
        self.client = Client()
        
        # Setup test users and data
        self.setup_test_data()
        
        # Run tests
        self.login_as_employer()
        self.verify_pending_trips()
        self.check_credit_activation()
        
        self.stdout.write(self.style.SUCCESS('All tests completed successfully'))

    def setup_test_data(self):
        """Setup test data including looking up the employer and employee accounts"""
        # Get employer user
        self.employer_email = 'acme@example.com'
        employer_user = User.objects.filter(email=self.employer_email).first()
        
        if not employer_user:
            self.stdout.write(self.style.ERROR(f'No employer found with email {self.employer_email}'))
            raise Exception('Employer user not found')
            
        self.stdout.write(self.style.SUCCESS(f'Found employer user: {employer_user.username}'))
        self.employer_user = employer_user
        
        # Get employee user
        self.employee_email = 'employee@example.com'
        employee_user = User.objects.filter(email=self.employee_email).first()
        
        if not employee_user:
            self.stdout.write(self.style.ERROR(f'No employee found with email {self.employee_email}'))
            raise Exception('Employee user not found')
            
        self.stdout.write(self.style.SUCCESS(f'Found employee user: {employee_user.username}'))
        self.employee_user = employee_user
        
        # Get or create test data for trips
        try:
            self.employee_profile = employee_user.employee_profile
            self.employer_profile = employer_user.employer_profile
        except:
            self.stdout.write(self.style.ERROR('Could not get employee or employer profile'))
            raise Exception('Profile retrieval failed')
        
        # Create a home and office location if they don't exist
        home_location = Location.objects.filter(created_by=employee_user, location_type='home').first()
        if not home_location:
            home_location = Location.objects.create(
                name='Employee Home',
                created_by=employee_user,
                latitude=51.5074,
                longitude=-0.1278,
                address='123 Test Home St, London',
                location_type='home'
            )
            self.stdout.write(self.style.SUCCESS('Created test home location'))
        self.home_location = home_location
        
        office_location = Location.objects.filter(created_by=employer_user, location_type='office').first()
        if not office_location:
            office_location = Location.objects.create(
                name='Office',
                created_by=employer_user,
                latitude=51.5074,
                longitude=-0.1378,
                address='456 Office St, London',
                location_type='office',
                employer=self.employer_profile
            )
            self.stdout.write(self.style.SUCCESS('Created test office location'))
        self.office_location = office_location
        
        # Create a pending trip with proof if it doesn't exist
        pending_trips = Trip.objects.filter(
            employee=self.employee_profile, 
            verification_status='pending',
            proof_image__isnull=False
        )
        
        if not pending_trips.exists():
            # Create a test client and login as employee
            temp_client = Client()
            logged_in = temp_client.login(username=self.employee_email, password='Employee123!')
            
            if not logged_in:
                self.stdout.write(self.style.ERROR('Failed to log in as employee to create test data'))
                raise Exception('Test data setup failed')
            
            # Create a completed trip
            trip = Trip.objects.create(
                employee=self.employee_profile,
                start_location=self.home_location,
                end_location=self.office_location,
                start_time=timezone.now() - timezone.timedelta(hours=2),
                end_time=timezone.now() - timezone.timedelta(hours=1),
                transport_mode='bicycle',
                distance_km=7.5,
                carbon_savings=0.9,
                credits_earned=0.9,
                verification_status='pending',
                proof_image='test_proof.jpg'  # Use dummy filename
            )
            
            # Create pending carbon credit
            CarbonCredit.objects.create(
                amount=0.9,
                source_trip=trip,
                owner_type='employee',
                owner_id=self.employee_profile.id,
                status='pending',
                expiry_date=timezone.now() + timezone.timedelta(days=365)
            )
            
            self.stdout.write(self.style.SUCCESS('Created test pending trip with credits'))
        else:
            self.stdout.write(self.style.SUCCESS('Found existing pending trips for testing'))

    def login_as_employer(self):
        """Log in as employer user who can verify trips"""
        login_successful = self.client.login(username=self.employer_email, password='Employer123!')
        
        if login_successful:
            self.stdout.write(self.style.SUCCESS('Successfully logged in as employer'))
        else:
            self.stdout.write(self.style.ERROR('Failed to log in as employer'))
            raise Exception('Employer login failed')

    def verify_pending_trips(self):
        """Test verifying pending trips"""
        self.stdout.write(self.style.NOTICE('Testing trip verification...'))
        
        # Get pending trips
        pending_trips = Trip.objects.filter(
            employee__employer=self.employer_profile,
            verification_status='pending',
            proof_image__isnull=False
        )
        
        if not pending_trips.exists():
            self.stdout.write(self.style.ERROR('No pending trips found for verification'))
            raise Exception('Test setup failed - no pending trips')
        
        trip_count = pending_trips.count()
        self.stdout.write(self.style.SUCCESS(f'Found {trip_count} pending trips for verification'))
        
        # Verify each trip
        for trip in pending_trips:
            self.stdout.write(self.style.NOTICE(f'Verifying trip ID: {trip.id}...'))
            
            # Prepare verification data
            data = {
                'verification_status': 'verified',
                'verification_notes': 'Verified by automated test'
            }
            
            # Make request to verify trip
            url = reverse('trips:trip_verify', kwargs={'pk': trip.id})
            response = self.client.post(url, data=json.dumps(data, cls=DecimalEncoder), content_type='application/json')
            
            # Check response
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f'Trip ID {trip.id} verified successfully'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to verify trip ID {trip.id}. Status code: {response.status_code}'))
                self.stdout.write(self.style.ERROR(f'Response: {response.content}'))
                raise Exception('Trip verification failed')
            
            # Refresh trip from database and check status
            trip.refresh_from_db()
            if trip.verification_status == 'verified':
                self.stdout.write(self.style.SUCCESS(f'Trip ID {trip.id} status updated to verified'))
            else:
                self.stdout.write(self.style.ERROR(f'Trip ID {trip.id} status not updated. Current status: {trip.verification_status}'))
                raise Exception('Trip status update failed')

    def check_credit_activation(self):
        """Test that carbon credits were activated after verification"""
        self.stdout.write(self.style.NOTICE('Testing credit activation...'))
        
        # Get verified trips
        verified_trips = Trip.objects.filter(
            employee__employer=self.employer_profile,
            verification_status='verified'
        )
        
        if not verified_trips.exists():
            self.stdout.write(self.style.ERROR('No verified trips found'))
            raise Exception('Verification test failed - no verified trips')
        
        for trip in verified_trips:
            self.stdout.write(self.style.NOTICE(f'Checking credits for trip ID: {trip.id}...'))
            
            # Check if carbon credits were activated
            credits = CarbonCredit.objects.filter(source_trip=trip)
            
            if not credits.exists():
                self.stdout.write(self.style.ERROR(f'No carbon credits found for trip ID {trip.id}'))
                continue
            
            active_credits = credits.filter(status='active')
            
            if active_credits.exists():
                self.stdout.write(self.style.SUCCESS(f'Carbon credits for trip ID {trip.id} activated successfully'))
                for credit in active_credits:
                    self.stdout.write(self.style.SUCCESS(f'Credit ID: {credit.id}, Amount: {credit.amount}, Status: {credit.status}'))
            else:
                self.stdout.write(self.style.ERROR(f'Carbon credits for trip ID {trip.id} not activated'))
                for credit in credits:
                    self.stdout.write(self.style.ERROR(f'Credit ID: {credit.id}, Amount: {credit.amount}, Status: {credit.status}'))
                raise Exception('Credit activation failed') 