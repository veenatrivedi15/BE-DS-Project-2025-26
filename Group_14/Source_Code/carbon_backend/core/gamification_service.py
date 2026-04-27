"""
Gamification service for leaderboards, badges, and progress tracking
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Window
from django.db.models.functions import Rank, DenseRank
from django.contrib.auth import get_user_model

from core.gamification_models import (
    Badge, UserBadge, Leaderboard, LeaderboardEntry,
    UserProgress, Streak, CommunityChallenge, ChallengeParticipant,
    UserPoints
)
from core.models import Notification
from trips.models import Trip, CarbonCredit

User = get_user_model()

logger = logging.getLogger(__name__)


class BadgeService:
    """Service for managing badges and achievements."""
    
    @staticmethod
    def check_and_award_badges(user):
        """
        Check user's progress and award appropriate badges.
        
        Args:
            user: User object
            
        Returns:
            List of newly awarded badges
        """
        newly_awarded = []
        
        if not user.is_employee:
            return newly_awarded
        
        # Get user's stats
        user_stats = BadgeService._get_user_stats(user)
        
        # Check all active badges
        for badge in Badge.objects.filter(is_active=True):
            if UserBadge.objects.filter(user=user, badge=badge).exists():
                continue  # Already earned
            
            if BadgeService._check_badge_condition(badge, user_stats):
                # Award badge
                user_badge = UserBadge.objects.create(
                    user=user,
                    badge=badge,
                    progress_value=user_stats.get(badge.condition_type, 0)
                )
                
                # Award points
                UserPoints.objects.create(
                    user=user,
                    points_type='badge',
                    points=badge.points,
                    description=f"Earned badge: {badge.name}",
                    related_object_id=badge.id
                )
                
                newly_awarded.append(badge)
                logger.info(f"Awarded badge '{badge.name}' to user {user.email}")
        
        return newly_awarded
    
    @staticmethod
    def _get_user_stats(user):
        """Get user's statistics for badge checking."""
        if not user.is_employee:
            return {}
        
        # Get trips from last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_trips = Trip.objects.filter(
            employee=user.employee_profile,
            created_at__gte=thirty_days_ago
        )
        
        # Calculate stats
        stats = {
            'trips_count': recent_trips.count(),
            'carbon_saved': sum(float(trip.carbon_savings or 0) for trip in recent_trips),
            'streak_days': BadgeService._calculate_streak_days(user),
        }
        
        return stats
    
    @staticmethod
    def _check_badge_condition(badge, user_stats):
        """Check if user meets badge condition."""
        condition_value = badge.condition_value
        user_value = user_stats.get(badge.condition_type, 0)
        
        if badge.condition_type == 'trips_count':
            return user_value >= condition_value
        elif badge.condition_type == 'carbon_saved':
            return user_value >= condition_value
        elif badge.condition_type == 'streak_days':
            return user_value >= condition_value
        
        return False
    
    @staticmethod
    def _calculate_streak_days(user):
        """Calculate user's current streak days."""
        if not user.is_employee:
            return 0
        
        # Get daily activity for last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_activity = Trip.objects.filter(
            employee=user.employee_profile,
            created_at__gte=thirty_days_ago
        ).dates('created_at', 'day')
        
        if not daily_activity:
            return 0
        
        # Calculate consecutive days
        streak = 0
        today = timezone.now().date()
        
        for i, date in enumerate(sorted(daily_activity, reverse=True)):
            expected_date = today - timedelta(days=i)
            if date == expected_date:
                streak += 1
            else:
                break
        
        return streak
    
    @staticmethod
    def get_user_badges(user, limit=10):
        """Get user's earned badges."""
        return UserBadge.objects.filter(
            user=user,
            is_earned=True
        ).select_related('badge').order_by('-earned_at')[:limit]
    
    @staticmethod
    def get_badge_progress(user):
        """Get user's progress towards all badges."""
        user_stats = BadgeService._get_user_stats(user)
        progress_data = []
        
        for badge in Badge.objects.filter(is_active=True):
            user_badge = UserBadge.objects.filter(user=user, badge=badge).first()
            
            if user_badge and user_badge.is_earned:
                continue  # Already earned
            
            current_value = user_stats.get(badge.condition_type, 0)
            percentage = min(100, (current_value / badge.condition_value) * 100) if badge.condition_value > 0 else 0
            
            progress_data.append({
                'badge': badge,
                'current_value': current_value,
                'target_value': badge.condition_value,
                'percentage': percentage,
                'is_earned': user_badge.is_earned if user_badge else False
            })
        
        return progress_data


