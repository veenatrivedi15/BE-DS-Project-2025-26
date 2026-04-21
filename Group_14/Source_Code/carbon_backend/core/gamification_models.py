"""
Gamification models for leaderboards, badges, and progress tracking
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from users.models import CustomUser, EmployeeProfile, EmployerProfile

User = get_user_model()


class Badge(models.Model):
    """Model for achievement badges."""
    
    BADGE_TYPES = (
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('special', 'Special'),
    )
    
    BADGE_CATEGORIES = (
        ('trips', 'Trips'),
        ('carbon', 'Carbon Savings'),
        ('streak', 'Streak'),
        ('milestone', 'Milestone'),
        ('community', 'Community'),
        ('special', 'Special Achievement'),
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    badge_type = models.CharField(max_length=10, choices=BADGE_TYPES)
    category = models.CharField(max_length=15, choices=BADGE_CATEGORIES)
    icon = models.CharField(max_length=50, default='🏆')
    condition_type = models.CharField(
        max_length=20,
        choices=(
            ('trips_count', 'Number of Trips'),
            ('carbon_saved', 'Carbon Saved'),
            ('streak_days', 'Consecutive Days'),
            ('special_condition', 'Special Condition'),
        )
    )
    condition_value = models.IntegerField(help_text="Value required to earn this badge")
    points = models.IntegerField(default=10, help_text="Points awarded for this badge")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['badge_type', 'category', 'points']
    
    def __str__(self):
        return f"{self.name} ({self.get_badge_type_display()})"


class UserBadge(models.Model):
    """Model for tracking user earned badges."""
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='earned_badges'
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='awarded_to'
    )
    earned_at = models.DateTimeField(default=timezone.now)
    progress_value = models.IntegerField(help_text="Current progress towards badge")
    is_earned = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.badge.name}"


class Leaderboard(models.Model):
    """Model for leaderboards."""
    
    LEADERBOARD_TYPES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('all_time', 'All Time'),
    )
    
    LEADERBOARD_CATEGORIES = (
        ('carbon_saved', 'Carbon Saved'),
        ('trips_count', 'Number of Trips'),
        ('badges_count', 'Badges Earned'),
        ('streak_days', 'Streak Days'),
        ('points', 'Total Points'),
    )
    
    name = models.CharField(max_length=100)
    leaderboard_type = models.CharField(max_length=10, choices=LEADERBOARD_TYPES)
    category = models.CharField(max_length=15, choices=LEADERBOARD_CATEGORIES)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['leaderboard_type', 'category']
    
    def __str__(self):
        return f"{self.name} ({self.get_leaderboard_type_display()})"


class LeaderboardEntry(models.Model):
    """Model for individual leaderboard entries."""
    
    leaderboard = models.ForeignKey(
        Leaderboard,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='leaderboard_entries'
    )
    value = models.DecimalField(max_digits=15, decimal_places=4)
    rank = models.IntegerField()
    previous_rank = models.IntegerField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['leaderboard', 'user']
        ordering = ['rank']
        indexes = [
            models.Index(fields=['leaderboard', 'rank']),
            models.Index(fields=['user', '-last_updated']),
        ]
    
    def __str__(self):
        return f"#{self.rank} {self.user.email} - {self.value}"


class UserProgress(models.Model):
    """Model for tracking user progress towards goals."""
    
    PROGRESS_TYPES = (
        ('daily_goal', 'Daily Goal'),
        ('weekly_goal', 'Weekly Goal'),
        ('monthly_goal', 'Monthly Goal'),
        ('badge_progress', 'Badge Progress'),
        ('streak_progress', 'Streak Progress'),
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='progress_tracking'
    )
    progress_type = models.CharField(max_length=20, choices=PROGRESS_TYPES)
    target_value = models.DecimalField(max_digits=10, decimal_places=2)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    percentage_complete = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    start_date = models.DateTimeField(default=timezone.now)
    target_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'progress_type']
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_progress_type_display()}: {self.percentage_complete}%"
    
    def update_progress(self, new_value):
        """Update progress and calculate percentage."""
        self.current_value = new_value
        if self.target_value > 0:
            current_value = Decimal(str(new_value))
            target_value = Decimal(str(self.target_value))
            self.percentage_complete = min(Decimal('100'), (current_value / target_value) * Decimal('100'))
        
        if self.percentage_complete >= 100 and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
        
        self.save()


class Streak(models.Model):
    """Model for tracking user streaks."""
    
    STREAK_TYPES = (
        ('daily_trips', 'Daily Trips'),
        ('sustainable_transport', 'Sustainable Transport'),
        ('carbon_goal', 'Carbon Goal'),
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='streaks'
    )
    streak_type = models.CharField(max_length=25, choices=STREAK_TYPES)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'streak_type']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_streak_type_display()}: {self.current_streak} days"
    
    def update_streak(self, activity_date):
        """Update streak based on activity date."""
        if self.last_activity_date:
            days_diff = (activity_date.date() - self.last_activity_date.date()).days
            
            if days_diff == 1:
                # Consecutive day
                self.current_streak += 1
                self.is_active = True
            elif days_diff > 1:
                # Streak broken
                if self.current_streak > self.longest_streak:
                    self.longest_streak = self.current_streak
                self.current_streak = 1
                self.is_active = True
            # days_diff == 0 means same day, no update needed
        else:
            # First activity
            self.current_streak = 1
            self.is_active = True
        
        self.last_activity_date = activity_date
        
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.save()


class CommunityChallenge(models.Model):
    """Model for community challenges."""
    
    CHALLENGE_TYPES = (
        ('individual', 'Individual'),
        ('team', 'Team'),
        ('company', 'Company'),
    )
    
    CHALLENGE_STATUS = (
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=10, choices=CHALLENGE_TYPES)
    status = models.CharField(max_length=10, choices=CHALLENGE_STATUS, default='upcoming')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    target_metric = models.CharField(
        max_length=20,
        choices=(
            ('carbon_saved', 'Carbon Saved'),
            ('trips_count', 'Number of Trips'),
            ('participants', 'Number of Participants'),
        )
    )
    target_value = models.IntegerField()
    reward_points = models.IntegerField(default=100)
    reward_badge = models.ForeignKey(
        Badge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='challenges'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class ChallengeParticipant(models.Model):
    """Model for tracking challenge participants."""
    
    challenge = models.ForeignKey(
        CommunityChallenge,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='challenges'
    )
    joined_at = models.DateTimeField(default=timezone.now)
    current_value = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['challenge', 'user']
    
    def __str__(self):
        return f"{self.user.email} - {self.challenge.title}"


class UserPoints(models.Model):
    """Model for tracking user points from various activities."""
    
    POINT_TYPES = (
        ('trip', 'Trip Completion'),
        ('badge', 'Badge Earned'),
        ('streak', 'Streak Milestone'),
        ('challenge', 'Challenge Completion'),
        ('bonus', 'Bonus Points'),
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='points_history'
    )
    points_type = models.CharField(max_length=10, choices=POINT_TYPES)
    points = models.IntegerField()
    description = models.CharField(max_length=200)
    related_object_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email}: +{self.points} ({self.get_points_type_display()})"
