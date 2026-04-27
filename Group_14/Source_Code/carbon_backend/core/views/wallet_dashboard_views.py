"""
Digital Carbon Credit & Wallet System Dashboard Views
HTML views for wallet dashboard and pages
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from core.wallet_service import WalletService, CreditVerificationService
from core.wallet_models import CarbonWallet, WalletTransaction, CreditTransfer
from core.models import Notification

User = get_user_model()


@login_required
def wallet_dashboard(request):
    """Main wallet dashboard view"""
    try:
        # Get wallet data
        balance = WalletService.get_wallet_balance(request.user)
        stats = WalletService.get_wallet_stats(request.user)
        recent_transactions = WalletService.get_transaction_history(
            user=request.user,
            limit=10
        )
        
        # Get pending transfers
        wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        pending_sent = wallet.sent_transfers.filter(status='pending').order_by('-created_at')[:5]
        pending_received = wallet.received_transfers.filter(status='pending').order_by('-created_at')[:5]
        
        context = {
            'balance': balance,
            'stats': stats,
            'recent_transactions': recent_transactions,
            'pending_sent': pending_sent,
            'pending_received': pending_received,
            'page_title': 'Carbon Credits Wallet'
        }
        
        return render(request, 'wallet/dashboard.html', context)
        
    except CarbonWallet.DoesNotExist:
        # Create wallet if it doesn't exist
        WalletService.get_or_create_wallet(request.user)
        return wallet_dashboard(request)
    except Exception as e:
        context = {
            'error': str(e),
            'page_title': 'Carbon Credits Wallet'
        }
        return render(request, 'wallet/dashboard.html', context)


@login_required
def transaction_history(request):
    """Full transaction history view"""
    try:
        page = int(request.GET.get('page', 1))
        transaction_type = request.GET.get('type')
        export_format = request.GET.get('export')
        
        # Get wallet
        wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        
        # Filter transactions
        transactions = wallet.transactions.all()
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        # Export to CSV if requested
        if export_format == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Date', 'Type', 'Amount', 'Description', 'Balance After'])
            
            for tx in transactions:
                writer.writerow([
                    tx.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    tx.get_transaction_type_display(),
                    tx.amount,
                    tx.description or '',
                    tx.balance_after
                ])
            
            return response
        
        # Paginate results
        paginator = Paginator(transactions, 50)
        transactions_page = paginator.get_page(page)
        
        context = {
            'transactions': transactions_page,
            'transaction_type': transaction_type,
            'page_title': 'Transaction History'
        }
        
        return render(request, 'wallet/transactions.html', context)
        
    except CarbonWallet.DoesNotExist:
        return render(request, 'wallet/transactions.html', {
            'error': 'Wallet not found',
            'page_title': 'Transaction History'
        })
    except Exception as e:
        return render(request, 'wallet/transactions.html', {
            'error': str(e),
            'page_title': 'Transaction History'
        })


@login_required
def pending_transfers(request):
    """Pending transfers view"""
    try:
        wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        
        sent_transfers = wallet.sent_transfers.filter(status='pending').order_by('-created_at')
        received_transfers = wallet.received_transfers.filter(status='pending').order_by('-created_at')
        
        context = {
            'sent_transfers': sent_transfers,
            'received_transfers': received_transfers,
            'page_title': 'Pending Transfers'
        }
        
        return render(request, 'wallet/pending_transfers.html', context)
        
    except CarbonWallet.DoesNotExist:
        return render(request, 'wallet/pending_transfers.html', {
            'error': 'Wallet not found',
            'page_title': 'Pending Transfers'
        })
    except Exception as e:
        return render(request, 'wallet/pending_transfers.html', {
            'error': str(e),
            'page_title': 'Pending Transfers'
        })


@login_required
def transfer_details(request, transfer_id):
    """Transfer details view"""
    try:
        transfer = get_object_or_404(
            CreditTransfer,
            id=transfer_id
        )
        
        # Check if user is sender or receiver
        if not (transfer.from_wallet.owner == request.user or transfer.to_wallet.owner == request.user):
            return render(request, 'wallet/transfer_details.html', {
                'error': 'Access denied',
                'page_title': 'Transfer Details'
            })
        
        # Check if user is sender or receiver
        is_sender = transfer.from_wallet.owner == request.user
        is_receiver = transfer.to_wallet.owner == request.user
        
        context = {
            'transfer': transfer,
            'is_sender': is_sender,
            'is_receiver': is_receiver,
            'page_title': 'Transfer Details'
        }
        
        return render(request, 'wallet/transfer_details.html', context)
        
    except Exception as e:
        return render(request, 'wallet/transfer_details.html', {
            'error': str(e),
            'page_title': 'Transfer Details'
        })


@login_required
def wallet_verification(request):
    """Wallet verification page"""
    try:
        wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        verification_report = CreditVerificationService.create_verification_report(wallet)
        
        context = {
            'verification_report': verification_report,
            'page_title': 'Wallet Verification'
        }
        
        return render(request, 'wallet/verification.html', context)
        
    except CarbonWallet.DoesNotExist:
        return render(request, 'wallet/verification.html', {
            'error': 'Wallet not found',
            'page_title': 'Wallet Verification'
        })
    except Exception as e:
        return render(request, 'wallet/verification.html', {
            'error': str(e),
            'page_title': 'Wallet Verification'
        })


@login_required
def wallet_settings(request):
    """Wallet settings page"""
    try:
        wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        
        if request.method == 'POST':
            # Update wallet settings
            from core.wallet_models import WalletSettings
            settings = wallet.settings
            
            settings.auto_transfer_enabled = request.POST.get('auto_transfer_enabled') == 'on'
            settings.auto_transfer_threshold = float(request.POST.get('auto_transfer_threshold', 0))
            
            recipient_email = request.POST.get('auto_transfer_recipient')
            if recipient_email:
                try:
                    recipient = User.objects.get(email=recipient_email)
                    settings.auto_transfer_recipient = recipient
                except User.DoesNotExist:
                    pass
            
            settings.notification_enabled = request.POST.get('notification_enabled') == 'on'
            settings.low_balance_alert = float(request.POST.get('low_balance_alert', 10))
            settings.monthly_report_enabled = request.POST.get('monthly_report_enabled') == 'on'
            
            settings.save()
            
            from django.contrib import messages
            messages.success(request, 'Wallet settings updated successfully!')
        
        context = {
            'wallet': wallet,
            'settings': wallet.settings,
            'page_title': 'Wallet Settings'
        }
        
        return render(request, 'wallet/settings.html', context)
        
    except CarbonWallet.DoesNotExist:
        return render(request, 'wallet/settings.html', {
            'error': 'Wallet not found',
            'page_title': 'Wallet Settings'
        })
    except Exception as e:
        return render(request, 'wallet/settings.html', {
            'error': str(e),
            'page_title': 'Wallet Settings'
        })
