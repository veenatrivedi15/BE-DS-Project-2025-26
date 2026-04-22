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
    """
    Admin users management view with enhanced filtering and search
    """
    # Get filter parameters
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'date_joined')
    sort_dir = request.GET.get('dir', 'desc')
    
    # Start with all users
    users_queryset = CustomUser.objects.all()
    
    # Apply role filter
    if role_filter:
        if role_filter == 'super_admin':
            users_queryset = users_queryset.filter(is_super_admin=True)
        elif role_filter == 'bank_admin':
            users_queryset = users_queryset.filter(is_bank_admin=True)
        elif role_filter == 'employer':
            users_queryset = users_queryset.filter(is_employer=True)
        elif role_filter == 'employee':
            users_queryset = users_queryset.filter(is_employee=True)
    
    # Apply status filter
    if status_filter:
        if status_filter == 'approved':
            users_queryset = users_queryset.filter(approved=True)
        elif status_filter == 'pending':
            users_queryset = users_queryset.filter(approved=False)
    
    # Apply search filter
    if search_query:
        users_queryset = users_queryset.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(employer_profile__company_name__icontains=search_query)
        ).distinct()
    
    # Apply sorting
    if sort_by == 'name':
        order_field = 'first_name' if sort_dir == 'asc' else '-first_name'
    elif sort_by == 'email':
        order_field = 'email' if sort_dir == 'asc' else '-email'
    elif sort_by == 'role':
        # Sorting by role is complex - fallback to date joined
        order_field = '-date_joined'
    else:  # default to date_joined
        order_field = 'date_joined' if sort_dir == 'asc' else '-date_joined'
    
    users_queryset = users_queryset.order_by(order_field)
    
    # Prefetch related profiles for optimization
    users_queryset = users_queryset.prefetch_related(
        'employer_profile', 
        'employee_profile', 
        'employee_profile__employer'
    )
    
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(users_queryset, 20)  # 20 users per page
    users = paginator.get_page(page_number)
    
    context = {
        'users': users,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'page_obj': users,
        'total_users': users_queryset.count(),
    }
    
    return render(request, 'admin/users.html', context)

@login_required
@user_passes_test(is_super_admin)
def user_detail(request, user_id):
    """
    Detailed view for a specific user
    """
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Get user's profile based on role
    profile = None
    if user.is_employer:
        profile = getattr(user, 'employer_profile', None)
    elif user.is_employee:
        profile = getattr(user, 'employee_profile', None)
    
    # Get user's trips if they're an employee
    trips = []
    if user.is_employee and hasattr(user, 'employee_profile'):
        trips = Trip.objects.filter(employee=user.employee_profile).order_by('-start_time')[:10]
    
    # Get user's locations
    locations = Location.objects.filter(created_by=user)
    
    # Get carbon credits for this user
    credits = None
    if user.is_employee and hasattr(user, 'employee_profile'):
        credits = CarbonCredit.objects.filter(owner_type='employee', owner_id=user.employee_profile.id)
    
    context = {
        'user_detail': user,
        'profile': profile,
        'trips': trips,
        'locations': locations,
        'credits': credits,
    }
    
    return render(request, 'admin/user_detail.html', context)

@login_required
@user_passes_test(is_super_admin)
def approve_user(request, user_id):
    """
    Approve a user account
    """
    if request.method != 'POST':
        return HttpResponseForbidden("Method not allowed")
    
    user = get_object_or_404(CustomUser, id=user_id)
    user.approved = True
    user.save()
    
    # Also approve profile if exists
    if user.is_employer and hasattr(user, 'employer_profile'):
        user.employer_profile.approved = True
        user.employer_profile.save()
    elif user.is_employee and hasattr(user, 'employee_profile'):
        user.employee_profile.approved = True
        user.employee_profile.save()
    
    messages.success(request, f"User {user.email} has been approved.")
    
    # Return partial HTML for HTMX or redirect
    if request.headers.get('HX-Request'):
        return render(request, 'admin/partials/user_row.html', {'user': user})
    
    return redirect('admin_users')

@login_required
@user_passes_test(is_super_admin)
def reject_user(request, user_id):
    """
    Reject a user account
    """
    if request.method != 'POST':
        return HttpResponseForbidden("Method not allowed")
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Mark as rejected by setting approved to False
    user.approved = False
    user.save()
    
    # Also update profile if exists
    if user.is_employer and hasattr(user, 'employer_profile'):
        user.employer_profile.approved = False
        user.employer_profile.save()
    elif user.is_employee and hasattr(user, 'employee_profile'):
        user.employee_profile.approved = False
        user.employee_profile.save()
    
    messages.success(request, f"User {user.email} has been rejected.")
    
    # Return partial HTML for HTMX or redirect
    if request.headers.get('HX-Request'):
        return render(request, 'admin/partials/user_row.html', {'user': user})
    
    return redirect('admin_users')

