from django.shortcuts import render

# Create your views here.

from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Trip, CarbonCredit
from users.models import EmployeeProfile, Location
from .serializers import (
    TripSerializer, TripStartSerializer, TripEndSerializer, 
    TripVerificationSerializer, CarbonCreditSerializer,
    CreditStatsSerializer, EmployerCreditStatsSerializer, TripStatsSerializer
)
from django.contrib.auth import get_user_model
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from users.permissions import IsApprovedUser, IsBankAdmin
from .permissions import IsOwnerOrAdmin, IsEmployerOrAdmin, IsEmployeeOrEmployerOrAdmin, IsCreditOwnerOrAdmin
from .utils import calculate_carbon_savings

User = get_user_model()

# Trip Views
class TripListView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployeeOrEmployerOrAdmin]
    
    def get(self, request):
        user = self.request.user
        
        if user.is_super_admin or user.is_bank_admin:
            # Admins can see all trips
            trips = Trip.objects.all().order_by('-start_time')
        elif user.is_employer:
            # Employers can see their employees' trips
            employer_profile = user.employer_profile
            trips = Trip.objects.filter(
                employee__employer=employer_profile
            ).order_by('-start_time')
        else:
            # Employees can see their own trips
            employee = EmployeeProfile.objects.get(user=user)
            trips = Trip.objects.filter(employee=employee).order_by('-start_time')
            
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