class LeaderboardService:
    """Service for managing leaderboards."""
    
    @staticmethod
    def update_leaderboards():
        """Update all active leaderboards."""
        updated_count = 0
        
        for leaderboard in Leaderboard.objects.filter(is_active=True):
            if LeaderboardService._update_leaderboard(leaderboard):
                updated_count += 1
        
        logger.info(f"Updated {updated_count} leaderboards")
        return updated_count
    
    @staticmethod
    def _update_leaderboard(leaderboard):
        """Update a specific leaderboard."""
        try:
            # Clear existing entries
            LeaderboardEntry.objects.filter(leaderboard=leaderboard).delete()
            
            # Get data based on category
            if leaderboard.category == 'carbon_saved':
                entries = LeaderboardService._get_carbon_saved_leaderboard(leaderboard)
            elif leaderboard.category == 'trips_count':
                entries = LeaderboardService._get_trips_count_leaderboard(leaderboard)
            elif leaderboard.category == 'badges_count':
                entries = LeaderboardService._get_badges_count_leaderboard(leaderboard)
            elif leaderboard.category == 'points':
                entries = LeaderboardService._get_points_leaderboard(leaderboard)
            else:
                return False
            
            # Create new entries with ranks
            for rank, (user, value) in enumerate(entries, 1):
                LeaderboardEntry.objects.create(
                    leaderboard=leaderboard,
                    user=user,
                    value=Decimal(str(value)),
                    rank=rank
                )
            
            leaderboard.last_updated = timezone.now()
            leaderboard.save()
            return True
            
        except Exception as e:
            logger.error(f"Error updating leaderboard {leaderboard.name}: {str(e)}")
            return False
    
    @staticmethod
    def _get_carbon_saved_leaderboard(leaderboard):
        """Get carbon saved leaderboard data."""
        # Filter by time period
        date_filter = LeaderboardService._get_date_filter(leaderboard.leaderboard_type)
        
        # Get carbon savings by user
        user_carbon = Trip.objects.filter(
            created_at__gte=date_filter
        ).values('employee__user').annotate(
            total_carbon=Sum('carbon_savings')
        ).order_by('-total_carbon')
        
        return [
            (User.objects.get(id=item['employee__user']), item['total_carbon'] or 0)
            for item in user_carbon
        ]
    
    @staticmethod
    def _get_trips_count_leaderboard(leaderboard):
        """Get trips count leaderboard data."""
        date_filter = LeaderboardService._get_date_filter(leaderboard.leaderboard_type)
        
        user_trips = Trip.objects.filter(
            created_at__gte=date_filter
        ).values('employee__user').annotate(
            trip_count=Count('id')
        ).order_by('-trip_count')
        
        return [
            (User.objects.get(id=item['employee__user']), item['trip_count'])
            for item in user_trips
        ]
    
    @staticmethod
    def _get_badges_count_leaderboard(leaderboard):
        """Get badges count leaderboard data."""
        user_badges = UserBadge.objects.filter(
            is_earned=True
        ).values('user').annotate(
            badge_count=Count('badge')
        ).order_by('-badge_count')
        
        return [
            (User.objects.get(id=item['user']), item['badge_count'])
            for item in user_badges
        ]
    
    @staticmethod
    def _get_points_leaderboard(leaderboard):
        """Get points leaderboard data."""
        date_filter = LeaderboardService._get_date_filter(leaderboard.leaderboard_type)
        
        user_points = UserPoints.objects.filter(
            created_at__gte=date_filter
        ).values('user').annotate(
            total_points=Sum('points')
        ).order_by('-total_points')
        
        return [
            (User.objects.get(id=item['user']), item['total_points'] or 0)
            for item in user_points
        ]
    
    @staticmethod
    def _get_date_filter(leaderboard_type):
        """Get date filter based on leaderboard type."""
        now = timezone.now()
        
        if leaderboard_type == 'daily':
            return now - timedelta(days=1)
        elif leaderboard_type == 'weekly':
            return now - timedelta(weeks=1)
        elif leaderboard_type == 'monthly':
            return now - timedelta(days=30)
        elif leaderboard_type == 'yearly':
            return now - timedelta(days=365)
        else:  # all_time
            return now - timedelta(days=3650)  # 10 years
    
    @staticmethod
    def get_leaderboard_data(leaderboard_type, category, limit=50):
        """Get leaderboard data for display."""
        try:
            leaderboard = Leaderboard.objects.get(
                leaderboard_type=leaderboard_type,
                category=category,
                is_active=True
            )
            
            entries = LeaderboardEntry.objects.filter(
                leaderboard=leaderboard
            ).select_related('user').order_by('rank')[:limit]
            
            return {
                'leaderboard': leaderboard,
                'entries': entries,
                'total_participants': LeaderboardEntry.objects.filter(leaderboard=leaderboard).count()
            }
            
        except Leaderboard.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_rank(user, leaderboard_type, category):
        """Get user's rank in a specific leaderboard."""
        try:
            leaderboard = Leaderboard.objects.get(
                leaderboard_type=leaderboard_type,
                category=category,
                is_active=True
            )
            
            entry = LeaderboardEntry.objects.filter(
                leaderboard=leaderboard,
                user=user
            ).first()
            
            return entry.rank if entry else None
            
        except Leaderboard.DoesNotExist:
            return None


