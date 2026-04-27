from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
import requests

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from django.utils import timezone

from .models import SystemConfig
from users.models import EmployerProfile, CustomUser
from trips.models import Trip, CarbonCredit
from marketplace.models import MarketplaceTransaction
from users.permissions import IsSuperAdmin, IsBankAdmin, IsApprovedUser

# System Config Views
class SystemConfigListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        """List all system configurations"""
        configs = SystemConfig.objects.all()
        data = [{
            'id': config.id,
            'name': config.name,
            'value': config.value,
            'description': config.description,
            'is_active': config.is_active,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        } for config in configs]
        return Response(data)
    
    def post(self, request):
        """Create a new system configuration"""
        data = request.data
        if not data.get('name') or not data.get('value'):
            return Response(
                {"error": "Name and value are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        config = SystemConfig.objects.create(
            name=data.get('name'),
            value=data.get('value'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True)
        )
        
        return Response({
            'id': config.id,
            'name': config.name,
            'value': config.value,
            'description': config.description,
            'is_active': config.is_active,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        }, status=status.HTTP_201_CREATED)


class SystemConfigDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request, pk):
        """Get a specific system configuration"""
        config = get_object_or_404(SystemConfig, pk=pk)
        return Response({
            'id': config.id,
            'name': config.name,
            'value': config.value,
            'description': config.description,
            'is_active': config.is_active,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        })
    
    def put(self, request, pk):
        """Update a system configuration"""
        config = get_object_or_404(SystemConfig, pk=pk)
        data = request.data
        
        if data.get('name'):
            config.name = data.get('name')
        if data.get('value'):
            config.value = data.get('value')
        if data.get('description'):
            config.description = data.get('description')
        if 'is_active' in data:
            config.is_active = data.get('is_active')
            
        config.save()
        
        return Response({
            'id': config.id,
            'name': config.name,
            'value': config.value,
            'description': config.description,
            'is_active': config.is_active,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        })
    
    def delete(self, request, pk):
        """Delete a system configuration"""
        config = get_object_or_404(SystemConfig, pk=pk)
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Admin-specific Views
class AdminStatsView(APIView):
    permission_classes = [IsAuthenticated, IsBankAdmin]
    
    def get(self, request):
        """Get admin dashboard statistics"""
        # User stats
        total_users = CustomUser.objects.count()
        total_employers = EmployerProfile.objects.count()
        pending_employers = EmployerProfile.objects.filter(approved=False).count()
        
        # Trip stats
        total_trips = Trip.objects.count()
        pending_verification = Trip.objects.filter(verification_status='pending').count()
        total_carbon_saved = Trip.objects.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
        
        # Carbon credit stats
        total_credits = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        active_credits = CarbonCredit.objects.filter(status='active').aggregate(Sum('amount'))['amount__sum'] or 0
        redeemed_credits = CarbonCredit.objects.filter(status='used').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Marketplace stats
        pending_transactions = MarketplaceTransaction.objects.filter(
            status='pending'
        ).count()
        
        stats = {
            'user_stats': {
                'total_users': total_users,
                'total_employers': total_employers,
                'pending_employers': pending_employers,
            },
            'trip_stats': {
                'total_trips': total_trips,
                'pending_verification': pending_verification,
                'total_carbon_saved': total_carbon_saved,
            },
            'credit_stats': {
                'total_credits': total_credits,
                'active_credits': active_credits,
                'redeemed_credits': redeemed_credits,
            },
            'marketplace_stats': {
                'pending_transactions': pending_transactions,
            }
        }
        
        return Response(stats)


