from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from users.models import EmployeeProfile, Location, EmployerProfile
from .models import Trip, CarbonCredit
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import tempfile
from PIL import Image
import io

User = get_user_model()


class TripModelTestCase(TestCase):
    """Tests for the Trip model."""
    
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username='testemployee',
            email='employee@test.com',
            password='password123',
            is_employee=True
        )
        
        # Create an employer
        self.employer_user = User.objects.create_user(
            username='testemployer',
            email='employer@test.com',
            password='password123',
            is_employer=True
        )
        
        self.employer = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name='Test Company',
            registration_number='12345',
            industry='IT',
            approved=True
        )
        
        # Create an employee
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employer=self.employer,
            approved=True
        )
        
        # Create locations
        self.home_location = Location.objects.create(
            name='Home',
            created_by=self.user,
            latitude=51.5074,
            longitude=-0.1278,
            address='London',
            location_type='home'
        )
        
        self.office_location = Location.objects.create(
            name='Office',
            created_by=self.employer_user,
            latitude=51.5074,
            longitude=-0.1378,
            address='London',
            location_type='office',
            employer=self.employer
        )
        
        # Create a trip
        self.trip = Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            start_time=timezone.now(),
            transport_mode='bicycle'
        )
    
    def test_trip_creation(self):
        """Test that a trip can be created."""
        self.assertEqual(Trip.objects.count(), 1)
        self.assertEqual(self.trip.employee, self.employee)
        self.assertEqual(self.trip.start_location, self.home_location)
        self.assertEqual(self.trip.transport_mode, 'bicycle')
        self.assertIsNone(self.trip.end_time)
        self.assertIsNone(self.trip.end_location)
        self.assertEqual(self.trip.verification_status, 'pending')
    
    def test_trip_end(self):
        """Test that a trip can be ended."""
        self.trip.end_location = self.office_location
        self.trip.end_time = timezone.now() + timedelta(hours=1)
        self.trip.distance_km = Decimal('10.5')
        self.trip.carbon_savings = Decimal('1.26')  # 10.5km * 0.12kg CO2/km (car baseline)
        self.trip.credits_earned = Decimal('1.26')
        self.trip.save()
        
        self.assertEqual(self.trip.distance_km, Decimal('10.5'))
        self.assertEqual(self.trip.carbon_savings, Decimal('1.26'))
        self.assertEqual(self.trip.credits_earned, Decimal('1.26'))
        self.assertIsNotNone(self.trip.end_time)
        self.assertEqual(self.trip.end_location, self.office_location)
    
    def test_trip_duration(self):
        """Test the trip duration property."""
        self.trip.end_time = self.trip.start_time + timedelta(hours=1)
        self.trip.save()
        
        duration = self.trip.duration
        self.assertEqual(duration.seconds, 3600)  # 1 hour = 3600 seconds