class ProgressService:
    """Service for tracking user progress."""
    
    @staticmethod
    def update_user_progress(user):
        """Update user's progress towards goals."""
        if not user.is_employee:
            return
        
        # Get user's current stats
        stats = BadgeService._get_user_stats(user)
        
        # Update daily goal
        ProgressService._update_progress(
            user, 'daily_goal', 
            stats.get('trips_count', 0), 
            target_value=3  # Target: 3 trips per day
        )
        
        # Update weekly goal
        ProgressService._update_progress(
            user, 'weekly_goal',
            stats.get('trips_count', 0),
            target_value=15  # Target: 15 trips per week
        )
        
        # Update carbon goal
        ProgressService._update_progress(
            user, 'badge_progress',
            stats.get('carbon_saved', 0),
            target_value=10  # Target: 10 kg CO2 saved
        )
    
    @staticmethod
    def _update_progress(user, progress_type, current_value, target_value):
        """Update or create progress entry."""
        progress, created = UserProgress.objects.get_or_create(
            user=user,
            progress_type=progress_type,
            defaults={
                'target_value': target_value,
                'current_value': current_value
            }
        )
        
        if not created:
            progress.update_progress(current_value)
    
    @staticmethod
    def get_user_progress(user):
        """Get user's current progress."""
        return UserProgress.objects.filter(user=user).order_by('-start_date')
    
    @staticmethod
    def create_goal(user, goal_type, target_value, target_date=None):
        """Create a new progress goal for user."""
        return UserProgress.objects.create(
            user=user,
            progress_type=goal_type,
            target_value=target_value,
            target_date=target_date
        )