class PendingEmployersView(APIView):
    permission_classes = [IsAuthenticated, IsBankAdmin]
    
    def get(self, request):
        """List all pending employer profiles"""
        employers = EmployerProfile.objects.filter(approved=False)
        data = [{
            'id': employer.id,
            'user_id': employer.user.id,
            'company_name': employer.company_name,
            'contact_email': employer.user.email,
            'registration_date': employer.user.date_joined,
        } for employer in employers]
        return Response(data)
    
    def post(self, request):
        """Approve or reject a pending employer"""
        employer_id = request.data.get('employer_id')
        approved = request.data.get('approved', False)
        
        if not employer_id:
            return Response(
                {"error": "Employer ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        employer = get_object_or_404(EmployerProfile, pk=employer_id)
        employer.approved = approved
        employer.save()
        
        # Also update the user's approval status
        user = employer.user
        user.approved = approved
        user.save()
        
        return Response({
            'id': employer.id,
            'company_name': employer.company_name,
            'is_approved': employer.approved
        })


class PendingTransactionsView(APIView):
    permission_classes = [IsAuthenticated, IsBankAdmin]
    
    def get(self, request):
        """List all pending transactions requiring admin approval"""
        transactions = MarketplaceTransaction.objects.filter(
            status='pending',
            admin_approval_required=True
        )
        data = [{
            'id': transaction.id,
            'seller': transaction.seller.company_name,
            'buyer': transaction.buyer.company_name,
            'credit_amount': transaction.credit_amount,
            'total_price': transaction.total_price,
            'created_at': transaction.created_at,
        } for transaction in transactions]
        return Response(data)


class BankAdminCreateView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """Create a new bank admin user"""
        data = request.data
        
        if not data.get('email') or not data.get('password'):
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user with admin privileges
        user = CustomUser.objects.create_user(
            email=data.get('email'),
            password=data.get('password'),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            is_staff=True
        )
        
        return Response({
            'id': user.id,
            'email': user.email,
            'is_staff': user.is_staff
        }, status=status.HTTP_201_CREATED)

class LandingPageView(TemplateView):
    """
    View for the landing page.
    """
    template_name = 'landing.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)

def dashboard_redirect(request):
    """
    Redirect to the appropriate dashboard based on user role
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.user.is_super_admin:
        return redirect('admin_dashboard')
    elif request.user.is_bank_admin:
        return redirect('bank_dashboard')
    elif request.user.is_employer:
        return redirect('employer_dashboard')
    elif request.user.is_employee:
        return redirect('employee_dashboard')
    else:
        # Fallback to employee dashboard if no specific role is set
        return redirect('employee_dashboard')

# Add the new AdminDashboardView
class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        """Get admin dashboard data including stats and recent trips"""
        # Get basic stats
        total_users = CustomUser.objects.count()
        total_trips = Trip.objects.count()
        
        # Carbon credits stats
        total_credits_earned = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        redeemed_credits = CarbonCredit.objects.filter(status='used').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Get recent trips with user details
        limit = int(request.query_params.get('limit', 10))
        recent_trips = Trip.objects.select_related(
            'employee', 'employee__user', 'employee__employer'
        ).order_by('-end_time')[:limit]
        
        trips_data = []
        for trip in recent_trips:
            trips_data.append({
                'id': trip.id,
                'user': {
                    'id': trip.employee.user.id,
                    'name': f"{trip.employee.user.first_name} {trip.employee.user.last_name}",
                    'email': trip.employee.user.email,
                    'employer': trip.employee.employer.company_name if trip.employee.employer else None,
                },
                'start_time': trip.start_time,
                'end_time': trip.end_time,
                'transport_mode': trip.transport_mode,
                'transport_mode_display': trip.get_transport_mode_display(),
                'distance': trip.distance_km,
                'carbon_savings': trip.carbon_savings,
                'credits_earned': trip.credits_earned,
                'start_location': trip.start_location.name if trip.start_location else None,
                'end_location': trip.end_location.name if trip.end_location else None,
                'verification_status': trip.verification_status,
                'has_proof': bool(trip.proof_image),
            })
        
        # Combine all data into a single response
        dashboard_data = {
            'stats': {
                'total_users': total_users,
                'total_trips': total_trips,
                'total_credits_earned': total_credits_earned,
                'credits_redeemed': redeemed_credits,
            },
            'recent_trips': trips_data
        }
        
        return Response(dashboard_data)