class TripAPITestCase(APITestCase):
    """Tests for the Trip API endpoints."""
    
    def setUp(self):
        # Create clients
        self.client = APIClient()
        self.admin_client = APIClient()
        
        # Create a super admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='password123',
            is_super_admin=True,
            is_staff=True,
            is_superuser=True,
            approved=True
        )
        
        # Create an employer user
        self.employer_user = User.objects.create_user(
            username='employer',
            email='employer@test.com',
            password='password123',
            is_employer=True,
            approved=True
        )
        
        self.employer = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name='Test Company',
            registration_number='12345',
            industry='IT',
            approved=True
        )
        
        # Create an employee user
        self.user = User.objects.create_user(
            username='employee',
            email='employee@test.com',
            password='password123',
            is_employee=True,
            approved=True
        )
        
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employer=self.employer,
            approved=True
        )
        
        # Create locations
        self.home_location = Location.objects.create(
            name='Home',
            created_by=self.user,
            latitude=51.5074,
            longitude=-0.1278,
            address='123 Home St, London',
            location_type='home'
        )
        
        self.office_location = Location.objects.create(
            name='Office',
            created_by=self.employer_user,
            latitude=51.5074,
            longitude=-0.1378,
            address='456 Office St, London',
            location_type='office',
            employer=self.employer
        )
        
        # Create a completed trip
        self.completed_trip = Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            end_location=self.office_location,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            transport_mode='bicycle',
            distance_km=Decimal('10.5'),
            carbon_savings=Decimal('1.26'),
            credits_earned=Decimal('1.26'),
            verification_status='pending'
        )
        
        # Create carbon credits for the trip
        self.credit = CarbonCredit.objects.create(
            amount=Decimal('1.26'),
            source_trip=self.completed_trip,
            owner_type='employee',
            owner_id=self.employee.id,
            status='pending',
            expiry_date=timezone.now() + timedelta(days=365)
        )
        
        # Authenticate clients
        self.client.force_authenticate(user=self.user)
        self.admin_client.force_authenticate(user=self.admin_user)
    
    def test_trip_list(self):
        """Test retrieving a list of trips."""
        url = reverse('trips:trip_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_trip_detail(self):
        """Test retrieving trip details."""
        url = reverse('trips:trip_detail', kwargs={'pk': self.completed_trip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.completed_trip.pk)
        self.assertEqual(float(response.data['distance_km']), 10.5)
    
    def test_trip_start(self):
        """Test starting a new trip."""
        url = reverse('trips:trip_start')
        data = {
            'start_location': 'Test Start',
            'start_address': '789 Start St, London',
            'start_latitude': 51.5074,
            'start_longitude': -0.1278,
            'transport_mode': 'bicycle'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Trip.objects.count(), 2)
        self.assertEqual(response.data['transport_mode'], 'bicycle')
    
    def test_trip_end(self):
        """Test ending a trip."""
        # Create a trip that's only started
        trip = Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            start_time=timezone.now() - timedelta(minutes=30),
            transport_mode='bicycle'
        )
        
        url = reverse('trips:trip_end', kwargs={'pk': trip.pk})
        data = {
            'end_location': 'Test End',
            'end_address': '101 End St, London',
            'end_latitude': 51.5074,
            'end_longitude': -0.1380,
            'distance_km': 5.0
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh trip from DB
        trip.refresh_from_db()
        self.assertIsNotNone(trip.end_time)
        self.assertEqual(float(trip.distance_km), 5.0)
        self.assertGreater(float(trip.carbon_savings), 0)
        
        # Check that a carbon credit was created
        self.assertEqual(CarbonCredit.objects.filter(source_trip=trip).count(), 1)
    
    def test_trip_verification(self):
        """Test verifying a trip."""
        # Add proof image to trip
        self.completed_trip.proof_image = 'test.jpg'
        self.completed_trip.save()
        
        url = reverse('trips:trip_verify', kwargs={'pk': self.completed_trip.pk})
        data = {
            'verification_status': 'verified',
            'verification_notes': 'Looks good!'
        }
        
        # Only admins can verify trips
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin verification
        response = self.admin_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh trip from DB
        self.completed_trip.refresh_from_db()
        self.assertEqual(self.completed_trip.verification_status, 'verified')
        
        # Check that carbon credit was activated
        self.credit.refresh_from_db()
        self.assertEqual(self.credit.status, 'active')
    
    def test_trip_stats(self):
        """Test retrieving trip statistics."""
        url = reverse('trips:trip_stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_trips'], 1)
        self.assertEqual(float(response.data['total_distance']), 10.5)
        self.assertEqual(float(response.data['total_carbon_saved']), 1.26)
    
    def test_credit_list(self):
        """Test retrieving active credits."""
        # First verify the trip to activate the credit
        self.completed_trip.proof_image = 'fake/path/to/image.jpg'
        self.completed_trip.save()
        
        url = reverse('trips:trip_verify', kwargs={'pk': self.completed_trip.pk})
        data = {
            'verification_status': 'verified'
        }
        self.admin_client.post(url, data)
        
        # Now check the credits
        self.client.force_authenticate(user=self.user)
        url = reverse('trips:credit_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['amount']), 1.26)
    
    def test_credit_history(self):
        """Test retrieving credit history."""
        self.client.force_authenticate(user=self.user)
        url = reverse('trips:credit_history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_credit_stats(self):
        """Test retrieving credit statistics."""
        self.client.force_authenticate(user=self.user)
        url = reverse('trips:credit_stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['total_credits_earned']), 1.26)
        self.assertEqual(float(response.data['pending_credits']), 1.26)


class TripTestCase(TestCase):
    def setUp(self):
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin_test@example.com',
            password='password123',
            is_super_admin=True
        )
        
        self.employer_user = User.objects.create_user(
            username='employer_test',
            email='employer_test@example.com',
            password='password123',
            is_employer=True
        )
        
        self.employee_user = User.objects.create_user(
            username='employee_test',
            email='employee_test@example.com',
            password='password123',
            is_employee=True
        )
        
        # Create employer profile
        self.employer = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name='Test Company',
            registration_number='12345',
            industry='IT',
            approved=True
        )
        
        # Create employee profile
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user,
            employer=self.employer,
            approved=True
        )
        
        # Create locations
        self.home_location = Location.objects.create(
            name='Home',
            created_by=self.employee_user,
            latitude=51.5074,
            longitude=-0.1278,
            address='London',
            location_type='home'
        )
        
        self.office_location = Location.objects.create(
            name='Office',
            created_by=self.employer_user,
            latitude=51.5074,
            longitude=-0.1378,
            address='London',
            location_type='office',
            employer=self.employer
        )
        
        # Create a trip
        self.trip = Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            start_time=timezone.now(),
            transport_mode='bicycle'
        )
    
    def test_trip_creation(self):
        """Test that a trip can be created."""
        self.assertEqual(Trip.objects.count(), 1)
        self.assertEqual(self.trip.employee, self.employee)
        self.assertEqual(self.trip.start_location, self.home_location)
        self.assertEqual(self.trip.transport_mode, 'bicycle')
        self.assertIsNone(self.trip.end_time)
        self.assertIsNone(self.trip.end_location)
        self.assertEqual(self.trip.verification_status, 'pending')
    
    def test_trip_end(self):
        """Test that a trip can be ended."""
        self.trip.end_location = self.office_location
        self.trip.end_time = timezone.now() + timedelta(hours=1)
        self.trip.distance_km = Decimal('10.5')
        self.trip.carbon_savings = Decimal('1.26')  # 10.5km * 0.12kg CO2/km (car baseline)
        self.trip.credits_earned = Decimal('1.26')
        self.trip.save()
        
        self.assertEqual(self.trip.distance_km, Decimal('10.5'))
        self.assertEqual(self.trip.carbon_savings, Decimal('1.26'))
        self.assertEqual(self.trip.credits_earned, Decimal('1.26'))
        self.assertIsNotNone(self.trip.end_time)
        self.assertEqual(self.trip.end_location, self.office_location)
    
    def test_trip_duration(self):
        """Test the trip duration property."""
        self.trip.end_time = self.trip.start_time + timedelta(hours=1)
        self.trip.save()
        
        duration = self.trip.duration
        self.assertEqual(duration.seconds, 3600)  # 1 hour = 3600 seconds 


