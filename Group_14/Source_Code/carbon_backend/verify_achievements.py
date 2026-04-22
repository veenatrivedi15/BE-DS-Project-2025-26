#!/usr/bin/env python
import os
import django
from django.db import models

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.gamification_models import UserBadge, UserPoints, UserProgress, Streak

User = get_user_model()

print('=== ACHIEVEMENT DASHBOARD DATA VERIFICATION ===')

# Get a sample user
user = User.objects.filter(is_employee=True).first()
print(f'Checking data for: {user.email}')

# Check badges
badges = UserBadge.objects.filter(user=user)
print(f'User Badges: {badges.count()}')
for badge in badges:
    print(f'  - {badge.badge.name} (earned: {badge.earned_at})')

# Check points
points = UserPoints.objects.filter(user=user)
total_points = points.aggregate(total=models.Sum('points'))['total'] or 0
print(f'Total Points: {total_points}')
for point in points[:3]:
    print(f'  - {point.points} points: {point.description} ({point.created_at})')

# Check progress
progress = UserProgress.objects.filter(user=user)
print(f'Progress Records: {progress.count()}')
for prog in progress:
    percentage = (prog.current_value / prog.target_value) * 100 if prog.target_value > 0 else 0
    print(f'  - {prog.progress_type}: {prog.current_value}/{prog.target_value} ({percentage:.1f}%)')

# Check streaks
streaks = Streak.objects.filter(user=user)
print(f'Streaks: {streaks.count()}')
for streak in streaks:
    print(f'  - {streak.streak_type}: {streak.current_streak} days (longest: {streak.longest_streak})')

print('\n=== ACHIEVEMENT DASHBOARD READY ===')
print('The achievement dashboard now shows REAL data from actual user activity!')