@login_required
@user_passes_test(is_super_admin)
def user_hierarchy(request):
    """
    View for displaying user hierarchy
    """
    # Get all employers with their employees
    employers = EmployerProfile.objects.prefetch_related(
        'user', 
        'employees',
        'employees__user'
    ).order_by('company_name')
    
    # Get admins (super admins and bank admins)
    admins = CustomUser.objects.filter(
        Q(is_super_admin=True) | Q(is_bank_admin=True)
    ).order_by('email')
    
    context = {
        'employers': employers,
        'admins': admins,
    }
    
    return render(request, 'admin/user_hierarchy.html', context)

@login_required
@user_passes_test(is_super_admin)
def employers_list(request):
    """
    View for displaying and managing employer accounts
    """
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'date_joined')
    sort_dir = request.GET.get('dir', 'desc')
    
    # Start with all employer profiles
    employers_queryset = EmployerProfile.objects.all().select_related('user')
    
    # Apply status filter
    if status_filter:
        if status_filter == 'approved':
            employers_queryset = employers_queryset.filter(approved=True)
        elif status_filter == 'pending':
            employers_queryset = employers_queryset.filter(approved=False)
    
    # Apply search filter
    if search_query:
        employers_queryset = employers_queryset.filter(
            Q(company_name__icontains=search_query) |
            Q(industry__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        ).distinct()
    
    # Apply sorting
    if sort_by == 'company':
        order_field = 'company_name' if sort_dir == 'asc' else '-company_name'
    elif sort_by == 'email':
        order_field = 'user__email' if sort_dir == 'asc' else '-user__email'
    elif sort_by == 'industry':
        order_field = 'industry' if sort_dir == 'asc' else '-industry'
    elif sort_by == 'status':
        order_field = 'approved' if sort_dir == 'asc' else '-approved'
    else:  # default to date joined
        order_field = 'user__date_joined' if sort_dir == 'asc' else '-user__date_joined'
    
    employers_queryset = employers_queryset.order_by(order_field)
    
    # Count employees for each employer
    for employer in employers_queryset:
        employer.employee_count = employer.employees.count()
    
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(employers_queryset, 20)  # 20 employers per page
    employers = paginator.get_page(page_number)
    
    context = {
        'employers': employers,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'page_obj': employers,
        'total_employers': employers_queryset.count(),
        'pending_approval_count': employers_queryset.filter(approved=False).count(),
    }
    
    return render(request, 'admin/employers.html', context)

@login_required
@user_passes_test(is_super_admin)
def create_user(request):
    """
    Create a new user
    """
    if request.method == 'POST':
        # Extract form data
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role')
        password = request.POST.get('password')
        
        # Basic validation
        if not all([email, role, password]):
            messages.error(request, "Please fill all required fields.")
            return redirect('admin_create_user')
        
        # Check if user already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f"User with email {email} already exists.")
            return redirect('admin_create_user')
        
        # Create the user
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            approved=True  # Auto-approve users created by admin
        )
        
        # Set role flags
        if role == 'super_admin':
            user.is_super_admin = True
            user.is_staff = True
            user.is_superuser = True
        elif role == 'bank_admin':
            user.is_bank_admin = True
            user.is_staff = True
        elif role == 'employer':
            user.is_employer = True
            # Create employer profile
            company_name = request.POST.get('company_name', '')
            registration_number = request.POST.get('registration_number', '')
            industry = request.POST.get('industry', '')
            
            if not all([company_name, registration_number]):
                messages.warning(request, f"User created but employer profile is incomplete.")
            else:
                EmployerProfile.objects.create(
                    user=user,
                    company_name=company_name,
                    registration_number=registration_number,
                    industry=industry,
                    approved=True
                )
        elif role == 'employee':
            user.is_employee = True
            # Would need employer ID to create employee profile
            employer_id = request.POST.get('employer_id')
            if employer_id:
                try:
                    employer = EmployerProfile.objects.get(id=employer_id)
                    EmployeeProfile.objects.create(
                        user=user,
                        employer=employer,
                        approved=True
                    )
                except EmployerProfile.DoesNotExist:
                    messages.warning(request, f"User created but employee profile could not be linked to employer.")
        
        user.save()
        messages.success(request, f"User {email} has been created successfully.")
        return redirect('admin_users')
    
    # GET request - show the create user form
    employers = EmployerProfile.objects.filter(approved=True).order_by('company_name')
    
    context = {
        'employers': employers,
    }
    
    return render(request, 'admin/create_user.html', context)

