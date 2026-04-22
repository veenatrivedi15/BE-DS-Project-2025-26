from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal
from users.models import Location
from .trips_views import create_trip
from django.core.paginator import Paginator
from django.db.models import Q
from trips.models import CarbonCredit, Trip
from django.conf import settings
from users.models import CustomUser
from django.urls import reverse
from users.models import EmployeeProfile
from marketplace.models import MarketOffer, EmployeeCreditOffer
from datetime import timedelta, datetime
import json
from core.utils.sustainability_tips import generate_single_sustainability_tip

@login_required
@user_passes_test(lambda u: u.is_employee)
def dashboard(request):
    """
    Dashboard view for employees.
    """
    employee = request.user.employee_profile
    
    # Calculate carbon credits earned
    total_credits = CarbonCredit.objects.filter(
        owner_type='employee', 
        owner_id=employee.id,
        status='active'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Credits earned in the last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    credits_last_week = CarbonCredit.objects.filter(
        owner_type='employee', 
        owner_id=employee.id, 
        status='active',
        timestamp__gte=week_ago
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get trip statistics - use all trips for total count
    total_trips = Trip.objects.filter(employee=employee).count()
    completed_trips = Trip.objects.filter(
        employee=employee, 
        verification_status='verified'
    ).count()
    
    # Calculate total distance traveled (from verified trips only)
    total_distance = Trip.objects.filter(
        employee=employee,
        verification_status='verified'
    ).aggregate(Sum('distance_km'))['distance_km__sum'] or 0
    
    # Calculate CO2 saved (from verified trips only)
    co2_saved = Trip.objects.filter(
        employee=employee,
        verification_status='verified'
    ).aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
    
    # Calculate CO2 emitted (baseline emissions if no eco-friendly trips were taken)
    # Sum of baseline emissions for all trips
    co2_emitted = Trip.objects.filter(
        employee=employee,
        verification_status='verified'
    ).aggregate(Sum('ef_baseline'))['ef_baseline__sum'] or 0
    if co2_emitted:
        # Multiply by distance to get total baseline emissions
        total_distance = Trip.objects.filter(
            employee=employee,
            verification_status='verified'
        ).aggregate(Sum('distance_km'))['distance_km__sum'] or 0
        # Convert to float to avoid Decimal/float division error
        co2_emitted = float(co2_emitted)
        total_distance = float(total_distance)
        # Average baseline emission factor per km
        avg_baseline_per_km = co2_emitted / total_distance if total_distance > 0 else 0
        co2_emitted = avg_baseline_per_km * total_distance
    else:
        co2_emitted = 0
    
    # Calculate total credits earned (from all active credits, not just verified trips)
    # This should match the total_credits calculated above
    total_credits_earned = CarbonCredit.objects.filter(
        owner_type='employee',
        owner_id=employee.id,
        status='active'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate streak (consecutive days with verified trips)
    # For simplicity, we'll just count consecutive days with trips
    streak = calculate_streak(employee)
    best_streak = getattr(employee, 'best_streak', 0)
    
    if streak > best_streak:
        employee.best_streak = streak
        employee.save()
    
    # Get recent trips
    recent_trips = Trip.objects.filter(
        employee=employee
    ).order_by('-start_time')[:5]
    
    # Get pending trips
    pending_trips = Trip.objects.filter(
        employee=employee,
        verification_status='pending'
    ).count()
    
    # Tree equivalent (rough estimate)
    tree_equivalent = int(co2_saved / 21) if co2_saved else 0  # 1 tree absorbs ~21kg CO2 per year
    
    # Get chart data for activity graphs
    
    # Weekly credits data (last 7 days)
    weekly_credits_data = []
    weekly_labels = []
    today = timezone.now().date()
    
    for i in range(6, -1, -1):  # Last 7 days
        date = today - timedelta(days=i)
        day_name = date.strftime('%a')  # Mon, Tue, etc.
        weekly_labels.append(day_name)
        
        # Get credits earned on this day
        day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        
        day_credits = CarbonCredit.objects.filter(
            owner_type='employee',
            owner_id=employee.id,
            status='active',
            timestamp__gte=day_start,
            timestamp__lt=day_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        weekly_credits_data.append(float(day_credits))
    
    # Monthly credits data (last 4 weeks)
    monthly_credits_data = []
    monthly_labels = []
    
    for i in range(3, -1, -1):  # Last 4 weeks
        week_start = today - timedelta(days=(i * 7) + 6)
        week_end = week_start + timedelta(days=7)
        monthly_labels.append(f"Week {4-i}")
        
        week_start_dt = timezone.make_aware(datetime.combine(week_start, datetime.min.time()))
        week_end_dt = timezone.make_aware(datetime.combine(week_end, datetime.min.time()))
        
        week_credits = CarbonCredit.objects.filter(
            owner_type='employee',
            owner_id=employee.id,
            status='active',
            timestamp__gte=week_start_dt,
            timestamp__lt=week_end_dt
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        monthly_credits_data.append(float(week_credits))
    
    # Transport modes data (from verified trips)
    transport_mode_counts = Trip.objects.filter(
        employee=employee,
        verification_status='verified'
    ).values('transport_mode').annotate(count=Count('id')).order_by('-count')
    
    transport_labels = []
    transport_data = []
    transport_colors = {
        'bicycle': '#55A630',
        'walking': '#1E88E5',
        'public_transport': '#70A9A1',
        'carpool': '#F9DC5C',
        'car': '#9DACFF',
        'work_from_home': '#FF6B6B'
    }
    
    total_verified_trips = Trip.objects.filter(
        employee=employee,
        verification_status='verified'
    ).count()
    
    for mode_data in transport_mode_counts:
        mode = mode_data['transport_mode']
        count = mode_data['count']
        percentage = (count / total_verified_trips * 100) if total_verified_trips > 0 else 0
        
        # Format mode name
        mode_name = mode.replace('_', ' ').title()
        if mode == 'public_transport':
            mode_name = 'Public Transport'
        elif mode == 'work_from_home':
            mode_name = 'Work from Home'
        
        transport_labels.append(mode_name)
        transport_data.append(round(percentage, 1))
    
    # If no trips, add default data
    if not transport_data:
        transport_labels = ['No trips yet']
        transport_data = [100]
    
    # Get personalized sustainability tip (single tip)
    try:
        sustainability_tip = generate_single_sustainability_tip(request.user)
    except Exception as e:
        # Fallback to default tip if generation fails
        sustainability_tip = "Consider using public transportation or carpooling to reduce your carbon footprint and earn more carbon credits."
    
    # Get user's gamification data
    from core.gamification_models import UserBadge, UserProgress, UserPoints, Streak
    
    # User badges earned
    user_badges = UserBadge.objects.filter(user=request.user).select_related('badge')
    total_badges = user_badges.count()
    recent_badges = user_badges.order_by('-earned_at')[:3]
    
    # User progress
    user_progress = UserProgress.objects.filter(user=request.user, is_completed=True).count()
    active_progress = UserProgress.objects.filter(user=request.user, is_completed=False).order_by('-start_date')[:3]
    
    # User points and streak
    user_points = UserPoints.objects.filter(user=request.user).aggregate(
        total_points=Sum('points'),
        points_this_week=Sum('points', filter=Q(created_at__gte=week_ago))
    )
    total_points = user_points['total_points'] or 0
    points_this_week = user_points['points_this_week'] or 0
    
    # Current streak
    current_streak = Streak.objects.filter(
        user=request.user, 
        streak_type='daily_trips',
        is_active=True
    ).first()
    current_streak_days = current_streak.current_streak if current_streak else 0
    
    # Get user's pollution alerts
    from core.pollution_models import UserPollutionAlert
    pollution_alerts = UserPollutionAlert.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:3]
    total_alerts = pollution_alerts.count()
    
    context = {
        'page_title': 'Employee Dashboard',
        'employee': employee,
        'total_credits': total_credits,
        'credits_last_week': credits_last_week,
        'total_trips': total_trips,
        'completed_trips': completed_trips,
        'total_distance': total_distance,
        'co2_saved': co2_saved,
        'co2_emitted': co2_emitted,
        'current_streak': current_streak_days,
        'best_streak': best_streak,
        'recent_trips': recent_trips,
        'pending_trips': pending_trips,
        'tree_equivalent': tree_equivalent,
        'wallet_balance': employee.wallet_balance,
        # Chart data (as lists for json_script filter)
        'weekly_credits_data': weekly_credits_data,
        'weekly_labels': weekly_labels,
        'monthly_credits_data': monthly_credits_data,
        'monthly_labels': monthly_labels,
        'transport_labels': transport_labels,
        'transport_data': transport_data,
        'sustainability_tip': sustainability_tip,
        # Gamification data
        'total_badges': total_badges,
        'recent_badges': recent_badges,
        'user_progress': user_progress,
        'active_progress': active_progress,
        'total_points': total_points,
        'points_this_week': points_this_week,
        # Pollution data
        'pollution_alerts': pollution_alerts,
        'total_alerts': total_alerts,
    }
    
    return render(request, 'employee/dashboard.html', context)

def calculate_streak(employee):
    """Calculate the employee's current streak of consecutive days with trips."""
    verified_trips = Trip.objects.filter(
        employee=employee,
        verification_status='verified'
    ).order_by('-start_time')
    
    if not verified_trips:
        return 0
    
    # Get dates of verified trips
    trip_dates = [trip.start_time.date() for trip in verified_trips]
    
    # Remove duplicates and sort
    unique_dates = sorted(set(trip_dates), reverse=True)
    
    # Calculate streak
    streak = 1
    today = timezone.now().date()
    
    # If no trip today, start from the most recent trip date
    if unique_dates[0] != today:
        today = unique_dates[0]
    
    # Check for consecutive days
    for i in range(1, len(unique_dates)):
        prev_date = today - timedelta(days=i)
        if prev_date in unique_dates:
            streak += 1
        else:
            break
    
    return streak

@login_required
@user_passes_test(lambda u: u.is_employee)
def trip_log(request):
    """
    View for logging new trips.
    """
    # Get employee profile
    employee = request.user.employee_profile
    
    # Check if this is a home location registration request
    if request.method == 'POST' and request.POST.get('register_home') == 'true':
        return register_home_location(request)
    
    # If POST request for a trip, handle form submission
    if request.method == 'POST':
        return create_trip(request)
    
    # For GET requests, render the form
    # Get employee's home location if it exists
    home_location = Location.objects.filter(
        created_by=request.user,
        location_type='home'
    ).first()
    
    # If user doesn't have a home location, create a default one automatically
    if not home_location:
        # Create a default home location with Thane, Maharashtra, India coordinates
        default_address = "Thane, Maharashtra, India"
        default_lat = 19.2183  # Thane latitude
        default_lng = 72.9781  # Thane longitude
        
        home_location = Location.objects.create(
            created_by=request.user,
            location_type='home',
            address=default_address,
            latitude=default_lat,
            longitude=default_lng,
            name=f"Home - Thane",
            is_primary=True
        )
        
        messages.info(request, "A default home location in Thane, Maharashtra, India has been created for you. You can update it in your profile settings.")
    
    has_home_location = True  # We now always have a home location
    
    # Get employer's locations
    employer_locations = []
    if employee.employer:
        employer_locations = employee.employer.office_locations.all()
        
        # If employer has no office locations, create a default one in Thane
        if not employer_locations.exists():
            default_office_address = "Thane East, Maharashtra, India"
            default_office_lat = 19.2300  # Thane East latitude
            default_office_lng = 72.9900  # Thane East longitude
            
            # Create default office location
            office_location = Location.objects.create(
                created_by=request.user,
                location_type='office',
                address=default_office_address,
                latitude=default_office_lat,
                longitude=default_office_lng,
                name="Office - Thane East",
                is_primary=True,
                employer=employee.employer
            )
            
            # Refresh the employer locations
            employer_locations = employee.employer.office_locations.all()
            
            messages.info(request, "A default office location in Thane East has been added for your employer.")
    
    # Get today's date for the form
    today = timezone.now()
    
    # Get Google Maps API key
    from django.conf import settings
    google_maps_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    context = {
        'page_title': 'Log a Trip',
        'employer_locations': employer_locations,
        'today': today,
        'has_home_location': has_home_location,
        'home_location': home_location,
        'google_maps_api_key': google_maps_api_key
    }
    
    return render(request, 'employee/trip_log.html', context)

@login_required
@user_passes_test(lambda u: u.is_employee)
def register_home_location(request):
    """
    Handle home location registration for employees.
    """
    if request.method == 'POST':
        try:
            # Get form data
            home_latitude = request.POST.get('home_latitude')
            home_longitude = request.POST.get('home_longitude')
            home_address = request.POST.get('home_address')
            
            # Validate required fields
            if not home_latitude or not home_longitude or not home_address:
                messages.error(request, "Please provide complete home location information.")
                return redirect('employee_trip_log')
            
            # Check if employee already has a home location
            existing_home = Location.objects.filter(
                created_by=request.user,
                location_type='home'
            ).first()
            
            if existing_home:
                # Update existing home location
                existing_home.latitude = Decimal(home_latitude)
                existing_home.longitude = Decimal(home_longitude)
                existing_home.address = home_address
                existing_home.save()
                messages.success(request, "Home location updated successfully.")
            else:
                # Create new home location
                Location.objects.create(
                    created_by=request.user,
                    name="Home",
                    latitude=Decimal(home_latitude),
                    longitude=Decimal(home_longitude),
                    address=home_address,
                    location_type='home',
                    is_primary=True,
                    employee=request.user.employee_profile
                )
                messages.success(request, "Home location registered successfully.")
            
            return redirect('employee_trip_log')
            
        except Exception as e:
            messages.error(request, f"Error registering home location: {str(e)}")
            return redirect('employee_trip_log')
    
    # For GET requests, redirect to trip log
    return redirect('employee_trip_log')

@login_required
@user_passes_test(lambda u: u.is_employee)
def trips_list(request):
    """
    View for listing all trips by the employee.
    """
    # Get employee profile
    employee = request.user.employee_profile
    
    # Get trips for this employee
    trips = employee.trips.all().order_by('-start_time')
    
    # Calculate aggregate statistics
    stats = trips.aggregate(
        total_distance=Sum('distance_km'),
        total_co2_saved=Sum('carbon_savings'),
        total_credits=Sum('credits_earned')
    )
    
    # Default values if no trips exist
    total_distance = stats['total_distance'] or 0
    total_co2_saved = stats['total_co2_saved'] or 0
    total_credits = stats['total_credits'] or 0
    
    context = {
        'trips': trips,
        'page_title': 'My Trips',
        'total_distance': total_distance,
        'total_co2_saved': total_co2_saved,
        'total_credits': total_credits,
    }
    
    return render(request, 'employee/trips.html', context)

@login_required
@user_passes_test(lambda u: u.is_employee)
def manage_home_location(request):
    """
    View for managing employee's home location.
    """
    # Get employee profile
    employee = request.user.employee_profile
    
    # Check if this is a POST request for updating home location
    if request.method == 'POST':
        try:
            # Get form data
            home_latitude = request.POST.get('home_latitude')
            home_longitude = request.POST.get('home_longitude')
            home_address = request.POST.get('home_address')
            home_name = request.POST.get('home_name', 'My Home')
            
            # Validate required fields
            if not home_latitude or not home_longitude or not home_address:
                messages.error(request, "Please provide complete home location information.")
                return redirect('employee_manage_home_location')
            
            # Check if employee already has a home location
            existing_home = Location.objects.filter(
                created_by=request.user,
                location_type='home'
            ).first()
            
            if existing_home:
                # Update existing home location
                existing_home.latitude = Decimal(home_latitude)
                existing_home.longitude = Decimal(home_longitude)
                existing_home.address = home_address
                existing_home.name = home_name
                existing_home.save()
                messages.success(request, "Home location updated successfully.")
            else:
                # Create new home location
                Location.objects.create(
                    created_by=request.user,
                    name=home_name,
                    latitude=Decimal(home_latitude),
                    longitude=Decimal(home_longitude),
                    address=home_address,
                    location_type='home',
                    is_primary=True,
                    employee=request.user.employee_profile
                )
                messages.success(request, "Home location registered successfully.")
            
            return redirect('employee_dashboard')
            
        except Exception as e:
            messages.error(request, f"Error saving home location: {str(e)}")
            return redirect('employee_manage_home_location')
    
    # For GET requests, show the form with existing data
    # Check if employee has a home location
    home_location = Location.objects.filter(
        created_by=request.user,
        location_type='home'
    ).first()
    
    has_home_location = home_location is not None
    
    # Get Google Maps API key
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY
    
    context = {
        'page_title': 'Manage Home Location',
        'home_location': home_location,
        'has_home_location': has_home_location,
        'google_maps_api_key': google_maps_api_key,
    }
    
    return render(request, 'employee/manage_home_location.html', context)

@login_required
@user_passes_test(lambda u: u.is_employee)
def profile(request):
    """View for employee profile page."""
    # Get the employee profile and stats
    employee_profile = getattr(request.user, 'employee_profile', None)
    
    # Get home location
    home_location = Location.objects.filter(
        created_by=request.user,
        location_type='home'
    ).first()
    
    # Get employee stats
    stats = {
        'total_credits': 0,
        'redeemed_credits': 0,
        'available_credits': 0,
        'total_trips': 0,
        'co2_saved': 0
    }
    
    if employee_profile:
        # Get trips
        trips = Trip.objects.filter(employee=employee_profile)
        total_trips = trips.count()
        
        # Carbon credits
        total_credits = CarbonCredit.objects.filter(
            owner_type='employee',
            owner_id=employee_profile.id
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        redeemed_credits = CarbonCredit.objects.filter(
            owner_type='employee',
            owner_id=employee_profile.id,
            status='used'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # CO2 saved
        co2_saved = trips.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
        
        stats = {
            'total_credits': total_credits,
            'redeemed_credits': redeemed_credits,
            'available_credits': total_credits - redeemed_credits,
            'total_trips': total_trips,
            'co2_saved': co2_saved
        }
    
    # Maps API key for displaying maps
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY
    
    context = {
        'page_title': 'Employee Profile',
        'user': request.user,
        'employee_profile': employee_profile,
        'home_location': home_location,
        'stats': stats,
        'google_maps_api_key': google_maps_api_key
    }
    return render(request, 'employee/profile.html', context)

@login_required
@user_passes_test(lambda u: u.is_employee)
def update_profile(request):
    """Handle employee profile updates."""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        # Validate email format
        if not email or '@' not in email:
            messages.error(request, "Please provide a valid email address.")
            return redirect('employee_profile')
        
        # Check if email is already in use by another user
        if CustomUser.objects.exclude(id=request.user.id).filter(email=email).exists():
            messages.error(request, "This email is already in use by another user.")
            return redirect('employee_profile')
        
        # Update user data
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect('employee_profile')
    
    # For GET requests, redirect to profile page
    return redirect('employee_profile')

@login_required
@user_passes_test(lambda u: u.is_employee)
def update_home_location(request):
    """Handle updating home location."""
    if request.method == 'POST':
        # Get form data
        address = request.POST.get('address')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Validate data
        if not address or not latitude or not longitude:
            messages.error(request, "Please provide complete location information.")
            return redirect('employee_profile')
        
        try:
            # Check if home location exists
            home_location = Location.objects.filter(
                created_by=request.user,
                location_type='home'
            ).first()
            
            if home_location:
                # Update existing location
                home_location.address = address
                home_location.latitude = Decimal(latitude)
                home_location.longitude = Decimal(longitude)
                home_location.save()
            else:
                # Create new home location
                home_location = Location.objects.create(
                    created_by=request.user,
                    name="Home",
                    address=address,
                    latitude=Decimal(latitude),
                    longitude=Decimal(longitude),
                    location_type='home',
                    is_primary=True,
                    employee=request.user.employee_profile
                )
            
            messages.success(request, "Home location updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating home location: {str(e)}")
        
        return redirect('employee_profile')
    
    # For GET requests, show a form to update home location
    # Get current home location
    home_location = Location.objects.filter(
        created_by=request.user,
        location_type='home'
    ).first()
    
    # Maps API key for displaying maps
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY
    
    context = {
        'page_title': 'Update Home Location',
        'home_location': home_location,
        'google_maps_api_key': google_maps_api_key
    }
    return render(request, 'employee/update_home_location.html', context)

@login_required
@user_passes_test(lambda u: u.is_employee)
def change_password(request):
    """Handle employee password changes."""
    if request.method == 'POST':
        # Get form data
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate passwords
        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Please fill in all password fields.")
            return redirect('employee_profile')
        
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('employee_profile')
        
        # Check current password
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('employee_profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password changed successfully.")
        return redirect('employee_profile')
    
    # For GET requests, redirect to profile page
    return redirect('employee_profile')

@login_required
@user_passes_test(lambda u: u.is_employee)
def marketplace(request):
    """
    View for employee marketplace to buy/sell credits to their employer.
    """
    employee = request.user.employee_profile
    employer = employee.employer
    
    # Get employee's active credits
    employee_credits = CarbonCredit.objects.filter(
        owner_type='employee',
        owner_id=employee.id,
        status='active'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get current market rate (average price from active market offers)
    market_rate = MarketOffer.objects.filter(
        status='active'
    ).aggregate(Avg('price_per_credit'))['price_per_credit__avg'] or 5.0  # Default to $5 if no data
    
    # Get pending offers
    pending_offers = EmployeeCreditOffer.objects.filter(
        employee=employee,
        status='pending'
    ).order_by('-created_at')
    
    # Get completed offers
    completed_offers = EmployeeCreditOffer.objects.filter(
        employee=employee,
        status__in=['approved', 'rejected', 'cancelled']
    ).order_by('-processed_at')[:10]  # Show last 10
    
    if request.method == 'POST':
        offer_type = request.POST.get('offer_type')
        credit_amount = request.POST.get('credit_amount')
        
        try:
            credit_amount = float(credit_amount)
            
            # Validate input
            if credit_amount <= 0:
                messages.error(request, "Credit amount must be positive")
                return redirect('employee_marketplace')
                
            # For selling: check if employee has enough credits
            if offer_type == 'sell' and credit_amount > employee_credits:
                messages.error(request, f"You don't have enough credits. Available: {employee_credits}")
                return redirect('employee_marketplace')
            
            # For buying: implement any validation if needed
            
            # Calculate total amount based on market rate
            total_amount = Decimal(str(credit_amount)) * Decimal(str(market_rate))
            
            # Create the offer
            EmployeeCreditOffer.objects.create(
                employee=employee,
                employer=employer,
                offer_type=offer_type,
                credit_amount=credit_amount,
                market_rate=market_rate,
                total_amount=total_amount,
                status='pending'
            )
            
            if offer_type == 'buy':
                messages.success(request, f"Your request to buy {credit_amount} credits for ${total_amount:.2f} has been submitted to your employer.")
            else:
                messages.success(request, f"Your request to sell {credit_amount} credits for ${total_amount:.2f} has been submitted to your employer.")
                
        except ValueError:
            messages.error(request, "Invalid credit amount")
        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")
    
    context = {
        'page_title': 'Marketplace',
        'employee': employee,
        'employer': employer,
        'employee_credits': employee_credits,
        'market_rate': market_rate,
        'pending_offers': pending_offers,
        'completed_offers': completed_offers,
        'wallet_balance': employee.wallet_balance
    }
    
    return render(request, 'employee/marketplace.html', context)

@login_required
@user_passes_test(lambda u: u.is_employee)
def cancel_offer(request, offer_id):
    """
    Cancel a pending credit offer.
    """
    employee = request.user.employee_profile
    
    try:
        offer = get_object_or_404(
            EmployeeCreditOffer, 
            id=offer_id, 
            employee=employee,
            status='pending'
        )
        
        offer.status = 'cancelled'
        offer.processed_at = timezone.now()
        offer.save()
        
        messages.success(request, "Your offer has been cancelled.")
        
    except EmployeeCreditOffer.DoesNotExist:
        messages.error(request, "Offer not found or already processed.")
    
    return redirect('employee_marketplace') 