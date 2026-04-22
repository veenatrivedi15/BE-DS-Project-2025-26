from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from users.models import CustomUser, EmployerProfile, Location
from trips.models import Trip, CarbonCredit
from marketplace.models import MarketplaceTransaction, MarketOffer
from django.db.models import Sum, Count, Avg, Case, When, Value, IntegerField, F, Q, Max, Min
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib import messages
from django.core.paginator import Paginator
import csv
import io
from django.utils.decorators import method_decorator
from users.decorators import bank_required
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db import models

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def dashboard(request):
    """
    Dashboard view for bank administrators.
    """
    # Get basic statistics
    total_users = CustomUser.objects.count()
    total_employers = EmployerProfile.objects.count()
    pending_approvals = EmployerProfile.objects.filter(approved=False).count()
    
    # Credit statistics
    total_credits_raw = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_credits = round(float(total_credits_raw), 2)  # Round to 2 decimal places
    
    # Recent credits (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_credits = CarbonCredit.objects.filter(timestamp__gte=seven_days_ago).aggregate(Sum('amount'))['amount__sum'] or 0
    recent_credits = round(float(recent_credits), 2)
    
    # Trip statistics
    total_trips = Trip.objects.count()
    
    # Use verification_status field in the filter
    verified_trips_count = Trip.objects.filter(verification_status='verified').count()
    
    # Transaction statistics
    transaction_count = MarketplaceTransaction.objects.count()
    
    # Location count
    location_count = Location.objects.count()
    
    # Market value calculation - fixed to use direct price calculation instead of accessing offer__price_per_credit
    avg_price = MarketplaceTransaction.objects.filter(
        status='completed'
    ).aggregate(avg_price=Avg(F('total_price') / F('credit_amount')))['avg_price'] or 0
    
    market_value = round(float(avg_price * total_credits_raw), 2)
    
    context = {
        'total_users': total_users,
        'total_employers': total_employers,
        'employer_count': total_employers,  # Add employer count
        'pending_approvals': pending_approvals,
        'total_credits': total_credits,
        'recent_credits': recent_credits,  # Add recent credits
        'total_trips': total_trips,
        'verified_trips': verified_trips_count,
        'transactions': transaction_count,
        'transaction_count': transaction_count,  # Add transaction count
        'location_count': location_count,  # Add location count
        'market_value': market_value,  # Add market value
        'page_title': 'Bank Admin Dashboard',
    }
    
    # Get pending employer approvals for the quick view
    pending_employers = EmployerProfile.objects.filter(approved=False).order_by('-created_at')[:5]
    context['pending_employers'] = pending_employers
    
    return render(request, 'bank/dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def dashboard_analytics(request):
    """
    API endpoint for dashboard analytics data (JSON response for charts)
    """
    # Get date range (default: last 30 days)
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Credits issued per day
    credits_per_day = (
        CarbonCredit.objects
        .filter(timestamp__gte=start_date)
        .extra(select={'day': "DATE(timestamp)"})
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    
    # If no data, create sample data points
    if not credits_per_day:
        # Generate sample data for the requested date range
        sample_credits = []
        for i in range(days):
            current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            # Random value between 0.5 and 5
            sample_credits.append({
                'day': current_date,
                'total': round(float(i % 5) + 0.5 + (i % 3), 2)  # Simple pattern with some variation
            })
        credits_per_day = sample_credits
    
    # Trips logged per day
    trips_per_day = (
        Trip.objects
        .filter(start_time__gte=start_date)
        .extra(select={'day': "DATE(start_time)"})
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    
    # Transport modes distribution
    transport_modes = (
        Trip.objects
        .filter(start_time__gte=start_date)
        .values('transport_mode')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # If no transport modes data, create sample data
    if not transport_modes:
        transport_modes = [
            {'transport_mode': 'bicycle', 'count': 12},
            {'transport_mode': 'work_from_home', 'count': 8},
            {'transport_mode': 'walking', 'count': 6},
            {'transport_mode': 'public_transport', 'count': 5},
            {'transport_mode': 'car', 'count': 3},
        ]
    
    # Transaction volume per day
    transactions_per_day = (
        MarketplaceTransaction.objects
        .filter(created_at__gte=start_date)
        .extra(select={'day': "DATE(created_at)"})
        .values('day')
        .annotate(count=Count('id'), volume=Sum('credit_amount'))
        .order_by('day')
    )
    
    return JsonResponse({
        'credits_per_day': list(credits_per_day),
        'trips_per_day': list(trips_per_day),
        'transport_modes': list(transport_modes),
        'transactions_per_day': list(transactions_per_day),
    })

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def employers_list(request):
    """
    View for listing and managing employers.
    """
    # Filter by approval status if requested
    approval_filter = request.GET.get('filter')
    
    if approval_filter == 'pending':
        employers = EmployerProfile.objects.filter(approved=False).order_by('-created_at')
    elif approval_filter == 'approved':
        employers = EmployerProfile.objects.filter(approved=True).order_by('-created_at')
    else:
        employers = EmployerProfile.objects.all().order_by('-created_at')
    
    context = {
        'employers': employers,
        'page_title': 'Manage Employers',
        'current_filter': approval_filter,
    }
    
    return render(request, 'bank/employers.html', context)

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def employer_approval(request, employer_id):
    """
    View for approving or rejecting an employer.
    """
    try:
        employer = EmployerProfile.objects.get(id=employer_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            employer.approved = True
            employer.save()
            # Also update the user's status
            employer.user.approved = True
            employer.user.save()
            return redirect('bank:bank_employers')
        elif action == 'reject':
            # Maybe add rejection notes in the future
            employer.delete()
            return redirect('bank:bank_employers')
            
    except EmployerProfile.DoesNotExist:
        pass
    
    return redirect('bank:bank_employers')

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def trading(request):
    """
    View for carbon credit trading platform.
    """
    # Get recent transactions
    recent_transactions = MarketplaceTransaction.objects.all().order_by('-created_at')[:10]
    
    # Get transaction statistics
    total_volume_raw = MarketplaceTransaction.objects.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
    # Format the total volume to avoid overflow
    total_volume = round(float(total_volume_raw), 2)
    
    pending_approvals = MarketplaceTransaction.objects.filter(status='pending').count()
    completed_transactions = MarketplaceTransaction.objects.filter(status='completed').count()
    
    # Get pending transactions for approval tab
    pending_transactions = MarketplaceTransaction.objects.filter(status='pending').order_by('-created_at')
    
    # Add mock pending transactions if none exist
    if not pending_transactions:
        # Create some mock pending transactions
        from datetime import datetime, timedelta
        import uuid
        
        mock_transactions = []
        buyers = ["Alpha Corp", "Beta Group", "Gamma Enterprises"]
        sellers = ["EcoTech Inc.", "Green Solutions", "Sustainable Energy"]
        
        for i in range(3):
            # Create a mock transaction for display purposes only
            mock_transaction = type('MockTransaction', (), {
                'id': uuid.uuid4().int % 10000,
                'seller': type('MockSeller', (), {'company_name': sellers[i]}),
                'buyer': type('MockBuyer', (), {'company_name': buyers[i]}),
                'credit_amount': (i+1) * 20,
                'price_per_credit': round(10 + (i * 1.2), 2),
                'total_price': round((i+1) * 20 * (10 + (i * 1.2)), 2),
                'created_at': datetime.now() - timedelta(hours=i * 4),
                'status': 'pending'
            })
            mock_transactions.append(mock_transaction)
        
        # Use mock transactions instead of database transactions
        pending_transactions = mock_transactions
    
    # Get completed transactions for history tab
    completed_transaction_records = MarketplaceTransaction.objects.filter(status='completed').order_by('-completed_at')[:20]
    
    # Check if there are any pending transactions in the recent_transactions list
    has_pending_transactions = any(transaction.status == 'pending' for transaction in recent_transactions)
    
    # Get real available credit offers from MarketOffer model
    available_credits = MarketOffer.objects.filter(status='active').order_by('-created_at')[:10]
    
    # Mock market offers if none exist (for demo purposes)
    if not available_credits:
        # Check if we have at least one employer to use for mock data
        employers = EmployerProfile.objects.all()
        if employers.exists():
            employer = employers.first()
            
            # Create some mock market offers
            from datetime import datetime, timedelta
            import uuid
            
            mock_offers = []
            companies = ["EcoTech Inc.", "Green Solutions", "Sustainable Energy", "EcoTransport"]
            
            for i, company in enumerate(companies):
                # Create a mock offer for display purposes only
                mock_offer = type('MockOffer', (), {
                    'id': uuid.uuid4().int % 10000,
                    'seller': type('MockSeller', (), {'company_name': company}),
                    'credit_amount': (i+1) * 25,
                    'price_per_credit': round(10 + (i * 1.5), 2),
                    'total_price': round((i+1) * 25 * (10 + (i * 1.5)), 2),
                    'created_at': datetime.now() - timedelta(days=i),
                    'status': 'active'
                })
                mock_offers.append(mock_offer)
            
            # Use mock offers instead of database offers
            available_credits = mock_offers
    
    # Mock data for top traders (since we don't have the actual query for this)
    top_traders = [
        {'company_name': 'EcoTech Inc.', 'bought': 150, 'sold': 75, 'net': 75},
        {'company_name': 'Green Solutions', 'bought': 120, 'sold': 200, 'net': -80},
        {'company_name': 'Sustainable Energy', 'bought': 85, 'sold': 40, 'net': 45},
        {'company_name': 'EcoTransport', 'bought': 60, 'sold': 90, 'net': -30},
    ]
    
    # Calculate real market stats
    avg_price = MarketOffer.objects.filter(status='active').aggregate(Avg('price_per_credit'))['price_per_credit__avg'] or 0
    available_credits_count = MarketOffer.objects.filter(status='active').aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
    seller_count = MarketOffer.objects.filter(status='active').values('seller').distinct().count()
    
    # If no real market stats, use mock data
    if avg_price == 0 and available_credits:
        avg_price = sum(offer.price_per_credit for offer in available_credits) / len(available_credits)
        available_credits_count = sum(offer.credit_amount for offer in available_credits)
        seller_count = len(set(offer.seller.company_name for offer in available_credits))
    
    market_stats = {
        'avg_price': round(avg_price, 2),
        'total_volume': total_volume,
        'available_credits': available_credits_count,
        'seller_count': seller_count
    }
    
    context = {
        'page_title': 'Carbon Credit Trading',
        'recent_transactions': recent_transactions,
        'pending_transactions': pending_transactions,
        'completed_transactions': completed_transaction_records,
        'total_volume': total_volume,
        'pending_approvals': pending_approvals,
        'completed_transactions_count': completed_transactions,
        'has_pending_transactions': has_pending_transactions,
        'top_traders': top_traders,
        'market_stats': market_stats,
        'available_credits': available_credits,
        'market_offers': available_credits,  # Add market_offers as an alias for available_credits
    }
    
    return render(request, 'bank/trading.html', context)

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def transaction_approval(request, transaction_id):
    """
    View for approving or rejecting a transaction.
    """
    try:
        transaction = MarketplaceTransaction.objects.get(id=transaction_id)
        action = request.GET.get('action', '')  # Get action from query parameter
        
        if action == 'approve':
            # Update transaction status
            transaction.status = 'completed'
            transaction.approved_by = request.user
            transaction.completed_at = timezone.now()
            transaction.save()
            
            # Add the carbon credits to the buyer's account
            CarbonCredit.objects.create(
                amount=transaction.credit_amount,
                source_trip=None,
                owner_type='employer',
                owner_id=transaction.buyer.id,
                timestamp=timezone.now(),
                status='active',
                expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
            )
            
            # Notify the users
            messages.success(request, f"Transaction #{transaction.id} approved successfully. {transaction.credit_amount} credits transferred to {transaction.buyer.company_name}.")
            return redirect('bank:bank_trading')
            
        elif action == 'reject':
            transaction.status = 'rejected'
            transaction.save()
            
            # Return the credits to the seller's offer
            offer = transaction.offer
            if offer.status != 'cancelled' and offer.status != 'expired':
                offer.credit_amount += transaction.credit_amount
                offer.total_price = offer.credit_amount * offer.price_per_credit
                # If the offer was completed, set it back to active
                if offer.status == 'completed':
                    offer.status = 'active'
                offer.save()
            
            messages.success(request, f"Transaction #{transaction.id} rejected. Credits returned to the marketplace.")
            return redirect('bank:bank_trading')
            
    except MarketplaceTransaction.DoesNotExist:
        messages.error(request, "Transaction not found.")
    
    return redirect('bank:bank_trading')

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def buy_credits(request):
    """
    View for bank admins to buy carbon credits.
    """
    if request.method == 'POST':
        offer_id = request.POST.get('buyOfferId')
        credit_amount = request.POST.get('creditAmount')
        price_per_credit = request.POST.get('pricePerCredit')
        total_price = request.POST.get('totalPrice')
        
        try:
            # Get the offer
            offer = MarketOffer.objects.get(id=offer_id)
            
            # Check if offer is active
            if offer.status != 'active':
                messages.error(request, "This offer is no longer active")
                return redirect('bank:bank_trading')
                
            # Check if enough credits available
            if int(credit_amount) > offer.credit_amount:
                messages.error(request, "Not enough credits available in this offer")
                return redirect('bank:bank_trading')
            
            # Create the transaction
            transaction = MarketplaceTransaction.objects.create(
                offer=offer,
                seller=offer.seller,
                buyer=request.user.employer_profile,
                credit_amount=int(credit_amount),
                price_per_credit=float(price_per_credit),
                total_price=float(total_price),
                status='pending'
            )
            
            # If this purchase uses all remaining credits, mark offer as completed
            if int(credit_amount) == offer.credit_amount:
                offer.status = 'completed'
                offer.save()
            # Otherwise, reduce the available credits
            else:
                offer.credit_amount -= int(credit_amount)
                offer.total_price = offer.credit_amount * offer.price_per_credit
                offer.save()
                
            messages.success(request, f"Successfully placed order for {credit_amount} credits")
            
        except MarketOffer.DoesNotExist:
            messages.error(request, "The selected offer no longer exists")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    return redirect('bank:bank_trading')

# Profile views
@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def profile(request):
    """View for bank admin profile page."""
    context = {
        'page_title': 'Bank Admin Profile',
        'user': request.user,
    }
    return render(request, 'bank/profile.html', context)

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def update_profile(request):
    """Handle bank admin profile updates."""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        # Validate email format
        if not email or '@' not in email:
            messages.error(request, "Please provide a valid email address.")
            return redirect('bank:profile')
        
        # Check if email is already in use by another user
        if CustomUser.objects.exclude(id=request.user.id).filter(email=email).exists():
            messages.error(request, "This email is already in use by another user.")
            return redirect('bank:profile')
        
        # Update user data
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect('bank:profile')
    
    # For GET requests, redirect to profile page
    return redirect('bank:profile')

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def change_password(request):
    """Handle bank admin password changes."""
    if request.method == 'POST':
        # Get form data
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate passwords
        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Please fill in all password fields.")
            return redirect('bank:profile')
        
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('bank:profile')
        
        # Check current password
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('bank:profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password changed successfully.")
        return redirect('bank:profile')
    
    # For GET requests, redirect to profile page
    return redirect('bank:profile')

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def reports(request):
    """
    Reports view for bank administrators
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
        # Transaction statistics
        total_transactions = MarketplaceTransaction.objects.count()
        total_volume = MarketplaceTransaction.objects.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
        
        # Credits statistics
        total_credits = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Get the average price per credit from completed transactions
        avg_price_per_credit = (
            MarketplaceTransaction.objects
            .filter(status='completed')
            .aggregate(avg_price=Avg('price_per_credit'))['avg_price'] or 0
        )
        
        # Count transactions by status
        completed_transactions = MarketplaceTransaction.objects.filter(status='completed').count()
        pending_transactions = MarketplaceTransaction.objects.filter(status='pending').count()
        
        # Add stats to context
        context.update({
            'total_transactions': total_transactions,
            'total_volume': total_volume,
            'total_credits': total_credits,
            'avg_price_per_credit': round(avg_price_per_credit, 2),
            'completed_transactions': completed_transactions,
            'pending_transactions': pending_transactions,
        })
    
    return render(request, 'bank/reports.html', context)

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
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
        # Transaction statistics
        total_transactions = MarketplaceTransaction.objects.count()
        total_volume = MarketplaceTransaction.objects.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
        
        # Credits statistics
        total_credits = CarbonCredit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Get the average price per credit from completed transactions
        avg_price_per_credit = (
            MarketplaceTransaction.objects
            .filter(status='completed')
            .aggregate(avg_price=Avg('price_per_credit'))['avg_price'] or 0
        )
        
        # Count transactions by status
        completed_transactions = MarketplaceTransaction.objects.filter(status='completed').count()
        pending_transactions = MarketplaceTransaction.objects.filter(status='pending').count()
        
        # Summary data
        data = [
            ['Metric', 'Value'],
            ['Total Transactions', total_transactions],
            ['Total Trading Volume', total_volume],
            ['Total Credits', total_credits],
            ['Average Price per Credit', round(avg_price_per_credit, 2)],
            ['Completed Transactions', completed_transactions],
            ['Pending Transactions', pending_transactions]
        ]
    
    elif report_type == 'transactions':
        # Get transactions based on date range
        transactions = MarketplaceTransaction.objects.all().order_by('-created_at')
        
        # Apply date filter if needed
        if date_range == '7d':
            transactions = transactions.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif date_range == '30d':
            transactions = transactions.filter(created_at__gte=timezone.now() - timedelta(days=30))
        elif date_range == '90d':
            transactions = transactions.filter(created_at__gte=timezone.now() - timedelta(days=90))
        
        # Headers
        data.append(['Transaction ID', 'Seller', 'Buyer', 'Credits', 'Price per Credit', 'Total Price', 'Status', 'Created', 'Completed'])
        
        # Transaction data
        for transaction in transactions:
            data.append([
                transaction.id,
                transaction.seller.company_name if transaction.seller else 'N/A',
                transaction.buyer.company_name if transaction.buyer else 'N/A',
                transaction.credit_amount,
                transaction.price_per_credit,
                transaction.total_price,
                transaction.status,
                transaction.created_at.strftime('%Y-%m-%d %H:%M') if transaction.created_at else 'N/A',
                transaction.completed_at.strftime('%Y-%m-%d %H:%M') if transaction.completed_at else 'N/A'
            ])
    
    # Generate export based on format
    if format == 'csv':
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="carbon_trading_{report_type}_report.csv"'
        
        # Write CSV data
        writer = csv.writer(response)
        for row in data:
            writer.writerow(row)
        
        return response
    
    elif format == 'pdf':
        # For PDF, a more complex implementation would be needed with a PDF library
        # This is a simplified version that returns a text response
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="carbon_trading_{report_type}_report.txt"'
        
        # Write data as text
        output = io.StringIO()
        for row in data:
            output.write('\t'.join([str(item) for item in row]) + '\n')
        
        response.write(output.getvalue())
        return response
    
    # Default fallback - return JSON
    return JsonResponse({'data': data})

# Transactions view
@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def transactions(request):
    """View for bank transactions page."""
    # Filter parameters
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'date')
    sort_dir = request.GET.get('dir', 'desc')
    
    # Get all transactions
    transactions_qs = MarketplaceTransaction.objects.all()
    
    # Apply filters
    if status_filter:
        transactions_qs = transactions_qs.filter(status=status_filter)
    
    # Apply sorting
    if sort_by == 'date':
        order_field = 'created_at' if sort_dir == 'asc' else '-created_at'
    elif sort_by == 'amount':
        order_field = 'credit_amount' if sort_dir == 'asc' else '-credit_amount'
    elif sort_by == 'price':
        order_field = 'total_price' if sort_dir == 'asc' else '-total_price'
    else:
        order_field = '-created_at'  # Default sorting
    
    transactions_qs = transactions_qs.order_by(order_field)
    
    # Pagination
    paginator = Paginator(transactions_qs, 10)
    page_number = request.GET.get('page', 1)
    transactions_page = paginator.get_page(page_number)
    
    # Context
    context = {
        'page_title': 'Carbon Credit Transactions',
        'transactions': transactions_page,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
    }
    
    return render(request, 'bank/transactions.html', context)

class BankDashboardView(View):
    @method_decorator(login_required)
    @method_decorator(bank_required)
    def get(self, request):
        context = {
            'page_title': 'Bank Dashboard',
        }
        return render(request, 'bank/dashboard.html', context)

@method_decorator([login_required, bank_required], name='dispatch')
class BankReportsView(View):
    """View for generating and displaying various bank reports"""
    
    def get(self, request):
        """Display the reports page"""
        context = {
            'page_title': 'Reports',
            'active_page': 'reports',
        }
        return render(request, 'bank/reports.html', context)
    
    def post(self, request):
        """Generate report content based on form data"""
        report_type = request.POST.get('report_type', '')
        date_range = request.POST.get('date_range', '7d')
        
        # Calculate the date range
        end_date = timezone.now()
        if date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        elif date_range == '1y':
            start_date = end_date - timedelta(days=365)
        else:
            # Default to 7 days
            start_date = end_date - timedelta(days=7)
        
        # Get report data based on type
        context = self._get_report_data(report_type, start_date, end_date)
        
        # Add report type to context
        context['report_type'] = report_type
        
        # Render only the report content partial
        return render(request, 'bank/partials/report_content.html', context)
    
    def _get_report_data(self, report_type, start_date, end_date):
        """Get data for the specified report type and date range"""
        context = {}
        
        # Filter transactions by date range
        transactions = MarketplaceTransaction.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        if report_type == 'summary':
            # Summary report data
            total_transactions = transactions.count()
            total_volume = transactions.aggregate(total=Sum('credit_amount'))['total'] or 0
            total_value = transactions.aggregate(total=Sum('total_price'))['total'] or 0
            avg_price = transactions.aggregate(avg=Avg(F('total_price') / F('credit_amount')))['avg'] or 0
            buy_count = transactions.count()
            sell_count = transactions.count()
            
            context.update({
                'total_transactions': total_transactions,
                'total_volume': total_volume,
                'total_value': total_value,
                'avg_price': avg_price,
                'buy_count': buy_count,
                'sell_count': sell_count,
            })
            
        elif report_type == 'transactions':
            # Transaction report data - list all transactions
            context['transactions'] = transactions.order_by('-created_at')
            
        elif report_type == 'price':
            # Price analytics report
            latest_transaction = transactions.order_by('-created_at').first()
            current_price = latest_transaction.total_price / latest_transaction.credit_amount if latest_transaction else 0
            avg_price = transactions.aggregate(avg=Avg(F('total_price') / F('credit_amount')))['avg'] or 0
            highest_price = transactions.annotate(price=F('total_price') / F('credit_amount')).aggregate(max=Max('price'))['max'] or 0
            lowest_price = transactions.annotate(price=F('total_price') / F('credit_amount')).aggregate(min=Min('price'))['min'] or 0
            
            # Group by day for price changes
            daily_prices = []
            # Implementation of daily price changes would go here
            # This would typically involve more complex queries with aggregation by date
            
            context.update({
                'current_price': current_price,
                'avg_price': avg_price,
                'highest_price': highest_price,
                'lowest_price': lowest_price,
                'price_changes': daily_prices,
            })
            
        elif report_type == 'employer_activity':
            # Employer activity report
            # Get top buyers and sellers by volume
            top_buyers = transactions.values('buyer__company_name').annotate(
                transaction_count=Count('id'),
                volume=Sum('credit_amount'),
                total_value=Sum('total_price')
            ).order_by('-volume')[:5]
            
            top_sellers = transactions.values('seller__company_name').annotate(
                transaction_count=Count('id'),
                volume=Sum('credit_amount'),
                total_value=Sum('total_price')
            ).order_by('-volume')[:5]
            
            context.update({
                'top_buyers': top_buyers,
                'top_sellers': top_sellers,
            })
            
        return context

@login_required
@bank_required
def export_report(request, report_type, date_range, format_type):
    """Export a report in the specified format"""
    # Calculate the date range
    end_date = timezone.now()
    if date_range == '7d':
        start_date = end_date - timedelta(days=7)
    elif date_range == '30d':
        start_date = end_date - timedelta(days=30)
    elif date_range == '90d':
        start_date = end_date - timedelta(days=90)
    elif date_range == '1y':
        start_date = end_date - timedelta(days=365)
    else:
        # Default to 7 days
        start_date = end_date - timedelta(days=7)
    
    # Get transactions for the specified date range
    transactions = MarketplaceTransaction.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('-created_at')
    
    if format_type == 'csv':
        # Generate CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{date_range}.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'summary':
            # Summary report CSV
            writer.writerow(['Report Type', 'Date Range', 'Generated At'])
            writer.writerow(['Summary Report', date_range, timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            total_transactions = transactions.count()
            total_volume = transactions.aggregate(total=Sum('credit_amount'))['total'] or 0
            total_value = transactions.aggregate(total=Sum('total_price'))['total'] or 0
            avg_price = transactions.aggregate(avg=Avg(F('total_price') / F('credit_amount')))['avg'] or 0
            buy_count = transactions.count()
            sell_count = transactions.count()
            
            writer.writerow(['Total Transactions', 'Total Volume', 'Total Value', 'Avg. Price', 'Buy Transactions', 'Sell Transactions'])
            writer.writerow([total_transactions, total_volume, total_value, avg_price, buy_count, sell_count])
            
        elif report_type == 'transactions':
            # Transaction report CSV
            writer.writerow(['Date', 'Transaction ID', 'Buyer', 'Seller', 'Volume', 'Price', 'Total Value', 'Status'])
            
            for transaction in transactions:
                # Calculate price per credit from total price and credit amount
                price_per_credit = transaction.total_price / transaction.credit_amount if transaction.credit_amount > 0 else 0
                
                writer.writerow([
                    transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    transaction.id,
                    transaction.buyer.company_name if transaction.buyer else 'N/A',
                    transaction.seller.company_name if transaction.seller else 'N/A',
                    transaction.credit_amount,
                    round(price_per_credit, 2),
                    transaction.total_price,
                    transaction.status
                ])
                
        elif report_type == 'price':
            # Price report CSV
            writer.writerow(['Date', 'Price'])
            
            # Group by day for price data
            # This is a simplified example - in a real application, you would aggregate by day
            for transaction in transactions:
                if transaction.credit_amount > 0:
                    price_per_credit = transaction.total_price / transaction.credit_amount
                    writer.writerow([
                        transaction.created_at.strftime('%Y-%m-%d'),
                        round(price_per_credit, 2)
                    ])
                
        elif report_type == 'employer_activity':
            # Employer activity CSV
            writer.writerow(['Employer', 'Total Buy Volume', 'Total Sell Volume'])
            
            # This is a simplified example - in a real application, you would 
            # aggregate by employer with more complex queries
            employers = {}
            
            # Get buy data
            buyer_data = transactions.values('buyer__company_name').annotate(
                buy_volume=Sum('credit_amount')
            )
            for item in buyer_data:
                company_name = item['buyer__company_name']
                if company_name not in employers:
                    employers[company_name] = {'buy': 0, 'sell': 0}
                employers[company_name]['buy'] = item['buy_volume']
            
            # Get sell data
            seller_data = transactions.values('seller__company_name').annotate(
                sell_volume=Sum('credit_amount')
            )
            for item in seller_data:
                company_name = item['seller__company_name']
                if company_name not in employers:
                    employers[company_name] = {'buy': 0, 'sell': 0}
                employers[company_name]['sell'] = item['sell_volume']
            
            for employer, data in employers.items():
                writer.writerow([
                    employer,
                    data['buy'],
                    data['sell']
                ])
        
        return response
        
    elif format_type == 'pdf':
        # In a real application, you would use a PDF library like ReportLab or WeasyPrint
        # For this example, we'll return a simple message
        return HttpResponse("PDF export would be implemented here with a PDF generation library.")
    
    # Default response if format isn't supported
    return redirect('bank:bank_reports')

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def generate_report(request):
    """
    API endpoint for generating report data via HTMX
    """
    report_type = request.GET.get('report-type', 'summary')
    date_range = request.GET.get('date-range', '7d')
    
    # Get date range in actual dates
    today = datetime.now().date()
    if date_range == '7d':
        start_date = today - timedelta(days=7)
    elif date_range == '30d':
        start_date = today - timedelta(days=30)
    elif date_range == '90d':
        start_date = today - timedelta(days=90)
    elif date_range == '1y':
        start_date = today - timedelta(days=365)
    else:  # All time
        start_date = None
    
    # For now, we'll return a simple template fragment
    # In a real implementation, you would fetch actual data here
    context = {
        'report_type': report_type,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': today,
    }
    
    return render(request, f'bank/reports/_{report_type}_report.html', context)

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def export_report(request):
    """
    API endpoint for exporting reports as CSV, PDF, or Excel
    """
    report_type = request.GET.get('report_type', 'summary')
    date_range = request.GET.get('date_range', '7d')
    format_type = request.GET.get('format', 'csv')
    
    # Get date range in actual dates
    today = datetime.now().date()
    if date_range == '7d':
        start_date = today - timedelta(days=7)
    elif date_range == '30d':
        start_date = today - timedelta(days=30)
    elif date_range == '90d':
        start_date = today - timedelta(days=90)
    elif date_range == '1y':
        start_date = today - timedelta(days=365)
    else:  # All time
        start_date = None
    
    # Example for CSV export - you would implement other formats similarly
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{date_range}.csv"'
        
        writer = csv.writer(response)
        
        # Write headers based on report type
        if report_type == 'summary':
            writer.writerow(['Metric', 'Value', 'Change'])
            writer.writerow(['Total Credits Managed', '45,678', '+12.5%'])
            writer.writerow(['Transaction Volume', '893', '+5.2%'])
            writer.writerow(['Average Price', '$65', '+3.8%'])
        elif report_type == 'transactions':
            writer.writerow(['Date', 'Transaction ID', 'Type', 'Counterparty', 'Credits', 'Price', 'Total Value', 'Status'])
            writer.writerow(['2023-05-10', 'TX-1025478', 'Purchase', 'EcoTech Inc.', '500', '$62.50', '$31,250', 'Completed'])
            writer.writerow(['2023-05-08', 'TX-1025477', 'Sale', 'GreenLife Co.', '750', '$63.25', '$47,437.50', 'Completed'])
        # Add more report types as needed
        
        return response
    
    # For other format types, you would implement appropriate export functionality
    # For now, just return a placeholder response
    return HttpResponse(f"Export {report_type} as {format_type} not implemented yet")

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def approvals(request):
    """
    View for transaction approvals management.
    Shows pending transactions that need to be approved or rejected.
    """
    # Get pending transactions that need approval
    pending_transactions = MarketplaceTransaction.objects.filter(
        status='pending'
    ).order_by('-created_at')
    
    # Get transactions that were recently approved or rejected (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_transactions = MarketplaceTransaction.objects.filter(
        status__in=['completed', 'rejected'],
        completed_at__gte=seven_days_ago
    ).order_by('-completed_at')
    
    # Get counts for statistics
    pending_count = pending_transactions.count()
    
    # Get approved/rejected counts for today
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    approved_count = MarketplaceTransaction.objects.filter(
        status='completed', 
        completed_at__gte=today_start
    ).count()
    
    rejected_count = MarketplaceTransaction.objects.filter(
        status='rejected', 
        completed_at__gte=today_start
    ).count()
    
    # Calculate total credits pending approval
    total_credits = pending_transactions.aggregate(
        total=Sum('credit_amount')
    )['total'] or 0
    
    context = {
        'page_title': 'Transaction Approvals',
        'active_page': 'approvals',
        'pending_transactions': pending_transactions,
        'recent_transactions': recent_transactions,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_credits': total_credits
    }
    
    return render(request, 'bank/approvals.html', context)

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def approve_transaction(request, transaction_id):
    """
    View for approving a transaction.
    """
    transaction = get_object_or_404(MarketplaceTransaction, id=transaction_id)
    
    # Only allow approving pending transactions
    if transaction.status != 'pending':
        messages.error(request, f"Transaction #{transaction_id} cannot be approved because it is not pending.")
        return redirect('bank:bank_approvals')
    
    # Update transaction status
    transaction.status = 'completed'
    transaction.approved_by = request.user
    transaction.completed_at = timezone.now()
    transaction.save()
    
    # Add the carbon credits to the buyer's account
    CarbonCredit.objects.create(
        amount=transaction.credit_amount,
        source_trip=None,
        owner_type='employer',
        owner_id=transaction.buyer.id,
        timestamp=timezone.now(),
        status='active',
        expiry_date=timezone.now() + timezone.timedelta(days=365)  # 1 year validity
    )
    
    # Notify the user
    messages.success(request, f"Transaction #{transaction_id} approved successfully. {transaction.credit_amount} credits transferred to {transaction.buyer.company_name}.")
    
    return redirect('bank:bank_approvals')

@login_required
@user_passes_test(lambda u: u.is_bank_admin)
def reject_transaction(request, transaction_id):
    """
    View for rejecting a transaction.
    """
    transaction = get_object_or_404(MarketplaceTransaction, id=transaction_id)
    
    # Only allow rejecting pending transactions
    if transaction.status != 'pending':
        messages.error(request, f"Transaction #{transaction_id} cannot be rejected because it is not pending.")
        return redirect('bank:bank_approvals')
    
    # Update transaction status
    transaction.status = 'rejected'
    transaction.save()
    
    # Return the credits to the seller's offer
    offer = transaction.offer
    if offer and offer.status != 'cancelled' and offer.status != 'expired':
        offer.credit_amount += transaction.credit_amount
        offer.total_price = offer.credit_amount * offer.price_per_credit
        # If the offer was completed, set it back to active
        if offer.status == 'completed':
            offer.status = 'active'
        offer.save()
    
    # Notify the user
    messages.success(request, f"Transaction #{transaction_id} rejected. Credits returned to the marketplace.")
    
    return redirect('bank:bank_approvals') 