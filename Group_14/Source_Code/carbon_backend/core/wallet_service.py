"""
Digital Carbon Credit & Wallet System Services
Handles wallet operations, transfers, verification, and smart contracts
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from core.wallet_models import (
    CarbonWallet, WalletTransaction, CreditTransfer, 
    CreditExpiry, WalletSettings
)
from core.models import Notification
from trips.models import Trip, CarbonCredit

User = get_user_model()
logger = logging.getLogger(__name__)


class WalletService:
    """Service for managing carbon wallets and transactions"""
    
    @staticmethod
    def get_or_create_wallet(user, wallet_type='employee'):
        """Get or create a wallet for the user"""
        wallet, created = CarbonWallet.objects.get_or_create(
            owner=user,
            wallet_type=wallet_type,
            defaults={
                'balance': 0,
                'available_balance': 0,
                'frozen_balance': 0,
                'status': 'active'
            }
        )
        
        # Create wallet settings if not exists
        if created:
            WalletSettings.objects.create(wallet=wallet)
        
        return wallet, created
    
    @staticmethod
    def get_wallet_balance(user, wallet_type='employee'):
        """Get current wallet balance"""
        try:
            wallet = CarbonWallet.objects.get(owner=user, wallet_type=wallet_type)
            return {
                'total_balance': float(wallet.balance),
                'available_balance': float(wallet.available_balance),
                'frozen_balance': float(wallet.frozen_balance),
                'wallet_id': str(wallet.id)
            }
        except CarbonWallet.DoesNotExist:
            # Create wallet if it doesn't exist and calculate initial balance
            wallet, created = WalletService.get_or_create_wallet(user, wallet_type)
            
            # Calculate credits from existing trips
            from trips.models import Trip
            trips = Trip.objects.filter(employee=user.employee_profile, verification_status='verified')
            total_credits = 0
            
            for trip in trips:
                # Calculate credits based on trip data
                base_credits = Decimal('1.0')
                
                # Bonus for eco-friendly transport
                if trip.transport_mode in ['bicycle', 'walking', 'electric_vehicle']:
                    base_credits *= Decimal('1.5')
                
                # Bonus for longer distances
                if trip.distance_km:
                    distance_bonus = min(trip.distance_km * Decimal('0.1'), Decimal('2.0'))
                    base_credits += distance_bonus
                
                total_credits += base_credits
            
            # Add calculated credits to wallet
            if total_credits > 0:
                wallet.add_credits(total_credits, 'trip', 'Initial credit calculation from existing trips')
            
            return {
                'total_balance': float(wallet.balance),
                'available_balance': float(wallet.available_balance),
                'frozen_balance': float(wallet.frozen_balance),
                'wallet_id': str(wallet.id)
            }
    
    @staticmethod
    def add_credits(user, amount, source='system', description=None, source_id=None):
        """Add credits to user's wallet"""
        try:
            wallet, _ = WalletService.get_or_create_wallet(user)
            transaction_record = wallet.add_credits(
                amount=amount,
                source=source,
                description=description
            )
            
            # Update source_id if provided
            if source_id:
                transaction_record.source_id = source_id
                transaction_record.save()
            
            # Create notification
            Notification.objects.create(
                user=user,
                title='Credits Added',
                message=f'{amount} credits have been added to your wallet.',
                notification_type='success'
            )
            
            return {
                'success': True,
                'transaction_id': str(transaction_record.id),
                'new_balance': float(wallet.balance),
                'available_balance': float(wallet.available_balance)
            }
            
        except Exception as e:
            logger.error(f"Error adding credits: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def transfer_credits(from_user, to_user_email, amount, message=None):
        """Transfer credits between users"""
        try:
            with transaction.atomic():
                # Get wallets
                from_wallet = CarbonWallet.objects.get(
                    owner=from_user, 
                    wallet_type='employee',
                    status='active'
                )
                
                to_user = User.objects.get(email=to_user_email)
                to_wallet, _ = WalletService.get_or_create_wallet(to_user)
                
                # Create transfer record
                transfer = CreditTransfer.objects.create(
                    from_wallet=from_wallet,
                    to_wallet=to_wallet,
                    amount=amount,
                    message=message or f'Transfer from {from_user.email}'
                )
                
                # Execute transfer
                success = transfer.execute_transfer()
                
                if success:
                    # Create notifications
                    Notification.objects.create(
                        user=from_user,
                        title='Transfer Sent',
                        message=f'{amount} credits sent to {to_user_email}',
                        notification_type='info'
                    )
                    
                    Notification.objects.create(
                        user=to_user,
                        title='Credits Received',
                        message=f'{amount} credits received from {from_user.email}',
                        notification_type='success'
                    )
                    
                    return {
                        'success': True,
                        'transfer_id': str(transfer.id),
                        'message': 'Transfer completed successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': transfer.failure_reason or 'Transfer failed'
                    }
                    
        except User.DoesNotExist:
            return {
                'success': False,
                'error': 'Recipient not found'
            }
        except CarbonWallet.DoesNotExist:
            return {
                'success': False,
                'error': 'Wallet not found or inactive'
            }
        except Exception as e:
            logger.error(f"Error transferring credits: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_transaction_history(user, limit=50, transaction_type=None):
        """Get user's transaction history"""
        try:
            wallet = CarbonWallet.objects.get(owner=user, wallet_type='employee')
            transactions = wallet.transactions.all()
            
            if transaction_type:
                transactions = transactions.filter(transaction_type=transaction_type)
            
            transactions = transactions[:limit]
            
            return [
                {
                    'id': str(tx.id),
                    'type': tx.transaction_type,
                    'amount': float(tx.amount),
                    'source': tx.source,
                    'destination': tx.destination,
                    'description': tx.description,
                    'balance_after': float(tx.balance_after),
                    'transaction_hash': tx.transaction_hash,
                    'created_at': tx.created_at.isoformat()
                }
                for tx in transactions
            ]
            
        except CarbonWallet.DoesNotExist:
            return []
    
    @staticmethod
    def get_wallet_stats(user):
        """Get comprehensive wallet statistics"""
        try:
            wallet = CarbonWallet.objects.get(owner=user, wallet_type='employee')
            
            # Calculate stats
            total_credits = float(wallet.balance)
            available_credits = float(wallet.available_balance)
            frozen_credits = float(wallet.frozen_balance)
            
            # Get transaction counts
            transactions = wallet.transactions.all()
            credits_earned = sum(
                tx.amount for tx in transactions 
                if tx.transaction_type in ['credit', 'transfer_in', 'reward']
            )
            credits_spent = sum(
                abs(tx.amount) for tx in transactions 
                if tx.transaction_type in ['debit', 'transfer_out', 'penalty']
            )
            
            # Get recent transfers
            recent_transfers = wallet.sent_transfers.filter(
                status='completed'
            ).order_by('-completed_at')[:5]
            
            return {
                'total_credits': total_credits,
                'available_credits': available_credits,
                'frozen_credits': frozen_credits,
                'total_earned': float(credits_earned),
                'total_spent': float(credits_spent),
                'net_earned': float(credits_earned - credits_spent),
                'transaction_count': transactions.count(),
                'recent_transfers': [
                    {
                        'recipient': tx.to_wallet.owner.email,
                        'amount': float(tx.amount),
                        'date': tx.completed_at.isoformat()
                    }
                    for tx in recent_transfers
                ]
            }
            
        except CarbonWallet.DoesNotExist:
            return {
                'total_credits': 0,
                'available_credits': 0,
                'frozen_credits': 0,
                'total_earned': 0,
                'total_spent': 0,
                'net_earned': 0,
                'transaction_count': 0,
                'recent_transfers': []
            }


class CreditVerificationService:
    """Service for blockchain-like credit verification"""
    
    @staticmethod
    def generate_transaction_hash(transaction_data):
        """Generate SHA-256 hash for transaction verification"""
        hash_string = json.dumps(transaction_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    @staticmethod
    def verify_transaction_integrity(transaction):
        """Verify transaction integrity using hash"""
        transaction_data = {
            'wallet_id': str(transaction.wallet.id),
            'transaction_type': transaction.transaction_type,
            'amount': float(transaction.amount),
            'source': transaction.source,
            'destination': transaction.destination,
            'created_at': transaction.created_at.isoformat()
        }
        
        calculated_hash = CreditVerificationService.generate_transaction_hash(transaction_data)
        return calculated_hash == transaction.transaction_hash
    
    @staticmethod
    def verify_wallet_balance(wallet):
        """Verify wallet balance against transaction history"""
        transactions = wallet.transactions.all()
        calculated_balance = sum(tx.amount for tx in transactions)
        
        # Allow small floating point differences
        difference = abs(float(calculated_balance) - float(wallet.balance))
        return difference < 0.0001
    
    @staticmethod
    def create_verification_report(wallet):
        """Create comprehensive verification report"""
        transactions = wallet.transactions.all()
        
        verified_transactions = []
        for tx in transactions:
            is_valid = CreditVerificationService.verify_transaction_integrity(tx)
            verified_transactions.append({
                'transaction_id': str(tx.id),
                'hash': tx.transaction_hash,
                'verified': is_valid,
                'amount': float(tx.amount),
                'type': tx.transaction_type
            })
        
        balance_verified = CreditVerificationService.verify_wallet_balance(wallet)
        
        return {
            'wallet_id': str(wallet.id),
            'balance_verified': balance_verified,
            'recorded_balance': float(wallet.balance),
            'transaction_count': transactions.count(),
            'verified_transactions': verified_transactions,
            'verification_timestamp': timezone.now().isoformat()
        }


class SmartContractService:
    """Service for automated credit rules and validations"""
    
    @staticmethod
    def process_trip_rewards(trip):
        """Automatically award credits for completed trips"""
        try:
            if trip.verification_status != 'verified':
                return None
            
            # Calculate credits based on trip data
            base_credits = Decimal('1.0')  # Base credit for any trip
            
            # Bonus for eco-friendly transport
            if trip.transport_mode in ['bicycle', 'walking', 'electric_vehicle']:
                base_credits *= Decimal('1.5')
            
            # Bonus for longer distances
            if trip.distance_km:
                distance_bonus = min(trip.distance_km * Decimal('0.1'), Decimal('2.0'))
                base_credits += distance_bonus
            
            # Round to 4 decimal places
            credits = base_credits.quantize(Decimal('0.0001'))
            
            # Add credits to user's wallet
            result = WalletService.add_credits(
                user=trip.user,
                amount=credits,
                source='trip',
                description=f'Reward for trip on {trip.date}',
                source_id=str(trip.id)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing trip rewards: {str(e)}")
            return None
    
    @staticmethod
    def process_auto_transfers():
        """Process automatic transfers based on wallet settings"""
        processed_transfers = []
        
        for settings in WalletSettings.objects.filter(auto_transfer_enabled=True):
            try:
                wallet = settings.wallet
                
                if wallet.available_balance >= settings.auto_transfer_threshold:
                    if settings.auto_transfer_recipient:
                        result = WalletService.transfer_credits(
                            from_user=wallet.owner,
                            to_user_email=settings.auto_transfer_recipient.email,
                            amount=settings.auto_transfer_threshold,
                            message='Automatic transfer'
                        )
                        
                        if result['success']:
                            processed_transfers.append({
                                'wallet_id': str(wallet.id),
                                'amount': float(settings.auto_transfer_threshold),
                                'recipient': settings.auto_transfer_recipient.email,
                                'transfer_id': result['transfer_id']
                            })
                            
            except Exception as e:
                logger.error(f"Error processing auto-transfer: {str(e)}")
        
        return processed_transfers
    
    @staticmethod
    def process_credit_expiry():
        """Process expired credits"""
        expired_credits = []
        
        # Get expired credits that haven't been processed
        expiry_records = CreditExpiry.objects.filter(
            expiry_date__lte=timezone.now(),
            processed=False,
            is_expired=False
        )
        
        for expiry in expiry_records:
            try:
                if expiry.process_expiry():
                    expired_credits.append({
                        'wallet_id': str(expiry.wallet.id),
                        'amount': float(expiry.amount),
                        'expiry_date': expiry.expiry_date.isoformat()
                    })
            except Exception as e:
                logger.error(f"Error processing credit expiry: {str(e)}")
        
        return expired_credits
    
    @staticmethod
    def validate_transfer_rules(from_wallet, to_wallet, amount):
        """Validate transfer against smart contract rules"""
        rules = {
            'minimum_transfer': Decimal('0.0001'),
            'daily_transfer_limit': Decimal('1000.0'),
            'require_verification': False
        }
        
        # Check minimum amount
        if amount < rules['minimum_transfer']:
            return {
                'valid': False,
                'reason': f'Minimum transfer amount is {rules["minimum_transfer"]} credits'
            }
        
        # Check daily limit
        today = timezone.now().date()
        daily_transfers = from_wallet.sent_transfers.filter(
            created_at__date=today,
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        if daily_transfers + amount > rules['daily_transfer_limit']:
            return {
                'valid': False,
                'reason': f'Daily transfer limit of {rules["daily_transfer_limit"]} credits exceeded'
            }
        
        return {
            'valid': True,
            'reason': 'Transfer validated successfully'
        }