class StreakService:
    """Service for managing user streaks."""
    
    @staticmethod
    def update_user_streaks(user):
        """Update user's activity streaks."""
        if not user.is_employee:
            return
        
        today = timezone.now()
        
        # Update daily trips streak
        today_trips = Trip.objects.filter(
            employee=user.employee_profile,
            created_at__date=today.date()
        ).exists()
        
        if today_trips:
            streak, created = Streak.objects.get_or_create(
                user=user,
                streak_type='daily_trips',
                defaults={'current_streak': 1, 'last_activity_date': today}
            )
            
            if not created:
                streak.update_streak(today)
    
    @staticmethod
    def get_user_streaks(user):
        """Get user's current streaks."""
        return Streak.objects.filter(user=user)
    
    @staticmethod
    def get_streak_milestone_badge(streak_days):
        """Get badge for streak milestone."""
        if streak_days >= 30:
            return '30 Day Streak Master'
        elif streak_days >= 14:
            return 'Two Week Warrior'
        elif streak_days >= 7:
            return 'Week Warrior'
        elif streak_days >= 3:
            return 'Streak Starter'
        return None


class ChallengeService:
    """Service for managing community challenges."""
    
    @staticmethod
    def get_active_challenges():
        """Get currently active challenges."""
        now = timezone.now()
        return CommunityChallenge.objects.filter(
            status='active',
            start_date__lte=now,
            end_date__gte=now
        )
    
    @staticmethod
    def join_challenge(user, challenge_id):
        """Join a community challenge."""
        try:
            challenge = CommunityChallenge.objects.get(id=challenge_id, status='active')
            
            participant, created = ChallengeParticipant.objects.get_or_create(
                challenge=challenge,
                user=user,
                defaults={'joined_at': timezone.now()}
            )
            
            if created:
                logger.info(f"User {user.email} joined challenge {challenge.title}")
                Notification.objects.create(
                    user=user,
                    notification_type='success',
                    title='Challenge Joined',
                    message=f"You joined '{challenge.title}'. Track your progress and earn rewards!",
                    link='/employee/gamification/challenges/'
                )
            
            return participant
            
        except CommunityChallenge.DoesNotExist:
            return None
    
    @staticmethod
    def update_challenge_progress(user):
        """Update user's progress in active challenges."""
        participants = ChallengeParticipant.objects.filter(
            user=user,
            challenge__status='active',
            is_completed=False
        )
        
        user_stats = BadgeService._get_user_stats(user)
        
        for participant in participants:
            challenge = participant.challenge
            
            if challenge.target_metric == 'carbon_saved':
                participant.current_value = int(user_stats.get('carbon_saved', 0))
            elif challenge.target_metric == 'trips_count':
                participant.current_value = user_stats.get('trips_count', 0)
            
            # Check if completed
            if participant.current_value >= challenge.target_value:
                participant.is_completed = True
                participant.completed_at = timezone.now()
                
                # Award points
                UserPoints.objects.create(
                    user=user,
                    points_type='challenge',
                    points=challenge.reward_points,
                    description=f"Completed challenge: {challenge.title}",
                    related_object_id=challenge.id
                )
                
                # Award badge if specified
                if challenge.reward_badge:
                    UserBadge.objects.get_or_create(
                        user=user,
                        badge=challenge.reward_badge,
                        defaults={'is_earned': True}
                    )

                Notification.objects.create(
                    user=user,
                    notification_type='success',
                    title='Challenge Completed',
                    message=f"You completed '{challenge.title}' and earned {challenge.reward_points} points!",
                    link='/employee/gamification/challenges/'
                )
            
            participant.save()


class PointsService:
    """Service for managing user points."""
    
    @staticmethod
    def award_points(user, points_type, points, description, related_object_id=None):
        """Award points to user."""
        return UserPoints.objects.create(
            user=user,
            points_type=points_type,
            points=points,
            description=description,
            related_object_id=related_object_id
        )
    
    @staticmethod
    def get_user_total_points(user):
        """Get user's total points."""
        return UserPoints.objects.filter(user=user).aggregate(
            total=Sum('points')
        )['total'] or 0
    
    @staticmethod
    def get_user_points_history(user, limit=20):
        """Get user's points history."""
        return UserPoints.objects.filter(user=user).order_by('-created_at')[:limit]
