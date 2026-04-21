from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.contrib import messages
from users.models import CustomUser, EmployerProfile, EmployeeProfile, Location
from trips.models import Trip, CarbonCredit
from django.utils import timezone
import csv
import io
from django.urls import reverse
from decimal import Decimal

# Import marketplace models if needed
from marketplace.models import MarketOffer, MarketplaceTransaction

def is_super_admin(user):
    return user.is_authenticated and user.is_super_admin

@login_required
@user_passes_test(is_super_admin)
def dashboard(request):
    """
    Admin dashboard view - shows system statistics
    """
    # Count total users, trips, and carbon credits
    total_users = CustomUser.objects.count()
    employers = EmployerProfile.objects.count()
    employees = EmployeeProfile.objects.count()
    bank_admins = CustomUser.objects.filter(is_bank_admin=True).count()
    super_admins = CustomUser.objects.filter(is_super_admin=True).count()
    pending_approval = EmployerProfile.objects.filter(approved=False).count()
    
    # Get from the trip and carbon credit models
    total_trips = Trip.objects.count()
    
    # Count new users in last 30 days
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    new_user_count = CustomUser.objects.filter(date_joined__gte=thirty_days_ago).count()
    
    # Count recent trips in last 7 days
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    recent_trip_count = Trip.objects.filter(start_time__gte=seven_days_ago).count()
    
    # Get carbon credits with proper formatting
    total_credits_raw = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_credits = round(float(total_credits_raw), 2)
    
    # Get pending employers for approval
    pending_employers = EmployerProfile.objects.filter(approved=False).select_related('user').order_by('-created_at')[:5]
    
    # Get recent trips for the dashboard
    recent_trips = Trip.objects.select_related(
        'employee', 'employee__user', 'employee__employer', 'start_location', 'end_location'
    ).order_by('-start_time')[:10]
    
    context = {
        'total_users': total_users,
        'employers': employers,
        'employees': employees,
        'employee_count': employees,
        'employer_count': employers,
        'bank_admin_count': bank_admins,
        'super_admin_count': super_admins,
        'pending_approval': pending_approval,
        'pending_approval_count': pending_approval,
        'total_trips': total_trips,
        'trip_count': total_trips,
        'recent_trip_count': recent_trip_count,
        'new_user_count': new_user_count,
        'total_credits': total_credits,
        'pending_employers': pending_employers,
        'recent_trips': recent_trips,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_super_admin)
def dashboard_recent_trips(request):
    """
    HTMX-compatible view that returns recent trips for the admin dashboard
    """
    # Get recent trips with employee and location details
    trips = Trip.objects.select_related(
        'employee', 'employee__user', 'start_location', 'end_location'
    ).order_by('-start_time')[:10]
    
    # Get transport modes for display
    transport_modes = Trip.TRANSPORT_MODES
    
    context = {
        'trips': trips,
        'transport_modes': transport_modes,
    }
    
    return render(request, 'admin/partials/recent_trips.html', context)

@login_required
@user_passes_test(is_super_admin)
def users_list(request):
    """Placeholder function for users list view"""
    return render(request, 'admin/users.html', {'users': []})

@login_required
@user_passes_test(is_super_admin)
def create_user(request):
    """Placeholder function for create user view"""
    return render(request, 'admin/create_user.html', {})

@login_required
@user_passes_test(is_super_admin)
def user_detail(request, user_id):
    """Placeholder function for user detail view"""
    return render(request, 'admin/user_detail.html', {'user_detail': None})

@login_required
@user_passes_test(is_super_admin)
def approve_user(request, user_id):
    """Placeholder function for approve user view"""
    return redirect('admin_users')

@login_required
@user_passes_test(is_super_admin)
def reject_user(request, user_id):
    """Placeholder function for reject user view"""
    return redirect('admin_users')

@login_required
@user_passes_test(is_super_admin)
def user_hierarchy(request):
    """Placeholder function for user hierarchy view"""
    return render(request, 'admin/user_hierarchy.html', {})

@login_required
@user_passes_test(is_super_admin)
def employers_list(request):
    """Placeholder function for employers list view"""
    return render(request, 'admin/employers.html', {'employers': []})

@login_required
@user_passes_test(is_super_admin)
def reports(request):
    """Placeholder function for reports view"""
    return render(request, 'admin/reports.html', {})

