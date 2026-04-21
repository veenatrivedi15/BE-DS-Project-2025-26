"""
Views for employee credit redemption with their employer.
Employees can redeem credits for coupons, money, etc.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Sum, Avg
from django.utils import timezone
from decimal import Decimal
from marketplace.models import EmployeeCreditOffer, MarketOffer
from users.models import EmployeeProfile
from core.wallet_service import WalletService

@login_required
@user_passes_test(lambda u: u.is_employee)
def redeem_credits(request):
    """
    View for employees to redeem their carbon credits for rewards.
    """
    employee = request.user.employee_profile
    employer = employee.employer
    
    if not employer:
        messages.error(request, "You are not associated with an employer.")
        return redirect('employee_dashboard')
    
    # Get employee's available credits from new wallet system
    wallet_balance = WalletService.get_wallet_balance(request.user)
    available_credits = Decimal(str(wallet_balance['available_balance']))
    
    # Get current market rate (for calculating value)
    market_rate = MarketOffer.objects.filter(
        status='active'
    ).aggregate(Avg('price_per_credit'))['price_per_credit__avg'] or Decimal('5.0')
    
    # Calculate total value of credits
    total_value = available_credits * market_rate
    
    # Get redemption history
    redemption_history = EmployeeCreditOffer.objects.filter(
        employee=employee,
        offer_type='redeem',
        status__in=['approved', 'pending', 'rejected']
    ).order_by('-created_at')[:20]
    
    # Redemption options (can be configured by employer)
    redemption_options = [
        {
            'id': 'cash',
            'name': 'Cash Payment',
            'description': 'Redeem credits for direct cash payment',
            'icon': '💰',
            'min_credits': 10,
            'rate': float(market_rate),  # 1 credit = market rate
        },
        {
            'id': 'coupon',
            'name': 'Gift Coupons',
            'description': 'Redeem for gift coupons and vouchers',
            'icon': '🎁',
            'min_credits': 5,
            'rate': float(market_rate * Decimal('1.1')),  # 10% bonus for coupons
        },
        {
            'id': 'voucher',
            'name': 'Shopping Vouchers',
            'description': 'Redeem for shopping vouchers',
            'icon': '🛍️',
            'min_credits': 5,
            'rate': float(market_rate * Decimal('1.1')),  # 10% bonus
        },
        {
            'id': 'donation',
            'name': 'Donate to Charity',
            'description': 'Donate your credits to environmental causes',
            'icon': '🌱',
            'min_credits': 1,
            'rate': float(market_rate),  # Same rate
        },
    ]
    
    if request.method == 'POST':
        redemption_type = request.POST.get('redemption_type')
        credit_amount = request.POST.get('credit_amount')
        additional_info = request.POST.get('additional_info', '')
        
        try:
            credit_amount = Decimal(str(credit_amount))
            
            # Validate input
            if credit_amount <= 0:
                messages.error(request, "Credit amount must be positive")
                return redirect('employee_redeem_credits')
            
            if credit_amount > available_credits:
                messages.error(request, f"You don't have enough credits. Available: {available_credits}")
                return redirect('employee_redeem_credits')
            
            # Find the redemption option
            option = next((opt for opt in redemption_options if opt['id'] == redemption_type), None)
            if not option:
                messages.error(request, "Invalid redemption type")
                return redirect('employee_redeem_credits')
            
            # Check minimum credits
            if credit_amount < option['min_credits']:
                messages.error(request, f"Minimum {option['min_credits']} credits required for this option")
                return redirect('employee_redeem_credits')
            
            # Calculate total value
            total_value = credit_amount * Decimal(str(option['rate']))
            
            # Create redemption request
            redemption_offer = EmployeeCreditOffer.objects.create(
                employee=employee,
                employer=employer,
                offer_type='redeem',  # New type for redemption
                credit_amount=credit_amount,
                market_rate=Decimal(str(option['rate'])),
                total_amount=total_value,
                status='pending'
            )
            
            # Set additional_info if provided
            if additional_info:
                redemption_offer.additional_info = additional_info
                redemption_offer.save()
            
            # Create notification for employer
            from core.models import Notification
            Notification.objects.create(
                user=employer.user,
                notification_type='redemption',
                title='New Redemption Request',
                message=f'{employee.user.get_full_name() or employee.user.email} has requested to redeem {credit_amount} credits (${total_value:.2f}).',
                link=f'/employer/redemption-requests/'
            )
            
            messages.success(
                request, 
                f"Your redemption request for {credit_amount} credits (worth ${total_value:.2f}) has been submitted to your employer. "
                f"You will be notified once it's processed."
            )
            
            return redirect('employee_redeem_credits')
            
        except ValueError:
            messages.error(request, "Invalid credit amount")
        except Exception as e:
            messages.error(request, f"Error processing redemption: {str(e)}")
    
    context = {
        'page_title': 'Redeem Credits',
        'employee': employee,
        'employer': employer,
        'available_credits': available_credits,
        'total_value': total_value,
        'market_rate': market_rate,
        'redemption_options': redemption_options,
        'redemption_history': redemption_history,
    }
    
    return render(request, 'employee/redeem_credits.html', context)