@login_required
@user_passes_test(is_super_admin)
def reports(request):
    """
    Admin reports view
    """
    report_type = request.GET.get('type', 'summary')
    date_range = request.GET.get('date_range', 'all')
    
    # Base context
    context = {
        'report_type': report_type,
        'date_range': date_range,
    }
    
    # Additional data for summary report
    if report_type == 'summary':
        # User statistics
        total_users = CustomUser.objects.count()
        total_employees = EmployeeProfile.objects.count()
        total_employers = EmployerProfile.objects.count()
        
        # Trip statistics
        total_trips = Trip.objects.count()
        total_carbon_saved = Trip.objects.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
        
        # Calculate average trips per employee
        avg_trips_per_user = 0
        if total_employees > 0:
            avg_trips_per_user = total_trips / total_employees
            
        # Credit statistics
        total_credits = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        redeemed_credits = CarbonCredit.objects.filter(status='used').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Add stats to context
        context.update({
            'total_users': total_users,
            'total_employees': total_employees,
            'total_employers': total_employers,
            'total_trips': total_trips,
            'total_carbon_saved': total_carbon_saved,
            'avg_trips_per_user': round(avg_trips_per_user, 2),
            'total_credits': total_credits,
            'redeemed_credits': redeemed_credits,
        })
    
    return render(request, 'admin/reports.html', context)

@login_required
@user_passes_test(is_super_admin)
def export_reports(request):
    """
    Export reports data in CSV or PDF format
    """
    report_type = request.GET.get('report_type', 'summary')
    date_range = request.GET.get('date_range', 'all')
    format = request.GET.get('format', 'csv')
    
    # Get data based on report type
    data = []
    
    if report_type == 'summary':
        # User statistics
        total_users = CustomUser.objects.count()
        total_employees = EmployeeProfile.objects.count()
        total_employers = EmployerProfile.objects.count()
        
        # Trip statistics
        total_trips = Trip.objects.count()
        total_carbon_saved = Trip.objects.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
        
        # Calculate average trips per employee
        avg_trips_per_user = 0
        if total_employees > 0:
            avg_trips_per_user = total_trips / total_employees
            
        # Credit statistics
        total_credits = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        redeemed_credits = CarbonCredit.objects.filter(status='used').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Summary data
        data = [
            ['Metric', 'Value'],
            ['Total Users', total_users],
            ['Total Employees', total_employees],
            ['Total Employers', total_employers],
            ['Total Trips', total_trips],
            ['Total Carbon Saved (kg)', total_carbon_saved],
            ['Average Trips per User', round(avg_trips_per_user, 2)],
            ['Total Credits', total_credits],
            ['Redeemed Credits', redeemed_credits]
        ]
    
    elif report_type == 'trips':
        # Get trips based on date range
        trips = Trip.objects.all().select_related('employee', 'employee__user').order_by('-start_time')
        
        # Apply date filter if needed
        if date_range == '7d':
            trips = trips.filter(start_time__gte=timezone.now() - timezone.timedelta(days=7))
        elif date_range == '30d':
            trips = trips.filter(start_time__gte=timezone.now() - timezone.timedelta(days=30))
        elif date_range == '90d':
            trips = trips.filter(start_time__gte=timezone.now() - timezone.timedelta(days=90))
        
        # Headers
        data.append(['Trip ID', 'Employee', 'Employer', 'Start Time', 'End Time', 'Transport Mode', 'Distance (km)', 'Carbon Savings (kg)', 'Credits Earned', 'Status'])
        
        # Trip data
        for trip in trips:
            data.append([
                trip.id,
                trip.employee.user.get_full_name(),
                trip.employee.employer.company_name,
                trip.start_time.strftime('%Y-%m-%d %H:%M'),
                trip.end_time.strftime('%Y-%m-%d %H:%M') if trip.end_time else 'N/A',
                trip.get_transport_mode_display(),
                trip.distance,
                trip.carbon_savings,
                trip.carbon_credits,
                'Verified' if trip.is_verified else 'Pending'
            ])
    
    elif report_type == 'credits':
        # Get credits based on date range
        credits = CarbonCredit.objects.all().order_by('-timestamp')
        
        # Apply date filter if needed
        if date_range == '7d':
            credits = credits.filter(timestamp__gte=timezone.now() - timezone.timedelta(days=7))
        elif date_range == '30d':
            credits = credits.filter(timestamp__gte=timezone.now() - timezone.timedelta(days=30))
        elif date_range == '90d':
            credits = credits.filter(timestamp__gte=timezone.now() - timezone.timedelta(days=90))
        
        # Headers
        data.append(['Credit ID', 'Amount', 'Source Type', 'Owner Type', 'Owner ID', 'Status', 'Timestamp', 'Expiry Date'])
        
        # Credit data
        for credit in credits:
            data.append([
                credit.id,
                credit.amount,
                'Trip' if credit.source_trip else 'System',
                credit.owner_type,
                credit.owner_id,
                credit.status,
                credit.timestamp.strftime('%Y-%m-%d %H:%M'),
                credit.expiry_date.strftime('%Y-%m-%d') if credit.expiry_date else 'N/A'
            ])
    
    elif report_type == 'employers':
        # Get all employers
        employers = EmployerProfile.objects.all().order_by('company_name')
        
        # Headers
        data.append(['Company Name', 'Industry', 'Total Employees', 'Total Trips', 'Total Carbon Saved (kg)', 'Total Credits'])
        
        # Employer data
        for employer in employers:
            employee_count = employer.employees.count()
            
            # Get trips for this employer's employees
            employee_ids = employer.employees.values_list('id', flat=True)
            trips = Trip.objects.filter(employee__id__in=employee_ids)
            trip_count = trips.count()
            carbon_saved = trips.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
            
            # Get credits for this employer
            credits = CarbonCredit.objects.filter(owner_type='employer', owner_id=employer.id)
            total_credits = credits.aggregate(Sum('amount'))['amount__sum'] or 0
            
            data.append([
                employer.company_name,
                employer.industry,
                employee_count,
                trip_count,
                carbon_saved,
                total_credits
            ])
    
    # Generate export based on format
    if format == 'csv':
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="carbon_credits_{report_type}_report.csv"'
        
        # Write CSV data
        writer = csv.writer(response)
        for row in data:
            writer.writerow(row)
        
        return response
    
    elif format == 'pdf':
        # For PDF, a more complex implementation would be needed with a PDF library
        # This is a simplified version that returns a text response
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="carbon_credits_{report_type}_report.txt"'
        
        # Write data as text
        output = io.StringIO()
        for row in data:
            output.write('\t'.join([str(item) for item in row]) + '\n')
        
        response.write(output.getvalue())
        return response
    
    # Default fallback - return JSON
    return JsonResponse({'data': data})

