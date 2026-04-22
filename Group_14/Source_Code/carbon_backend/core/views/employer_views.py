from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from users.models import EmployeeProfile, CustomUser, EmployeeInvitation, Location
from trips.models import Trip, CarbonCredit
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages

# Import marketplace models
from marketplace.models import MarketOffer, MarketplaceTransaction, TransactionNotification, EmployeeCreditOffer
from decimal import Decimal

@login_required
@user_passes_test(lambda u: u.is_employer)
def dashboard(request):
    """
    Dashboard view for employer users.
    """
    employer_profile = request.user.employer_profile
    
    # Get basic statistics
    total_employees = employer_profile.employees.count()
    active_employees = employer_profile.employees.filter(approved=True).count()
    
    # Get trip statistics for this employer's employees
    employee_ids = employer_profile.employees.values_list('id', flat=True)
    
    # Trip statistics
    all_trips = Trip.objects.filter(employee__in=employee_ids)
    total_trips = all_trips.count()
    pending_trips = all_trips.filter(verification_status='pending').count()
    
    # Carbon credit statistics
    total_credits = all_trips.aggregate(Sum('credits_earned'))['credits_earned__sum'] or 0
    
    # Calculate credits growth (this month vs last month)
    now = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    
    this_month_credits = all_trips.filter(start_time__gte=this_month_start).aggregate(Sum('credits_earned'))['credits_earned__sum'] or 0
    last_month_credits = all_trips.filter(start_time__gte=last_month_start, start_time__lt=this_month_start).aggregate(Sum('credits_earned'))['credits_earned__sum'] or 1  # Avoid division by zero
    
    credits_growth = ((this_month_credits - last_month_credits) / last_month_credits) * 100 if last_month_credits > 0 else 0
    
    # CO2 saved statistics
    co2_saved = all_trips.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
    tree_equivalent = int(co2_saved / 21)  # Rough estimate: 1 tree absorbs ~21kg CO2 per year
    
    # Get top employees for this month
    top_employees = []
    employee_profiles = employer_profile.employees.filter(approved=True)
    
    for profile in employee_profiles[:5]:  # Limit to top 5
        employee_trips = all_trips.filter(employee=profile, start_time__gte=this_month_start)
        trip_count = employee_trips.count()
        total_distance = employee_trips.aggregate(Sum('distance_km'))['distance_km__sum'] or 0
        total_credits = employee_trips.aggregate(Sum('credits_earned'))['credits_earned__sum'] or 0
        co2_saved = employee_trips.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
        
        if trip_count > 0:
            top_employees.append({
                'user': profile.user,
                'department': getattr(profile, 'department', 'N/A'),
                'trip_count': trip_count,
                'total_distance': total_distance,
                'total_credits': total_credits,
                'co2_saved': co2_saved
            })
    
    # Sort by credits earned
    top_employees = sorted(top_employees, key=lambda x: x['total_credits'], reverse=True)
    
    context = {
        'page_title': 'Employer Dashboard',
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_trips': total_trips,
        'pending_trips': pending_trips,
        'total_credits': total_credits,
        'credits_growth': credits_growth,
        'co2_saved': co2_saved,
        'tree_equivalent': tree_equivalent,
        'top_employees': top_employees,
    }
    
    return render(request, 'employer/dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def employees_list(request):
    """
    View for listing and managing employees.
    """
    # Get employees for this employer
    employees = request.user.employer_profile.employees.all().order_by('-created_at')
    
    # Get employee counts by status
    total_employees = employees.count()
    approved_employees = employees.filter(approved=True).count()
    pending_employees = employees.filter(approved=False).count()
    
    # Calculate active employees count (active in the last week)
    one_week_ago = timezone.now() - timedelta(days=7)
    employee_ids = employees.filter(approved=True).values_list('id', flat=True)
    active_employees_count = Trip.objects.filter(
        employee__in=employee_ids,
        start_time__gte=one_week_ago
    ).values('employee').distinct().count()
    
    # For each employee, get their carbon credit statistics
    for employee in employees:
        # Get trips for this employee
        employee_trips = Trip.objects.filter(employee=employee)
        
        # Calculate total credits earned
        employee.total_credits = employee_trips.aggregate(Sum('credits_earned'))['credits_earned__sum'] or 0
        
        # Calculate trip count
        employee.trip_count = employee_trips.count()
        
        # Calculate total CO2 saved
        employee.total_co2_saved = employee_trips.aggregate(Sum('carbon_savings'))['carbon_savings__sum'] or 0
    
    context = {
        'employees': employees,
        'total_employees': total_employees,
        'approved_employees': approved_employees,
        'pending_employees': pending_employees,
        'active_employees_count': active_employees_count,
        'page_title': 'Manage Employees',
    }
    
    return render(request, 'employer/employees.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def locations_list(request):
    """
    View for listing and managing office locations.
    """
    # Get locations for this employer
    employer_profile = request.user.employer_profile
    locations = employer_profile.office_locations.all().order_by('-created_at')
    
    # Get the primary location if any
    try:
        primary_location = locations.get(is_primary=True)
    except:
        primary_location = None
    
    # Count unique cities (based on addresses)
    city_count = len(set([loc.address.split(',')[-2].strip() for loc in locations if ',' in loc.address]))
    
    # Get Google Maps API key from settings
    from django.conf import settings
    maps_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    context = {
        'locations': locations,
        'primary_location': primary_location,
        'city_count': city_count,
        'maps_api_key': maps_api_key,
        'page_title': 'Manage Locations',
    }
    
    return render(request, 'employer/locations.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def location_add(request):
    """
    View for adding a new office location.
    """
    employer_profile = request.user.employer_profile
    
    if request.method == 'POST':
        name = request.POST.get('name')
        location_type = request.POST.get('location_type', 'office')
        address = request.POST.get('address')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Validate inputs
        if not all([name, location_type, address, latitude, longitude]):
            messages.error(request, "All fields are required.")
            return redirect('employer:locations')
        
        try:
            # Create new location
            from users.models import Location
            
            location = Location.objects.create(
                name=name,
                created_by=request.user,
                latitude=latitude,
                longitude=longitude,
                address=address,
                location_type=location_type,
                employer=employer_profile,
                is_primary=False
            )
            
            # If this is the first location, make it primary
            if employer_profile.office_locations.count() == 1:
                location.is_primary = True
                location.save()
                messages.success(request, f"Added {name} as your primary office location.")
            else:
                messages.success(request, f"Added new office location: {name}")
                
        except Exception as e:
            messages.error(request, f"Error adding location: {str(e)}")
    
    return redirect('employer:locations')

@login_required
@user_passes_test(lambda u: u.is_employer)
def location_edit(request, location_id):
    """
    View for editing an existing office location.
    """
    employer_profile = request.user.employer_profile
    
    try:
        # Get location and verify ownership
        location = get_object_or_404(Location, id=location_id, employer=employer_profile)
        
        if request.method == 'POST':
            name = request.POST.get('name')
            location_type = request.POST.get('location_type', 'office')
            address = request.POST.get('address')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            
            # Validate inputs
            if not all([name, location_type, address, latitude, longitude]):
                messages.error(request, "All fields are required.")
                return redirect('employer:locations')
            
            # Update location
            location.name = name
            location.location_type = location_type
            location.address = address
            location.latitude = latitude
            location.longitude = longitude
            location.save()
            
            messages.success(request, f"Updated location: {name}")
    
    except Location.DoesNotExist:
        messages.error(request, "Location not found.")
    except Exception as e:
        messages.error(request, f"Error updating location: {str(e)}")
    
    return redirect('employer:locations')

@login_required
@user_passes_test(lambda u: u.is_employer)
def location_delete(request, location_id):
    """
    View for deleting an office location.
    """
    employer_profile = request.user.employer_profile
    
    try:
        # Get location and verify ownership
        location = get_object_or_404(Location, id=location_id, employer=employer_profile)
        
        # Don't allow deleting primary locations
        if location.is_primary:
            messages.error(request, "Cannot delete the primary office location.")
            return redirect('employer:locations')
        
        location_name = location.name
        location.delete()
        
        messages.success(request, f"Deleted location: {location_name}")
    
    except Location.DoesNotExist:
        messages.error(request, "Location not found.")
    except Exception as e:
        messages.error(request, f"Error deleting location: {str(e)}")
    
    return redirect('employer:locations')

@login_required
@user_passes_test(lambda u: u.is_employer)
def location_set_primary(request, location_id):
    """
    View for setting a location as the primary office.
    """
    employer_profile = request.user.employer_profile
    
    try:
        # Get location and verify ownership
        location = get_object_or_404(Location, id=location_id, employer=employer_profile)
        
        # Clear primary flag from all locations for this employer
        employer_profile.office_locations.update(is_primary=False)
        
        # Set this location as primary
        location.is_primary = True
        location.save()
        
        messages.success(request, f"Set {location.name} as your primary office location.")
    
    except Location.DoesNotExist:
        messages.error(request, "Location not found.")
    except Exception as e:
        messages.error(request, f"Error setting primary location: {str(e)}")
    
    return redirect('employer:locations')

@login_required
@user_passes_test(lambda u: u.is_employer)
def trading(request):
    """
    View for carbon credit trading.
    """
    employer_profile = request.user.employer_profile
    
    # Get the employer's current carbon credit balance
    # This would typically be fetched from a balance system
    # For now, let's use a placeholder value or calculate from trips
    try:
        total_credits = CarbonCredit.objects.filter(
            owner_type='employer', 
            owner_id=employer_profile.id,
            status='active'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    except:
        total_credits = 0
    
    # Get active market offers (excluding the employer's own offers)
    market_offers = MarketOffer.objects.filter(
        status='active'
    ).exclude(
        seller=employer_profile
    ).order_by('-created_at')
    
    # Get the employer's transactions
    transactions = MarketplaceTransaction.objects.filter(
        Q(buyer=employer_profile) | Q(seller=employer_profile)
    ).order_by('-created_at')
    
    # Calculate total credits purchased
    total_purchased = transactions.filter(
        buyer=employer_profile,
        status__in=['approved', 'completed']
    ).aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
    
    # Get average market price
    avg_price = MarketOffer.objects.filter(
        status='active'
    ).aggregate(Avg('price_per_credit'))['price_per_credit__avg'] or 0
    
    # Get user's transaction notifications
    notifications = TransactionNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]  # Show latest 10 notifications
    
    context = {
        'page_title': 'Carbon Credit Trading',
        'market_offers': market_offers,
        'transactions': transactions,
        'total_credits': total_credits,
        'total_purchased': total_purchased,
        'avg_price': avg_price,
        'notifications': notifications,
    }
    
    return render(request, 'employer/trading.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def pending_trips(request):
    """
    View for approving pending trips from employees.
    """
    employer_profile = request.user.employer_profile
    employee_ids = employer_profile.employees.values_list('id', flat=True)
    
    pending_trips = Trip.objects.filter(
        employee__in=employee_ids,
        verification_status='pending'
    ).order_by('-start_time')
    
    context = {
        'pending_trips': pending_trips,
        'page_title': 'Pending Trip Approvals',
    }
    
    return render(request, 'employer/pending_trips.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def trip_approval(request, trip_id):
    """
    View for approving or rejecting a specific trip.
    """
    employer_profile = request.user.employer_profile
    employee_ids = employer_profile.employees.values_list('id', flat=True)
    
    try:
        trip = Trip.objects.get(id=trip_id, employee__in=employee_ids)
        action = request.POST.get('action')
        
        if action == 'approve':
            # Check if trip already has credits assigned
            if trip.credits_earned and trip.credits_earned > 0 and trip.verification_status != 'verified':
                # Check if employer has enough credits in their wallet
                employer_credits = CarbonCredit.objects.filter(
                    owner_type='employer',
                    owner_id=employer_profile.id,
                    status='active'
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                credits_to_award = trip.credits_earned
                
                if employer_credits >= credits_to_award:
                    # Update trip status
                    trip.verification_status = 'verified'
                    trip.verified_by = request.user
                    trip.save()
                    
                    # Find any pending credits for this trip and activate them
                    pending_credits = CarbonCredit.objects.filter(
                        source_trip=trip,
                        owner_type='employee',
                        owner_id=trip.employee.id,
                        status='pending'
                    )
                    
                    if pending_credits.exists():
                        for credit in pending_credits:
                            credit.status = 'active'
                            credit.save()
                    else:
                        # Create new credits for employee if none exist
                        CarbonCredit.objects.create(
                            amount=credits_to_award,
                            source_trip=trip,
                            owner_type='employee',
                            owner_id=trip.employee.id,
                            status='active',
                            expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
                        )
                    
                    # Deduct credits from employer's wallet
                    remaining_to_deduct = credits_to_award
                    employer_active_credits = CarbonCredit.objects.filter(
                        owner_type='employer',
                        owner_id=employer_profile.id,
                        status='active'
                    ).order_by('timestamp')  # Use oldest credits first
                    
                    for credit in employer_active_credits:
                        if remaining_to_deduct <= 0:
                            break
                            
                        if credit.amount <= remaining_to_deduct:
                            # Use the entire credit
                            credit.status = 'used'
                            credit.save()
                            remaining_to_deduct -= credit.amount
                        else:
                            # Split the credit
                            new_amount = credit.amount - remaining_to_deduct
                            
                            # Update the original credit
                            credit.amount = new_amount
                            credit.save()
                            
                            # Create a record of the used portion
                            CarbonCredit.objects.create(
                                amount=remaining_to_deduct,
                                source_trip=trip,
                                owner_type='employer',
                                owner_id=employer_profile.id,
                                timestamp=timezone.now(),
                                status='used',
                                expiry_date=credit.expiry_date
                            )
                            
                            remaining_to_deduct = 0
                    
                    messages.success(request, f"Trip approved and {credits_to_award} credits awarded to the employee.")
                else:
                    messages.error(request, f"Not enough credits in your wallet. You need {credits_to_award} credits but only have {employer_credits}.")
                    return redirect('employer:pending_trips')
            else:
                # Update trip status if no credits involved or already verified
                trip.verification_status = 'verified'
                trip.verified_by = request.user
                trip.save()
                messages.success(request, "Trip approved successfully.")
                
        elif action == 'reject':
            trip.verification_status = 'rejected'
            trip.save()
            
            # Cancel any pending credits for this trip
            pending_credits = CarbonCredit.objects.filter(
                source_trip=trip,
                owner_type='employee',
                status='pending'
            )
            
            for credit in pending_credits:
                credit.status = 'expired'
                credit.save()
            
            messages.success(request, "Trip rejected successfully.")
            
    except Trip.DoesNotExist:
        messages.error(request, "Trip not found.")
    
    return redirect('employer:pending_trips')

@login_required
@user_passes_test(lambda u: u.is_employer)
def create_transaction(request):
    """
    Handle the creation of a new transaction when a user buys credits.
    """
    if request.method != 'POST':
        return redirect('employer:trading')
        
    employer_profile = request.user.employer_profile
    
    # Get the offer ID and amount from the form
    offer_id = request.POST.get('offer_id')
    amount = request.POST.get('amount')
    
    try:
        # Convert amount to decimal
        credit_amount = float(amount)
        
        # Get the offer
        offer = get_object_or_404(MarketOffer, pk=offer_id, status='active')
        
        # Check if trying to buy from self
        if offer.seller == employer_profile:
            messages.error(request, "You cannot buy your own credits")
            return redirect('employer:trading')
            
        # Check if enough credits available
        if credit_amount > offer.credit_amount:
            messages.error(request, "Not enough credits available in this offer")
            return redirect('employer:trading')
        
        # Convert to Decimal for database operations
        credit_amount_decimal = Decimal(str(credit_amount))
        price_decimal = Decimal(str(offer.price_per_credit))
        total_price_decimal = credit_amount_decimal * price_decimal
            
        # Create the transaction
        transaction = MarketplaceTransaction.objects.create(
            offer=offer,
            seller=offer.seller,
            buyer=employer_profile,
            credit_amount=credit_amount_decimal,
            total_price=total_price_decimal,
            status='pending',
            admin_approval_required=True  # Require bank approval for all transactions
        )
        
        # If this purchase uses all remaining credits, mark offer as completed
        if credit_amount_decimal == offer.credit_amount:
            offer.status = 'completed'
            offer.save()
        # Otherwise, reduce the available credits
        else:
            offer.credit_amount -= credit_amount_decimal
            offer.total_price = offer.credit_amount * offer.price_per_credit
            offer.save()
        
        messages.success(
            request, 
            f"Successfully purchased {credit_amount} credits for ${total_price_decimal}. "
            f"Transaction #{transaction.id} is pending approval from the bank. "
            f"Credits will be added to your account once approved."
        )
        
    except ValueError:
        messages.error(request, "Invalid amount specified")
    except MarketOffer.DoesNotExist:
        messages.error(request, "The selected offer is no longer available")
    except Exception as e:
        messages.error(request, f"Error processing transaction: {str(e)}")
    
    return redirect('employer:trading')

@login_required
@user_passes_test(lambda u: u.is_employer)
def create_offer(request):
    """
    Handle the creation of a new market offer to sell credits.
    """
    if request.method != 'POST':
        return redirect('employer:trading')
        
    employer_profile = request.user.employer_profile
    
    # Get form data
    credit_amount = request.POST.get('credit_amount')
    price_per_credit = request.POST.get('price_per_credit')
    
    try:
        # Convert to float
        credit_amount = float(credit_amount)
        price_per_credit = float(price_per_credit)
        
        # Validate inputs
        if credit_amount <= 0:
            messages.error(request, "Credit amount must be positive")
            return redirect('employer:trading')
            
        if price_per_credit <= 0:
            messages.error(request, "Price per credit must be positive")
            return redirect('employer:trading')
        
        # Check if employer has enough credits
        available_credits = CarbonCredit.objects.filter(
            owner_type='employer', 
            owner_id=employer_profile.id,
            status='active'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        if credit_amount > available_credits:
            messages.error(request, f"You don't have enough credits. Available: {available_credits}")
            return redirect('employer:trading')
        
        # Calculate total price
        total_price = credit_amount * price_per_credit
        
        # Set expiry date to 30 days from now
        expiry_date = timezone.now() + timedelta(days=30)
        
        # Convert values to Decimal for DB operations
        credit_amount_decimal = Decimal(str(credit_amount))
        price_per_credit_decimal = Decimal(str(price_per_credit))
        total_price_decimal = Decimal(str(total_price))
        
        # Create the offer
        offer = MarketOffer.objects.create(
            seller=employer_profile,
            credit_amount=credit_amount_decimal,
            price_per_credit=price_per_credit_decimal,
            total_price=total_price_decimal,
            expiry_date=expiry_date,
            status='active'
        )
        
        # Reserve (deduct) the carbon credits from the user's account
        # Find available credits to deduct
        active_credits = CarbonCredit.objects.filter(
            owner_type='employer',
            owner_id=employer_profile.id,
            status='active'
        ).order_by('timestamp')  # Use oldest credits first (timestamp instead of created_at)
        
        remaining_to_deduct = credit_amount_decimal
        
        for credit in active_credits:
            if remaining_to_deduct <= 0:
                break
                
            if credit.amount <= remaining_to_deduct:
                # Use the entire credit
                credit.status = 'used'
                credit.save()
                remaining_to_deduct -= credit.amount
            else:
                # Split the credit
                # Use part of it and keep the rest active
                new_amount = credit.amount - remaining_to_deduct
                
                # Update the original credit
                credit.amount = new_amount
                credit.save()
                
                # Create a record of the used portion
                CarbonCredit.objects.create(
                    amount=remaining_to_deduct,
                    source_trip=credit.source_trip,
                    owner_type='employer',
                    owner_id=employer_profile.id,
                    timestamp=timezone.now(),
                    status='used',
                    expiry_date=credit.expiry_date
                )
                
                remaining_to_deduct = Decimal('0')
                
        messages.success(request, f"Successfully listed {credit_amount} credits for sale at ${price_per_credit} each.")
        return redirect('employer:trading')
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('employer:trading')

@login_required
@user_passes_test(lambda u: u.is_employer)
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read or unread.
    """
    if request.method != 'POST':
        return redirect('employer:trading')
    
    try:
        notification = TransactionNotification.objects.get(id=notification_id, user=request.user)
        
        # Toggle read status
        notification.is_read = not notification.is_read
        notification.save()
        
        if notification.is_read:
            messages.success(request, "Notification marked as read.")
        else:
            messages.success(request, "Notification marked as unread.")
            
    except TransactionNotification.DoesNotExist:
        messages.error(request, "Notification not found.")
    
    return redirect('employer:trading')

@login_required
@user_passes_test(lambda u: u.is_employer)
def employee_approval(request, employee_id):
    """
    View for approving or rejecting an employee.
    """
    employer_profile = request.user.employer_profile
    
    try:
        # Ensure the employee belongs to this employer
        employee = EmployeeProfile.objects.get(id=employee_id, employer=employer_profile)
        action = request.GET.get('action', '')
        
        if action == 'approve':
            employee.approved = True
            employee.save()
            
            # Also update the user's status
            employee.user.approved = True
            employee.user.save()
            
            messages.success(request, f"Successfully approved {employee.user.get_full_name()}")
            
        elif action == 'reject':
            # Optionally add rejection reason in the future
            employee_name = employee.user.get_full_name()
            employee_email = employee.user.email
            
            # Delete the employee profile and user
            user = employee.user
            employee.delete()
            user.delete()
            
            messages.success(request, f"Successfully rejected employee {employee_name} ({employee_email})")
            
    except EmployeeProfile.DoesNotExist:
        messages.error(request, "Employee not found")
    
    return redirect('employer:employees')

@login_required
@user_passes_test(lambda u: u.is_employer)
def invite_employee(request):
    """
    View for inviting a new employee by email.
    """
    if request.method != 'POST':
        return redirect('employer:employees')
    
    email = request.POST.get('email')
    department = request.POST.get('department', '')
    message = request.POST.get('message', '')
    
    if not email:
        messages.error(request, "Email address is required")
        return redirect('employer:employees')
        
    # Check if user with this email already exists
    if CustomUser.objects.filter(email=email).exists():
        messages.error(request, f"User with email {email} already exists")
        return redirect('employer:employees')
    
    try:
        # Generate a unique invitation token
        import uuid
        import datetime
        token = str(uuid.uuid4())
        
        # Create an invitation record (you would need to create this model)
        from users.models import EmployeeInvitation
        
        invitation = EmployeeInvitation.objects.create(
            employer=request.user.employer_profile,
            email=email,
            department=department,
            message=message,
            token=token,
            expires_at=timezone.now() + timezone.timedelta(days=7)  # 7 days expiry
        )
        
        # Send invitation email (would need email configuration)
        invitation_url = request.build_absolute_uri(
            reverse('users:employee_register') + f'?token={token}'
        )
        
        # Here you would normally send an email with the invitation_url
        # For now, just show a success message with the URL
        messages.success(
            request, 
            f"Invitation sent to {email}. Invitation link: {invitation_url}"
        )
        
    except Exception as e:
        messages.error(request, f"Error sending invitation: {str(e)}")
    
    return redirect('employer:employees')

# Profile views
@login_required
@user_passes_test(lambda u: u.is_employer)
def profile(request):
    """View for employer profile page."""
    # Get the employer profile associated with this user
    employer_profile = getattr(request.user, 'employer_profile', None)
    
    context = {
        'page_title': 'Employer Profile',
        'user': request.user,
        'employer_profile': employer_profile,
    }
    return render(request, 'employer/profile.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def update_profile(request):
    """Handle employer profile updates."""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        company_name = request.POST.get('company_name')
        industry = request.POST.get('industry')
        phone = request.POST.get('phone')
        website = request.POST.get('website')
        address = request.POST.get('address')
        
        # Validate email format
        if not email or '@' not in email:
            messages.error(request, "Please provide a valid email address.")
            return redirect('employer:profile')
        
        # Check if email is already in use by another user
        if CustomUser.objects.exclude(id=request.user.id).filter(email=email).exists():
            messages.error(request, "This email is already in use by another user.")
            return redirect('employer:profile')
        
        # Update user data
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        # Update employer profile if it exists
        employer_profile = getattr(user, 'employer_profile', None)
        if employer_profile:
            employer_profile.company_name = company_name
            employer_profile.industry = industry
            employer_profile.phone = phone
            employer_profile.website = website
            employer_profile.address = address
            employer_profile.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect('employer:profile')
    
    # For GET requests, redirect to profile page
    return redirect('employer:profile')

@login_required
@user_passes_test(lambda u: u.is_employer)
def change_password(request):
    """Handle employer password changes."""
    if request.method == 'POST':
        # Get form data
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate passwords
        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Please fill in all password fields.")
            return redirect('employer:profile')
        
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('employer:profile')
        
        # Check current password
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('employer:profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password changed successfully.")
        return redirect('employer:profile')
    
    # For GET requests, redirect to profile page
    return redirect('employer:profile')

@login_required
@user_passes_test(lambda u: u.is_employer)
def employee_marketplace(request):
    """
    View for handling employee credit trading requests.
    """
    employer_profile = request.user.employer_profile
    
    # Get pending credit offers from employees
    pending_offers = EmployeeCreditOffer.objects.filter(
        employer=employer_profile,
        status='pending'
    ).order_by('-created_at')
    
    # Get completed offers (processed in last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    completed_offers = EmployeeCreditOffer.objects.filter(
        employer=employer_profile,
        status__in=['approved', 'rejected', 'cancelled'],
        processed_at__gte=thirty_days_ago
    ).order_by('-processed_at')
    
    # Get employer credit balance
    employer_credits = CarbonCredit.objects.filter(
        owner_type='employer',
        owner_id=employer_profile.id,
        status='active'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get current market rate
    market_rate = MarketOffer.objects.filter(
        status='active'
    ).aggregate(Avg('price_per_credit'))['price_per_credit__avg'] or 5.0  # Default to $5 if no data
    
    context = {
        'page_title': 'Employee Credit Marketplace',
        'pending_offers': pending_offers,
        'completed_offers': completed_offers,
        'employer_credits': employer_credits,
        'market_rate': market_rate,
        'wallet_balance': employer_profile.wallet_balance
    }
    
    return render(request, 'employer/employee_marketplace.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def process_employee_offer(request, offer_id):
    """
    Process (approve/reject) an employee credit offer.
    """
    if request.method != 'POST':
        return redirect('employer:employee_marketplace')
    
    employer_profile = request.user.employer_profile
    action = request.POST.get('action')
    
    try:
        offer = get_object_or_404(
            EmployeeCreditOffer, 
            id=offer_id, 
            employer=employer_profile,
            status='pending'
        )
        
        employee = offer.employee
        credit_amount = offer.credit_amount
        total_amount = offer.total_amount
        
        if action == 'approve':
            # For employee selling credits to employer
            if offer.offer_type == 'sell':
                # Check if employee has enough credits
                employee_credits = CarbonCredit.objects.filter(
                    owner_type='employee',
                    owner_id=employee.id,
                    status='active'
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                if employee_credits < credit_amount:
                    messages.error(request, f"Employee doesn't have enough credits. Required: {credit_amount}, Available: {employee_credits}")
                    return redirect('employer:employee_marketplace')
                
                # Check if employer has enough wallet balance
                if employer_profile.wallet_balance < total_amount:
                    messages.error(request, f"Not enough balance in your wallet. Required: ${total_amount}, Available: ${employer_profile.wallet_balance}")
                    return redirect('employer:employee_marketplace')
                
                # Transfer credits from employee to employer
                remaining_to_transfer = credit_amount
                employee_active_credits = CarbonCredit.objects.filter(
                    owner_type='employee',
                    owner_id=employee.id,
                    status='active'
                ).order_by('timestamp')  # Use oldest credits first
                
                for credit in employee_active_credits:
                    if remaining_to_transfer <= 0:
                        break
                        
                    if credit.amount <= remaining_to_transfer:
                        # Use the entire credit
                        credit.status = 'used'
                        credit.save()
                        
                        # Create a new credit for the employer
                        CarbonCredit.objects.create(
                            amount=credit.amount,
                            source_trip=credit.source_trip,
                            owner_type='employer',
                            owner_id=employer_profile.id,
                            timestamp=timezone.now(),
                            status='active',
                            expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
                        )
                        
                        remaining_to_transfer -= credit.amount
                    else:
                        # Split the credit
                        new_amount = credit.amount - remaining_to_transfer
                        
                        # Update the original credit
                        credit.amount = new_amount
                        credit.save()
                        
                        # Create a used credit record for the employee
                        CarbonCredit.objects.create(
                            amount=remaining_to_transfer,
                            source_trip=credit.source_trip,
                            owner_type='employee',
                            owner_id=employee.id,
                            timestamp=timezone.now(),
                            status='used',
                            expiry_date=credit.expiry_date
                        )
                        
                        # Create a new credit for the employer
                        CarbonCredit.objects.create(
                            amount=remaining_to_transfer,
                            source_trip=credit.source_trip,
                            owner_type='employer',
                            owner_id=employer_profile.id,
                            timestamp=timezone.now(),
                            status='active',
                            expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
                        )
                        
                        remaining_to_transfer = 0
                
                # Transfer money to employee's wallet
                employee.wallet_balance += total_amount
                employee.save()
                
                # Deduct from employer's wallet
                employer_profile.wallet_balance -= total_amount
                employer_profile.save()
                
                messages.success(request, f"Successfully bought {credit_amount} credits from {employee.user.get_full_name()} for ${total_amount}.")
                
            # For employee buying credits from employer
            else:
                # Check if employer has enough credits
                employer_credits = CarbonCredit.objects.filter(
                    owner_type='employer',
                    owner_id=employer_profile.id,
                    status='active'
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                if employer_credits < credit_amount:
                    messages.error(request, f"You don't have enough credits. Required: {credit_amount}, Available: {employer_credits}")
                    return redirect('employer:employee_marketplace')
                
                # Check if employee has enough wallet balance
                if employee.wallet_balance < total_amount:
                    messages.error(request, f"Employee doesn't have enough balance in their wallet. Required: ${total_amount}, Available: ${employee.wallet_balance}")
                    return redirect('employer:employee_marketplace')
                
                # Transfer credits from employer to employee
                remaining_to_transfer = credit_amount
                employer_active_credits = CarbonCredit.objects.filter(
                    owner_type='employer',
                    owner_id=employer_profile.id,
                    status='active'
                ).order_by('timestamp')  # Use oldest credits first
                
                for credit in employer_active_credits:
                    if remaining_to_transfer <= 0:
                        break
                        
                    if credit.amount <= remaining_to_transfer:
                        # Use the entire credit
                        credit.status = 'used'
                        credit.save()
                        
                        # Create a new credit for the employee
                        CarbonCredit.objects.create(
                            amount=credit.amount,
                            source_trip=credit.source_trip,
                            owner_type='employee',
                            owner_id=employee.id,
                            timestamp=timezone.now(),
                            status='active',
                            expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
                        )
                        
                        remaining_to_transfer -= credit.amount
                    else:
                        # Split the credit
                        new_amount = credit.amount - remaining_to_transfer
                        
                        # Update the original credit
                        credit.amount = new_amount
                        credit.save()
                        
                        # Create a used credit record for the employer
                        CarbonCredit.objects.create(
                            amount=remaining_to_transfer,
                            source_trip=credit.source_trip,
                            owner_type='employer',
                            owner_id=employer_profile.id,
                            timestamp=timezone.now(),
                            status='used',
                            expiry_date=credit.expiry_date
                        )
                        
                        # Create a new credit for the employee
                        CarbonCredit.objects.create(
                            amount=remaining_to_transfer,
                            source_trip=credit.source_trip,
                            owner_type='employee',
                            owner_id=employee.id,
                            timestamp=timezone.now(),
                            status='active',
                            expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
                        )
                        
                        remaining_to_transfer = 0
                
                # Transfer money from employee's wallet to employer's
                employee.wallet_balance -= total_amount
                employee.save()
                
                # Add to employer's wallet
                employer_profile.wallet_balance += total_amount
                employer_profile.save()
                
                messages.success(request, f"Successfully sold {credit_amount} credits to {employee.user.get_full_name()} for ${total_amount}.")
            
            # Update offer status
            offer.status = 'approved'
            offer.processed_at = timezone.now()
            offer.save()
            
        elif action == 'reject':
            offer.status = 'rejected'
            offer.processed_at = timezone.now()
            offer.save()
            
            messages.success(request, f"Offer from {employee.user.get_full_name()} rejected.")
            
    except EmployeeCreditOffer.DoesNotExist:
        messages.error(request, "Offer not found or already processed.")
    except Exception as e:
        messages.error(request, f"Error processing offer: {str(e)}")
    
    return redirect('employer:employee_marketplace') 