class EmployeeTripFeaturesTestCase(TestCase):
    """Tests specifically for employee trip logging features."""
    
    def setUp(self):
        # Create users
        self.employee_user = User.objects.create_user(
            username='employee_feature_test',
            email='employee_feature@example.com',
            password='password123',
            is_employee=True,
            approved=True
        )
        
        self.employer_user = User.objects.create_user(
            username='employer_feature_test',
            email='employer_feature@example.com',
            password='password123',
            is_employer=True,
            approved=True
        )
        
        # Create employer
        self.employer = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name='Feature Test Company',
            registration_number='54321',
            industry='Technology',
            approved=True
        )
        
        # Create employee
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user,
            employer=self.employer,
            approved=True
        )
        
        # Create locations
        self.home_location = Location.objects.create(
            name='Employee Home',
            created_by=self.employee_user,
            latitude=51.5074,
            longitude=-0.1278,
            address='123 Employee Home St, London',
            location_type='home'
        )
        
        self.office_location = Location.objects.create(
            name='Feature Office',
            created_by=self.employer_user,
            latitude=51.5074,
            longitude=-0.1378,
            address='789 Office Feature St, London',
            location_type='office',
            employer=self.employer
        )
        
        # Setup API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.employee_user)
    
    def test_employee_create_trip_log(self):
        """Test that an employee can create a new trip log."""
        url = reverse('trips:trip_start')
        data = {
            'start_location': self.home_location.name,
            'start_address': self.home_location.address,
            'start_latitude': self.home_location.latitude,
            'start_longitude': self.home_location.longitude,
            'transport_mode': 'bicycle'
        }
        
        # Check trip count before
        initial_count = Trip.objects.count()
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check trip was created
        self.assertEqual(Trip.objects.count(), initial_count + 1)
        
        # Check trip details
        trip = Trip.objects.latest('id')
        self.assertEqual(trip.employee, self.employee)
        self.assertEqual(trip.transport_mode, 'bicycle')
        self.assertIsNotNone(trip.start_time)
        self.assertIsNone(trip.end_time)
    
    def test_employee_complete_trip(self):
        """Test that an employee can complete a trip they started."""
        # Create a started trip
        trip = Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            start_time=timezone.now() - timedelta(minutes=30),
            transport_mode='bicycle'
        )
        
        url = reverse('trips:trip_end', kwargs={'pk': trip.pk})
        data = {
            'end_location': self.office_location.name,
            'end_address': self.office_location.address,
            'end_latitude': self.office_location.latitude,
            'end_longitude': self.office_location.longitude,
            'distance_km': 8.5
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh trip from DB
        trip.refresh_from_db()
        self.assertIsNotNone(trip.end_time)
        self.assertEqual(float(trip.distance_km), 8.5)
        
        # Check carbon calculations
        self.assertGreater(float(trip.carbon_savings), 0)
        self.assertGreater(float(trip.credits_earned), 0)
        
        # Check carbon credit was created
        self.assertEqual(CarbonCredit.objects.filter(source_trip=trip).count(), 1)
    
    def test_upload_trip_proof(self):
        """Test that an employee can upload proof for a completed trip."""
        # Create a completed trip
        trip = Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            end_location=self.office_location,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() - timedelta(minutes=30),
            transport_mode='bicycle',
            distance_km=Decimal('5.0'),
            carbon_savings=Decimal('0.6'),
            credits_earned=Decimal('0.6')
        )
        
        # Create a test image
        image = Image.new('RGB', (100, 100), color = 'red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        image_io.name = 'test.jpg'
        
        url = reverse('trips:trip_proof_upload', kwargs={'pk': trip.pk})
        
        # Create multipart data
        data = {'proof_image': image_io}
        
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh trip from DB
        trip.refresh_from_db()
        self.assertIsNotNone(trip.proof_image)
    
    def test_employee_trip_list(self):
        """Test that an employee can see their own trips."""
        # Create multiple trips
        Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            end_location=self.office_location,
            start_time=timezone.now() - timedelta(days=2),
            end_time=timezone.now() - timedelta(days=2) + timedelta(hours=1),
            transport_mode='bicycle',
            distance_km=Decimal('7.0'),
            carbon_savings=Decimal('0.84'),
            credits_earned=Decimal('0.84')
        )
        
        Trip.objects.create(
            employee=self.employee,
            start_location=self.office_location,
            end_location=self.home_location,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() - timedelta(days=1) + timedelta(hours=1),
            transport_mode='bicycle',
            distance_km=Decimal('7.0'),
            carbon_savings=Decimal('0.84'),
            credits_earned=Decimal('0.84')
        )
        
        url = reverse('trips:trip_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_employee_carbon_credit_dashboard(self):
        """Test that an employee can see their carbon credit dashboard."""
        # Create a trip and verified carbon credit
        trip = Trip.objects.create(
            employee=self.employee,
            start_location=self.home_location,
            end_location=self.office_location,
            start_time=timezone.now() - timedelta(days=3),
            end_time=timezone.now() - timedelta(days=3) + timedelta(hours=1),
            transport_mode='bicycle',
            distance_km=Decimal('10.0'),
            carbon_savings=Decimal('1.2'),
            credits_earned=Decimal('1.2'),
            verification_status='verified'
        )
        
        CarbonCredit.objects.create(
            amount=Decimal('1.2'),
            source_trip=trip,
            owner_type='employee',
            owner_id=self.employee.id,
            status='active',
            expiry_date=timezone.now() + timedelta(days=365)
        )
        
        # Test credit stats
        url = reverse('trips:credit_stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['total_credits_earned']), 1.2)
        self.assertEqual(float(response.data['active_credits']), 1.2)
        
        # Test credit list
        url = reverse('trips:credit_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['amount']), 1.2) 