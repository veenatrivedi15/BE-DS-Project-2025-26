"""
Views for employers to handle employee redemption requests.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from decimal import Decimal
from marketplace.models import EmployeeCreditOffer
from trips.models import CarbonCredit
from core.models import Notification

@login_required
@user_passes_test(lambda u: u.is_employer)
def redemption_requests(request):
    """
    View for employers to see and manage employee redemption requests.
    """
    employer_profile = request.user.employer_profile
    
    # Get pending redemption requests
    pending_requests = EmployeeCreditOffer.objects.filter(
        employer=employer_profile,
        offer_type='redeem',
        status='pending'
    ).order_by('-created_at')
    
    # Get processed requests (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    processed_requests = EmployeeCreditOffer.objects.filter(
        employer=employer_profile,
        offer_type='redeem',
        status__in=['approved', 'rejected', 'cancelled'],
        processed_at__gte=thirty_days_ago
    ).order_by('-processed_at')
    
    # Get employer credit balance
    employer_credits = CarbonCredit.objects.filter(
        owner_type='employer',
        owner_id=employer_profile.id,
        status='active'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get total pending redemption value
    total_pending_value = pending_requests.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    context = {
        'page_title': 'Redemption Requests',
        'pending_requests': pending_requests,
        'processed_requests': processed_requests,
        'employer_credits': employer_credits,
        'total_pending_value': total_pending_value,
    }
    
    return render(request, 'employer/redemption_requests.html', context)

@login_required
@user_passes_test(lambda u: u.is_employer)
def process_redemption(request, request_id):
    """
    Process (approve/reject) a redemption request.
    """
    employer_profile = request.user.employer_profile
    
    redemption_request = get_object_or_404(
        EmployeeCreditOffer,
        id=request_id,
        employer=employer_profile,
        offer_type='redeem'
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')  # 'approve' or 'reject'
        
        if action == 'approve':
            # Mark employee credits as redeemed
            # IMPORTANT: Convert to list to avoid QuerySet evaluation issues
            employee_credits = list(CarbonCredit.objects.filter(
                owner_type='employee',
                owner_id=redemption_request.employee.id,
                status='active'
            ).order_by('timestamp'))
            
            # Calculate how many credits to redeem
            credits_to_redeem = Decimal(str(redemption_request.credit_amount))
            redeemed_count = Decimal('0')
            
            # Update credit status to used (only the requested amount)
            for credit in employee_credits:
                if redeemed_count >= credits_to_redeem:
                    break  # Stop when we've redeemed enough
                
                credit_amount = Decimal(str(credit.amount))
                remaining_needed = credits_to_redeem - redeemed_count
                
                if credit_amount <= remaining_needed:
                    # Redeem entire credit - mark as 'used' (not 'redeemed' - that status doesn't exist)
                    credit.status = 'used'
                    credit.save()
                    redeemed_count += credit_amount
                else:
                    # Partial redemption - create new credit for remaining amount
                    remaining = credit_amount - remaining_needed
                    if remaining > 0:
                        # Create new credit with remaining amount
                        CarbonCredit.objects.create(
                            owner_type='employee',
                            owner_id=redemption_request.employee.id,
                            amount=remaining,
                            status='active',
                            timestamp=credit.timestamp
                        )
                    # Mark original credit as used (with partial amount)
                    credit.amount = remaining_needed
                    credit.status = 'used'
                    credit.save()
                    redeemed_count = credits_to_redeem
                    break  # We've redeemed exactly what we need
            
            # Transfer redeemed credits to employer (employer receives the credits)
            # This represents the employer "buying back" the credits from the employee
            # Create a new credit entry for the employer
            CarbonCredit.objects.create(
                owner_type='employer',
                owner_id=employer_profile.id,
                amount=credits_to_redeem,
                status='active',
                timestamp=timezone.now()
            )
            
            # Update redemption request
            redemption_request.status = 'approved'
            redemption_request.processed_at = timezone.now()
            redemption_request.save()
            
            # Create notification for employee
            Notification.objects.create(
                user=redemption_request.employee.user,
                notification_type='success',
                title='Redemption Approved',
                message=f'Your redemption request for {redemption_request.credit_amount} credits (${redemption_request.total_amount:.2f}) has been approved and processed.',
                link=f'/employee/redeem/'
            )
            
            messages.success(request, f"Redemption request approved. {redemption_request.credit_amount} credits have been redeemed.")
            
        elif action == 'reject':
            redemption_request.status = 'rejected'
            redemption_request.processed_at = timezone.now()
            redemption_request.save()
            
            # Create notification for employee
            Notification.objects.create(
                user=redemption_request.employee.user,
                notification_type='error',
                title='Redemption Rejected',
                message=f'Your redemption request for {redemption_request.credit_amount} credits has been rejected. Please contact your employer for more information.',
                link=f'/employee/redeem/'
            )
            
            messages.success(request, "Redemption request rejected.")
        
        return redirect('employer:redemption_requests')
    
    context = {
        'page_title': 'Process Redemption',
        'redemption_request': redemption_request,
    }
    
    return render(request, 'employer/process_redemption.html', context)

