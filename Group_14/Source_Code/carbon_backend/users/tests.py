from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import CustomUser, EmployeeProfile, EmployerProfile
from decimal import Decimal

class EmployeeRegistrationTests(TestCase):
    """Test cases for employee registration functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create an approved employer for testing
        self.employer_user = CustomUser.objects.create_user(
            username='employer1',
            email='employer@example.com',
            password='testpass123',
            first_name='Employer',
            last_name='Test',
            is_employer=True,
            approved=True
        )
        
        self.employer = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name='Test Company',
            registration_number='REG123456',
            industry='Technology',
            approved=True
        )
        
        # Create a client for API requests
        self.client = APIClient()
        
    def test_employee_registration_success(self):
        """Test successful employee registration."""
        url = reverse('users:employee_register')
        data = {
            'email': 'employee@example.com',
            'username': 'employee1',
            'password': 'testpass123',
            'first_name': 'Employee',
            'last_name': 'Test',
            'employer_id': self.employer.id,
            'employee_id': 'EMP001',
            'home_address': '123 Test St',
            'home_latitude': Decimal('37.7749'),
            'home_longitude': Decimal('-122.4194')
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CustomUser.objects.filter(email='employee@example.com').exists())
        self.assertTrue(EmployeeProfile.objects.filter(user__email='employee@example.com').exists())
        
    def test_employee_registration_duplicate_email(self):
        """Test employee registration with a duplicate email address."""
        # First create a user (not an employee)
        existing_user = CustomUser.objects.create_user(
            username='existing',
            email='duplicate@example.com',
            password='testpass123',
            first_name='Existing',
            last_name='User'
        )
        
        url = reverse('users:employee_register')
        data = {
            'email': 'duplicate@example.com',  # Same email as existing user
            'username': 'newemployee',  # Different username
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'Employee',
            'employer_id': self.employer.id,
            'employee_id': 'EMP002'
        }
        
        response = self.client.post(url, data, format='json')
        # This should succeed with HTTP 201 CREATED since we're converting an existing user
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that the existing user has been updated with employee role
        existing_user.refresh_from_db()
        self.assertTrue(existing_user.is_employee)
        self.assertTrue(hasattr(existing_user, 'employee_profile'))
        
    def test_employee_registration_duplicate_employer(self):
        """Test employee registration with an email already registered as an employer."""
        url = reverse('users:employee_register')
        data = {
            'email': 'employer@example.com',  # Same as employer email
            'username': 'employerattempt',
            'password': 'testpass123',
            'first_name': 'Employer',
            'last_name': 'Attempt',
            'employer_id': self.employer.id
        }
        
        response = self.client.post(url, data, format='json')
        # This should fail with HTTP 400 BAD REQUEST
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('already registered as an employer', response.data['email'][0])
        
    def test_employee_registration_duplicate_username_different_email(self):
        """Test employee registration with a duplicate username but different email."""
        url = reverse('users:employee_register')
        data = {
            'email': 'newemployee@example.com',
            'username': 'employer1',  # Same as employer username
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'Employee',
            'employer_id': self.employer.id
        }
        
        response = self.client.post(url, data, format='json')
        # This should fail with HTTP 400 BAD REQUEST
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
        self.assertIn('already taken', response.data['username'][0])