class TripDetailView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsOwnerOrAdmin]
    
    def get(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        
        # Permission check
        self.check_object_permissions(request, trip)
            
        serializer = TripSerializer(trip)
        return Response(serializer.data)

class TripStartView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser]
    
    def post(self, request):
        # Only employees can start trips
        if not request.user.is_employee:
            return Response(
                {"detail": "Only employees can start trips."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        employee = EmployeeProfile.objects.get(user=request.user)
        serializer = TripStartSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        # Get or create location
        start_location, created = Location.objects.get_or_create(
            name=serializer.validated_data['start_location'],
            defaults={
                'address': serializer.validated_data.get('start_address', ''),
                'created_by': request.user,
                'location_type': 'commute',
                'latitude': serializer.validated_data.get('start_latitude', 0),
                'longitude': serializer.validated_data.get('start_longitude', 0)
            }
        )
            
        trip = Trip.objects.create(
            employee=employee,
            start_location=start_location,
            transport_mode=serializer.validated_data['transport_mode'],
            start_time=timezone.now(),
            verification_status='pending'
        )
        
        trip_serializer = TripSerializer(trip)
        return Response(trip_serializer.data, status=status.HTTP_201_CREATED)

class TripEndView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsOwnerOrAdmin]
    
    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        
        # Permission check
        self.check_object_permissions(request, trip)
        
        # Only employees can end their own trips
        if not request.user.is_employee or not hasattr(request.user, 'employee_profile') or trip.employee != request.user.employee_profile:
            return Response(
                {"detail": "You can only end your own trips."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if trip.end_time:
            return Response({"error": "Trip already ended"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Pass the trip in the context for distance calculation
        serializer = TripEndSerializer(data=request.data, context={'trip': trip})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create location
        end_location, created = Location.objects.get_or_create(
            name=serializer.validated_data['end_location'],
            defaults={
                'address': serializer.validated_data.get('end_address', ''),
                'created_by': request.user,
                'location_type': 'commute',
                'latitude': serializer.validated_data.get('end_latitude', 0),
                'longitude': serializer.validated_data.get('end_longitude', 0)
            }
        )
        
        # Get distance from serializer
        distance = float(serializer.validated_data['distance_km'])
        
        # Calculate carbon savings and credits using utility function
        carbon_saved, credits = calculate_carbon_savings(distance, trip.transport_mode)
        
        # Update trip
        trip.end_location = end_location
        trip.end_time = timezone.now()
        trip.distance_km = distance
        trip.carbon_savings = carbon_saved
        trip.credits_earned = credits
        trip.save()
        
        # Create carbon credits if applicable
        if credits > 0:
            CarbonCredit.objects.create(
                amount=credits,
                source_trip=trip,
                owner_type='employee',
                owner_id=trip.employee.id,
                timestamp=timezone.now(),
                status='pending',
                expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
            )
        
        trip_serializer = TripSerializer(trip)
        return Response(trip_serializer.data)

class TripProofUploadView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        
        # Permission check
        self.check_object_permissions(request, trip)
        
        # Only employees can upload proof for their own trips
        if not request.user.is_employee or not hasattr(request.user, 'employee_profile') or trip.employee != request.user.employee_profile:
            return Response(
                {"detail": "You can only upload proof for your own trips."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.FILES.get('proof_image'):
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        trip.proof_image = request.FILES['proof_image']
        trip.verification_status = 'pending'
        trip.save()
        
        trip_serializer = TripSerializer(trip)
        return Response(trip_serializer.data)

class TripVerificationView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsBankAdmin]
    
    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        
        if not trip.proof_image:
            return Response({"error": "Trip has no proof image"}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = TripVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        verification_status = serializer.validated_data['verification_status']
        trip.verification_status = verification_status
        trip.verified_by = request.user
        trip.save()
        
        # Update associated carbon credits
        if verification_status == 'verified':
            CarbonCredit.objects.filter(source_trip=trip).update(status='active')
        elif verification_status == 'rejected':
            CarbonCredit.objects.filter(source_trip=trip).update(status='expired')
        
        trip_serializer = TripSerializer(trip)
        return Response(trip_serializer.data)

class TripStatsView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployeeOrEmployerOrAdmin]
    
    def get(self, request):
        user = self.request.user
        
        if user.is_super_admin or user.is_bank_admin:
            # Admins see overall stats
            user_trips = Trip.objects.all()
        elif user.is_employer:
            # Employers see their employees' stats
            employer_profile = user.employer_profile
            user_trips = Trip.objects.filter(employee__employer=employer_profile)
        else:
            # Employees see their own stats
            employee = EmployeeProfile.objects.get(user=user)
            user_trips = Trip.objects.filter(employee=employee)
        
        stats = {
            'total_trips': user_trips.count(),
            'total_distance': user_trips.aggregate(Sum('distance_km'))['distance_km__sum'] or 0,
            'total_carbon_saved': user_trips.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0,
            'total_credits_earned': user_trips.aggregate(Sum('credits_earned'))['credits_earned__sum'] or 0,
            'trips_by_mode': {
                mode[0]: user_trips.filter(transport_mode=mode[0]).count()
                for mode in Trip.TRANSPORT_MODES
            },
            'verified_trips': user_trips.filter(verification_status='verified').count(),
            'rejected_trips': user_trips.filter(verification_status='rejected').count(),
            'pending_trips': user_trips.filter(verification_status='pending').count(),
        }
        
        serializer = TripStatsSerializer(stats)
        return Response(serializer.data)

# Carbon Credit Views
class CreditListView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployeeOrEmployerOrAdmin]
    
    def get(self, request):
        user = self.request.user
        
        if user.is_super_admin or user.is_bank_admin:
            # Admins see all active credits
            credits = CarbonCredit.objects.filter(status='active').order_by('-timestamp')
        elif user.is_employer:
            # Employers see their own and their employees' credits
            employer_profile = user.employer_profile
            
            # Credits directly owned by the employer
            employer_credits = CarbonCredit.objects.filter(
                owner_type='employer',
                owner_id=employer_profile.id,
                status='active'
            )
            
            # Credits owned by employees of the employer
            employee_ids = EmployeeProfile.objects.filter(employer=employer_profile).values_list('id', flat=True)
            employee_credits = CarbonCredit.objects.filter(
                owner_type='employee',
                owner_id__in=employee_ids,
                status='active'
            )
            
            credits = employer_credits.union(employee_credits).order_by('-timestamp')
        else:
            # Employees see their own credits
            employee = EmployeeProfile.objects.get(user=user)
            credits = CarbonCredit.objects.filter(
                owner_type='employee', 
                owner_id=employee.id,
                status='active'
            ).order_by('-timestamp')
        
        serializer = CarbonCreditSerializer(credits, many=True)
        return Response(serializer.data)

class CreditHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployeeOrEmployerOrAdmin]
    
    def get(self, request):
        user = self.request.user
        
        if user.is_super_admin or user.is_bank_admin:
            # Admins see all credits
            credits = CarbonCredit.objects.all().order_by('-timestamp')
        elif user.is_employer:
            # Employers see their own and their employees' credits
            employer_profile = user.employer_profile
            
            # Credits directly owned by the employer
            employer_credits = CarbonCredit.objects.filter(
                owner_type='employer',
                owner_id=employer_profile.id
            )
            
            # Credits owned by employees of the employer
            employee_ids = EmployeeProfile.objects.filter(employer=employer_profile).values_list('id', flat=True)
            employee_credits = CarbonCredit.objects.filter(
                owner_type='employee',
                owner_id__in=employee_ids
            )
            
            credits = employer_credits.union(employee_credits).order_by('-timestamp')
        else:
            # Employees see their own credits
            employee = EmployeeProfile.objects.get(user=user)
            credits = CarbonCredit.objects.filter(
                owner_type='employee', 
                owner_id=employee.id
            ).order_by('-timestamp')
        
        serializer = CarbonCreditSerializer(credits, many=True)
        return Response(serializer.data)

class CreditStatsView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployeeOrEmployerOrAdmin]
    
    def get(self, request):
        user = self.request.user
        
        if user.is_super_admin or user.is_bank_admin:
            # Admins see overall stats
            user_credits = CarbonCredit.objects.all()
        elif user.is_employer:
            # Employers see their employees' stats
            employer_profile = user.employer_profile
            
            # Credits directly owned by the employer
            employer_credits = CarbonCredit.objects.filter(
                owner_type='employer',
                owner_id=employer_profile.id
            )
            
            # Credits owned by employees of the employer
            employee_ids = EmployeeProfile.objects.filter(employer=employer_profile).values_list('id', flat=True)
            employee_credits = CarbonCredit.objects.filter(
                owner_type='employee',
                owner_id__in=employee_ids
            )
            
            user_credits = employer_credits.union(employee_credits)
        else:
            # Employees see their own stats
            employee = EmployeeProfile.objects.get(user=user)
            user_credits = CarbonCredit.objects.filter(
                owner_type='employee', 
                owner_id=employee.id
            )
        
        active_credits = user_credits.filter(status='active')
        
        stats = {
            'total_credits_earned': user_credits.aggregate(Sum('amount'))['amount__sum'] or 0,
            'active_credits': active_credits.aggregate(Sum('amount'))['amount__sum'] or 0,
            'pending_credits': user_credits.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
            'expired_credits': user_credits.filter(status='expired').aggregate(Sum('amount'))['amount__sum'] or 0,
            'used_credits': user_credits.filter(status='used').aggregate(Sum('amount'))['amount__sum'] or 0,
        }
        
        serializer = CreditStatsSerializer(stats)
        return Response(serializer.data)

class EmployerCreditStatsView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployerOrAdmin]
    
    def get(self, request):
        user = self.request.user
        
        if user.is_super_admin or user.is_bank_admin:
            # Admin users see company-wide statistics
            all_credits = CarbonCredit.objects.all()
            
            stats = {
                'total_credits_issued': all_credits.aggregate(Sum('amount'))['amount__sum'] or 0,
                'active_credits': all_credits.filter(status='active').aggregate(Sum('amount'))['amount__sum'] or 0,
                'credits_by_status': {
                    status[0]: all_credits.filter(status=status[0]).aggregate(Sum('amount'))['amount__sum'] or 0
                    for status in CarbonCredit.CREDIT_STATUS
                },
                'top_employees': EmployeeProfile.objects.annotate(
                    total_credits=Sum('trips__credits_earned')
                ).exclude(total_credits=None).order_by('-total_credits')[:10].values(
                    'id', 'user__email', 'total_credits'
                )
            }
        else:
            # Employer sees only their company's statistics
            employer_profile = user.employer_profile
            
            # Get all employees for this employer
            employee_ids = EmployeeProfile.objects.filter(employer=employer_profile).values_list('id', flat=True)
            
            # Get all credits for these employees
            employee_credits = CarbonCredit.objects.filter(
                owner_type='employee',
                owner_id__in=employee_ids
            )
            
            # Get all credits for the employer
            employer_credits = CarbonCredit.objects.filter(
                owner_type='employer',
                owner_id=employer_profile.id
            )
            
            # Combine both sets of credits
            all_credits = employee_credits.union(employer_credits)
            
            stats = {
                'total_credits_issued': all_credits.aggregate(Sum('amount'))['amount__sum'] or 0,
                'active_credits': all_credits.filter(status='active').aggregate(Sum('amount'))['amount__sum'] or 0,
                'credits_by_status': {
                    status[0]: all_credits.filter(status=status[0]).aggregate(Sum('amount'))['amount__sum'] or 0
                    for status in CarbonCredit.CREDIT_STATUS
                },
                'top_employees': EmployeeProfile.objects.filter(employer=employer_profile).annotate(
                    total_credits=Sum('trips__credits_earned')
                ).exclude(total_credits=None).order_by('-total_credits')[:10].values(
                    'id', 'user__email', 'total_credits'
                )
            }
        
        serializer = EmployerCreditStatsSerializer(stats)
        return Response(serializer.data)
