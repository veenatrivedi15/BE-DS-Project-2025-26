"""
Management command to populate achievement data based on real user activity
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from datetime import timedelta, datetime
from decimal import Decimal

from trips.models import Trip
from core.gamification_models import (
    Badge, UserBadge, UserPoints, UserProgress, Streak
)
from core.wallet_service import WalletService

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate achievement data based on real user activity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Process specific user only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        self.stdout.write('Populating achievement data with real user activity...')
        
        # Get users to process
        if options['user_email']:
            users = User.objects.filter(email=options['user_email'])
        else:
            users = User.objects.filter(is_employee=True)
        
        for user in users:
            if not hasattr(user, 'employee_profile'):
                continue
                
            self.stdout.write(f'\nProcessing user: {user.email}')
            
            # Get user's verified trips
            trips = Trip.objects.filter(
                employee=user.employee_profile,
                verification_status='verified'
            )
            
            if not trips.exists():
                self.stdout.write('  No verified trips found')
                continue
            
            # Calculate real stats
            total_trips = trips.count()
            total_distance = trips.aggregate(
                total=models.Sum('distance_km')
            )['total'] or Decimal('0')
            total_carbon_saved = trips.aggregate(
                total=models.Sum('carbon_savings')
            )['total'] or Decimal('0')
            
            self.stdout.write(f'  Stats: {total_trips} trips, {total_distance}km, {total_carbon_saved}kg CO2 saved')
            
            # Award badges based on real achievements
            self._award_badges(user, total_trips, total_carbon_saved, options)
            
            # Calculate and award points
            self._award_points(user, total_trips, total_distance, total_carbon_saved, options)
            
            # Calculate streaks
            self._calculate_streaks(user, trips, options)
            
            # Update progress
            self._update_progress(user, total_trips, total_distance, total_carbon_saved, options)
        
        self.stdout.write('\n[SUCCESS] Achievement data population completed!')

    def _award_badges(self, user, total_trips, total_carbon_saved, options):
        """Award badges based on real achievements"""
        badges_awarded = []
        
        # First Step badge
        if total_trips >= 1:
            badge = Badge.objects.filter(name='First Step').first()
            if badge and not UserBadge.objects.filter(user=user, badge=badge).exists():
                badges_awarded.append(badge)
        
        # Commuter badge
        if total_trips >= 10:
            badge = Badge.objects.filter(name='Commuter').first()
            if badge and not UserBadge.objects.filter(user=user, badge=badge).exists():
                badges_awarded.append(badge)
        
        # Carbon Saver badge
        if total_carbon_saved >= Decimal('5'):
            badge = Badge.objects.filter(name='Carbon Saver').first()
            if badge and not UserBadge.objects.filter(user=user, badge=badge).exists():
                badges_awarded.append(badge)
        
        # Planet Protector badge
        if total_carbon_saved >= Decimal('100'):
            badge = Badge.objects.filter(name='Planet Protector').first()
            if badge and not UserBadge.objects.filter(user=user, badge=badge).exists():
                badges_awarded.append(badge)
        
        if options['dry_run']:
            for badge in badges_awarded:
                self.stdout.write(f'    Would award badge: {badge.name}')
        else:
            for badge in badges_awarded:
                UserBadge.objects.create(
                    user=user,
                    badge=badge,
                    earned_at=timezone.now(),
                    progress_value=100  # Badge is fully earned
                )
                self.stdout.write(f'    [OK] Awarded badge: {badge.name}')

    def _award_points(self, user, total_trips, total_distance, total_carbon_saved, options):
        """Calculate and award points based on real activity"""
        # Calculate points based on various factors
        points = int(total_trips * 10)  # 10 points per trip
        points += int(float(total_distance) * 2)  # 2 points per km
        points += int(float(total_carbon_saved) * 50)  # 50 points per kg CO2 saved
        
        # Check if user already has points
        existing_points = UserPoints.objects.filter(user=user).aggregate(
            total=models.Sum('points')
        )['total'] or 0
        
        if existing_points == 0 and points > 0:
            if options['dry_run']:
                self.stdout.write(f'    Would award {points} points')
            else:
                UserPoints.objects.create(
                    user=user,
                    points=points,
                    points_type='trip',
                    description=f'Points from {total_trips} trips, {total_distance}km, {total_carbon_saved}kg CO2 saved',
                    created_at=timezone.now()
                )
                self.stdout.write(f'    [OK] Awarded {points} points')

    def _calculate_streaks(self, user, trips, options):
        """Calculate streaks based on trip dates"""
        if not trips.exists():
            return
        
        # Get trip dates sorted
        trip_dates = sorted(set(trips.values_list('start_time__date', flat=True)))
        
        # Calculate current streak
        current_streak = 0
        today = timezone.now().date()
        
        for i, date in enumerate(reversed(trip_dates)):
            expected_date = today - timedelta(days=i)
            if date == expected_date:
                current_streak += 1
            else:
                break
        
        if current_streak >= 3:
            if options['dry_run']:
                self.stdout.write(f'    Would create streak: {current_streak} days')
            else:
                # Create or update streak
                streak, created = Streak.objects.get_or_create(
                    user=user,
                    streak_type='daily_trips',
                    defaults={
                        'current_streak': current_streak,
                        'longest_streak': current_streak,
                        'last_activity': max(trip_dates),
                        'start_date': max(trip_dates) - timedelta(days=current_streak-1)
                    }
                )
                
                if not created and current_streak > streak.current_streak:
                    streak.current_streak = current_streak
                    streak.last_activity = max(trip_dates)
                    streak.save()
                
                self.stdout.write(f'    [OK] Updated streak: {current_streak} days')

    def _update_progress(self, user, total_trips, total_distance, total_carbon_saved, options):
        """Update user progress towards goals"""
        progress_goals = [
            ('trips_completed', total_trips, 50),  # Goal: 50 trips
            ('carbon_saved', float(total_carbon_saved), 100),  # Goal: 100kg CO2
            ('distance_traveled', float(total_distance), 500),  # Goal: 500km
        ]
        
        for goal_type, current_value, target_value in progress_goals:
            progress, created = UserProgress.objects.get_or_create(
                user=user,
                progress_type=goal_type,
                defaults={
                    'current_value': current_value,
                    'target_value': target_value,
                    'percentage_complete': min((current_value / target_value) * 100, 100)
                }
            )
            
            if not created:
                progress.current_value = current_value
                progress.percentage_complete = min((current_value / target_value) * 100, 100)
                progress.save()
            
            percentage = min((current_value / target_value) * 100, 100)
            if options['dry_run']:
                self.stdout.write(f'    Would update {goal_type}: {current_value}/{target_value} ({percentage:.1f}%)')
            else:
                self.stdout.write(f'    [OK] Updated {goal_type}: {current_value}/{target_value} ({percentage:.1f}%)')