# Profile views
@login_required
@user_passes_test(is_super_admin)
def admin_profile(request):
    """View for admin profile page."""
    context = {
        'page_title': 'Admin Profile',
        'user': request.user,
    }
    return render(request, 'admin/profile.html', context)

@login_required
@user_passes_test(is_super_admin)
def admin_update_profile(request):
    """Handle admin profile updates."""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        # Validate email format
        if not email or '@' not in email:
            messages.error(request, "Please provide a valid email address.")
            return redirect('admin_profile')
        
        # Check if email is already in use by another user
        if CustomUser.objects.exclude(id=request.user.id).filter(email=email).exists():
            messages.error(request, "This email is already in use by another user.")
            return redirect('admin_profile')
        
        # Update user data
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect('admin_profile')
    
    # For GET requests, redirect to profile page
    return redirect('admin_profile')

@login_required
@user_passes_test(is_super_admin)
def admin_change_password(request):
    """Handle admin password changes."""
    if request.method == 'POST':
        # Get form data
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate passwords
        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Please fill in all password fields.")
            return redirect('admin_profile')
        
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('admin_profile')
        
        # Check current password
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('admin_profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password changed successfully.")
        return redirect('admin_profile')
    
    # For GET requests, redirect to profile page
    return redirect('admin_profile')

@login_required
@user_passes_test(lambda u: u.is_super_admin or u.is_bank_admin)
def employer_approval(request, employer_id):
    """
    Handle employer account approval or rejection.
    """
    try:
        employer = EmployerProfile.objects.get(id=employer_id, approved=False)
        action = request.GET.get('action', '')
        
        if action == 'approve':
            employer.approved = True
            employer.save()
            
            # Also approve the user
            user = employer.user
            user.approved = True
            user.save()
            
            # Allocate initial carbon credits to the employer (if not already done)
            if not employer.initial_credits_allocated:
                # Determine initial credit amount based on company size or other factors
                # For now, we'll use a fixed amount of 1000 credits
                initial_credits = 1000
                
                # Create carbon credit record
                CarbonCredit.objects.create(
                    amount=initial_credits,
                    source_trip=None,  # No associated trip for initial credits
                    owner_type='employer',
                    owner_id=employer.id,
                    timestamp=timezone.now(),
                    status='active',
                    expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
                )
                
                # Mark as allocated
                employer.initial_credits_allocated = True
                employer.save()
                
                messages.success(
                    request, 
                    f"Employer {employer.company_name} has been approved and allocated {initial_credits} initial carbon credits."
                )
            else:
                messages.success(request, f"Employer {employer.company_name} has been approved.")
                
        elif action == 'reject':
            # Implement rejection logic here
            # You may want to send a notification to the employer
            # For now, we'll just delete the employer account
            user = employer.user
            employer.delete()
            user.delete()
            
            messages.success(request, "Employer account has been rejected and removed.")
            
    except EmployerProfile.DoesNotExist:
        messages.error(request, "Employer not found or already approved.")
        
    return redirect('admin_pending_employers') 