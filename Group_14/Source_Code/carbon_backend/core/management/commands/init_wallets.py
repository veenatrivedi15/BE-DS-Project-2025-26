"""
Management command to initialize wallets with existing trip data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from core.wallet_service import WalletService
from trips.models import Trip

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize wallets with existing trip data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Initialize wallet for specific user only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        self.stdout.write('Initializing wallets with trip data...')
        
        # Get users to process
        if options['user_email']:
            users = User.objects.filter(email=options['user_email'])
        else:
            users = User.objects.filter(is_employee=True)
        
        total_users = 0
        total_credits = 0
        
        for user in users:
            # Get user's completed trips
            trips = Trip.objects.filter(employee=user.employee_profile, verification_status='verified')
            
            if not trips.exists():
                continue
            
            # Calculate credits from trips
            user_credits = Decimal('0')
            trip_count = 0
            
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
                
                user_credits += base_credits
                trip_count += 1
            
            if options['dry_run']:
                self.stdout.write(
                    f'User: {user.email} | Trips: {trip_count} | Credits: {user_credits}'
                )
            else:
                # Get or create wallet
                wallet, created = WalletService.get_or_create_wallet(user)
                
                # Add credits if wallet is new or has zero balance
                if created or wallet.balance == 0:
                    result = WalletService.add_credits(
                        user=user,
                        amount=user_credits,
                        source='trip',
                        description=f'Initial credit calculation from {trip_count} trips'
                    )
                    
                    if result['success']:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'[OK] {user.email}: {trip_count} trips -> {user_credits} credits'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'[ERROR] {user.email}: {result["error"]}'
                            )
                        )
                        continue
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[WARNING] {user.email}: Wallet already has credits ({wallet.balance})'
                        )
                    )
                    continue
            
            total_users += 1
            total_credits += float(user_credits)
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would process {total_users} users with {total_credits:.4f} total credits'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[SUCCESS] Processed {total_users} users with {total_credits:.4f} total credits'
                )
            )
