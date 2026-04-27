"""
Digital Carbon Credit & Wallet System API Views
REST endpoints for wallet operations
"""

import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth import get_user_model
import json

from core.wallet_service import (
    WalletService, CreditVerificationService, SmartContractService
)
from core.wallet_models import CarbonWallet, WalletTransaction, CreditTransfer
from core.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def wallet_balance(request):
    """Get current wallet balance"""
    try:
        balance_data = WalletService.get_wallet_balance(request.user)
        return JsonResponse({
            'success': True,
            'data': balance_data
        })
    except Exception as e:
        logger.error(f"Error getting wallet balance: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def add_credits(request):
    """Add credits to wallet (admin/system only)"""
    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount', 0)))
        source = data.get('source', 'system')
        description = data.get('description')
        source_id = data.get('source_id')
        target_user_email = data.get('target_user')
        
        if amount <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Amount must be positive'
            }, status=400)
        
        # Only allow admin or system to add credits to other users
        if target_user_email and not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        target_user = User.objects.get(email=target_user_email) if target_user_email else request.user
        result = WalletService.add_credits(
            user=target_user,
            amount=amount,
            source=source,
            description=description,
            source_id=source_id
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Target user not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error adding credits: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def transfer_credits(request):
    """Transfer credits to another user"""
    try:
        data = json.loads(request.body)
        recipient_email = data.get('recipient_email')
        amount = Decimal(str(data.get('amount', 0)))
        message = data.get('message', '')
        
        if not recipient_email:
            return JsonResponse({
                'success': False,
                'error': 'Recipient email is required'
            }, status=400)
        
        if amount <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Amount must be positive'
            }, status=400)
        
        result = WalletService.transfer_credits(
            from_user=request.user,
            to_user_email=recipient_email,
            amount=amount,
            message=message
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error transferring credits: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def transaction_history(request):
    """Get transaction history"""
    try:
        limit = int(request.GET.get('limit', 50))
        transaction_type = request.GET.get('type')
        
        transactions = WalletService.get_transaction_history(
            user=request.user,
            limit=limit,
            transaction_type=transaction_type
        )
        
        return JsonResponse({
            'success': True,
            'data': transactions
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid limit parameter'
        }, status=400)
    except Exception as e:
        logger.error(f"Error getting transaction history: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def wallet_stats(request):
    """Get comprehensive wallet statistics"""
    try:
        stats = WalletService.get_wallet_stats(request.user)
        return JsonResponse({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting wallet stats: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def verify_wallet(request):
    """Verify wallet integrity and transaction hashes"""
    try:
        wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        verification_report = CreditVerificationService.create_verification_report(wallet)
        
        return JsonResponse({
            'success': True,
            'data': verification_report
        })
        
    except CarbonWallet.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Wallet not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error verifying wallet: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def transfer_status(request, transfer_id):
    """Get status of a specific transfer"""
    try:
        transfer = get_object_or_404(
            CreditTransfer,
            id=transfer_id,
            from_wallet__owner=request.user
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'transfer_id': str(transfer.id),
                'status': transfer.status,
                'amount': float(transfer.amount),
                'recipient': transfer.to_wallet.owner.email,
                'message': transfer.message,
                'created_at': transfer.created_at.isoformat(),
                'completed_at': transfer.completed_at.isoformat() if transfer.completed_at else None,
                'failure_reason': transfer.failure_reason
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting transfer status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def validate_transfer(request):
    """Validate transfer rules before execution"""
    try:
        data = json.loads(request.body)
        recipient_email = data.get('recipient_email')
        amount = Decimal(str(data.get('amount', 0)))
        
        if not recipient_email or amount <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Invalid transfer parameters'
            }, status=400)
        
        # Get wallets
        from_wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        to_user = User.objects.get(email=recipient_email)
        to_wallet, _ = WalletService.get_or_create_wallet(to_user)
        
        # Validate transfer rules
        validation = SmartContractService.validate_transfer_rules(
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            amount=amount
        )
        
        return JsonResponse({
            'success': True,
            'data': validation
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Recipient not found'
        }, status=404)
    except CarbonWallet.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Wallet not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error validating transfer: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def pending_transfers(request):
    """Get pending transfers for the user"""
    try:
        wallet = CarbonWallet.objects.get(owner=request.user, wallet_type='employee')
        
        # Sent transfers
        sent_pending = wallet.sent_transfers.filter(status='pending').order_by('-created_at')
        received_pending = wallet.received_transfers.filter(status='pending').order_by('-created_at')
        
        sent_data = [
            {
                'transfer_id': str(tx.id),
                'recipient': tx.to_wallet.owner.email,
                'amount': float(tx.amount),
                'message': tx.message,
                'created_at': tx.created_at.isoformat()
            }
            for tx in sent_pending
        ]
        
        received_data = [
            {
                'transfer_id': str(tx.id),
                'sender': tx.from_wallet.owner.email,
                'amount': float(tx.amount),
                'message': tx.message,
                'created_at': tx.created_at.isoformat()
            }
            for tx in received_pending
        ]
        
        return JsonResponse({
            'success': True,
            'data': {
                'sent': sent_data,
                'received': received_data
            }
        })
        
    except CarbonWallet.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Wallet not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting pending transfers: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def process_trip_rewards(request):
    """Process rewards for a completed trip (system endpoint)"""
    try:
        data = json.loads(request.body)
        trip_id = data.get('trip_id')
        
        if not trip_id:
            return JsonResponse({
                'success': False,
                'error': 'Trip ID is required'
            }, status=400)
        
        from trips.models import Trip
        trip = get_object_or_404(Trip, id=trip_id)
        
        result = SmartContractService.process_trip_rewards(trip)
        
        if result:
            return JsonResponse({
                'success': True,
                'data': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to process trip rewards'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error processing trip rewards: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def wallet_summary(request):
    """Get wallet summary for dashboard"""
    try:
        balance = WalletService.get_wallet_balance(request.user)
        stats = WalletService.get_wallet_stats(request.user)
        
        # Get recent transactions
        recent_transactions = WalletService.get_transaction_history(
            user=request.user,
            limit=5
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'balance': balance,
                'stats': stats,
                'recent_transactions': recent_transactions
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting wallet summary: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