@login_required
@user_passes_test(is_super_admin)
def export_reports(request):
    """Placeholder function for export reports view"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'
    writer = csv.writer(response)
    writer.writerow(['No data'])
    return response

@login_required
@user_passes_test(is_super_admin)
def admin_profile(request):
    """Placeholder function for admin profile view"""
    return render(request, 'admin/profile.html', {'user': request.user})

@login_required
@user_passes_test(is_super_admin)
def admin_update_profile(request):
    """Placeholder function for admin update profile view"""
    return redirect('admin_profile')

@login_required
@user_passes_test(is_super_admin)
def admin_change_password(request):
    """Placeholder function for admin change password view"""
    return redirect('admin_profile')

@login_required
@user_passes_test(lambda u: u.is_super_admin or u.is_bank_admin)
def employer_approval(request, employer_id):
    """Placeholder function for employer approval view"""
    return redirect('admin_pending_employers')

# Add additional admin views as needed 
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.contrib import messages
from users.models import CustomUser, EmployerProfile, EmployeeProfile, Location
from trips.models import Trip, CarbonCredit
from django.utils import timezone
import csv
import io
from django.urls import reverse
from decimal import Decimal

# Import marketplace models if needed
from marketplace.models import MarketOffer, MarketplaceTransaction

def is_super_admin(user):
    return user.is_authenticated and user.is_super_admin

@login_required
@user_passes_test(is_super_admin)
def dashboard(request):
    """
    Admin dashboard view - shows system statistics
    """
    # Count total users, trips, and carbon credits
    total_users = CustomUser.objects.count()
    employers = EmployerProfile.objects.count()
    employees = EmployeeProfile.objects.count()
    bank_admins = CustomUser.objects.filter(is_bank_admin=True).count()
    super_admins = CustomUser.objects.filter(is_super_admin=True).count()
    pending_approval = EmployerProfile.objects.filter(approved=False).count()
    
    # Get from the trip and carbon credit models
    total_trips = Trip.objects.count()
    
    # Count new users in last 30 days
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    new_user_count = CustomUser.objects.filter(date_joined__gte=thirty_days_ago).count()
    
    # Count recent trips in last 7 days
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    recent_trip_count = Trip.objects.filter(start_time__gte=seven_days_ago).count()
    
    # Get carbon credits with proper formatting
    total_credits_raw = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_credits = round(float(total_credits_raw), 2)
    
    # Get pending employers for approval
    pending_employers = EmployerProfile.objects.filter(approved=False).select_related('user').order_by('-created_at')[:5]
    
    # Get recent trips for the dashboard
    recent_trips = Trip.objects.select_related(
        'employee', 'employee__user', 'employee__employer', 'start_location', 'end_location'
    ).order_by('-start_time')[:10]
    
    context = {
        'total_users': total_users,
        'employers': employers,
        'employees': employees,
        'employee_count': employees,
        'employer_count': employers,
        'bank_admin_count': bank_admins,
        'super_admin_count': super_admins,
        'pending_approval': pending_approval,
        'pending_approval_count': pending_approval,
        'total_trips': total_trips,
        'trip_count': total_trips,
        'recent_trip_count': recent_trip_count,
        'new_user_count': new_user_count,
        'total_credits': total_credits,
        'pending_employers': pending_employers,
        'recent_trips': recent_trips,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_super_admin)
def dashboard_recent_trips(request):
    """
    HTMX-compatible view that returns recent trips for the admin dashboard
    """
    # Get recent trips with employee and location details
    trips = Trip.objects.select_related(
        'employee', 'employee__user', 'start_location', 'end_location'
    ).order_by('-start_time')[:10]
    
    # Get transport modes for display
    transport_modes = Trip.TRANSPORT_MODES
    
    context = {
        'trips': trips,
        'transport_modes': transport_modes,
    }
    
    return render(request, 'admin/partials/recent_trips.html', context)

@login_required
@user_passes_test(is_super_admin)
def users_list(request):
    """Placeholder function for users list view"""
    return render(request, 'admin/users.html', {'users': []})

@login_required
@user_passes_test(is_super_admin)
def create_user(request):
    """Placeholder function for create user view"""
    return render(request, 'admin/create_user.html', {})

@login_required
@user_passes_test(is_super_admin)
def user_detail(request, user_id):
    """Placeholder function for user detail view"""
    return render(request, 'admin/user_detail.html', {'user_detail': None})

@login_required
@user_passes_test(is_super_admin)
def approve_user(request, user_id):
    """Placeholder function for approve user view"""
    return redirect('admin_users')

@login_required
@user_passes_test(is_super_admin)
def reject_user(request, user_id):
    """Placeholder function for reject user view"""
    return redirect('admin_users')

@login_required
@user_passes_test(is_super_admin)
def user_hierarchy(request):
    """Placeholder function for user hierarchy view"""
    return render(request, 'admin/user_hierarchy.html', {})

@login_required
@user_passes_test(is_super_admin)
def employers_list(request):
    """Placeholder function for employers list view"""
    return render(request, 'admin/employers.html', {'employers': []})

@login_required
@user_passes_test(is_super_admin)
def reports(request):
    """Placeholder function for reports view"""
    return render(request, 'admin/reports.html', {})

@login_required
@user_passes_test(is_super_admin)
def export_reports(request):
    """Placeholder function for export reports view"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'
    writer = csv.writer(response)
    writer.writerow(['No data'])
    return response

@login_required
@user_passes_test(is_super_admin)
def admin_profile(request):
    """Placeholder function for admin profile view"""
    return render(request, 'admin/profile.html', {'user': request.user})

@login_required
@user_passes_test(is_super_admin)
def admin_update_profile(request):
    """Placeholder function for admin update profile view"""
    return redirect('admin_profile')

@login_required
@user_passes_test(is_super_admin)
def admin_change_password(request):
    """Placeholder function for admin change password view"""
    return redirect('admin_profile')

@login_required
@user_passes_test(lambda u: u.is_super_admin or u.is_bank_admin)
def employer_approval(request, employer_id):
    """Placeholder function for employer approval view"""
    return redirect('admin_pending_employers')

# Add additional admin views as needed 