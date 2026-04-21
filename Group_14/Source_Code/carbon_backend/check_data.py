#!/usr/bin/env python
import os
import django
from django.db import models

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from trips.models import Trip
from core.wallet_service import WalletService
from core.gamification_models import Badge, UserBadge, UserPoints, UserProgress, Streak

User = get_user_model()

print('=== USERS & DATA CHECK ===')
users = User.objects.filter(is_employee=True)
print(f'Total employee users: {users.count()}')

for user in users[:3]:
    print(f'\nUser: {user.email}')
    print(f'  - Employee Profile: {hasattr(user, "employee_profile")}')
    
    if hasattr(user, 'employee_profile'):
        trips = Trip.objects.filter(employee=user.employee_profile)
        print(f'  - Total Trips: {trips.count()}')
        print(f'  - Verified Trips: {trips.filter(verification_status="verified").count()}')
        
        # Show some trip details
        for trip in trips.filter(verification_status="verified")[:2]:
            print(f'    Trip: {trip.transport_mode}, {trip.distance_km}km, {trip.carbon_savings}kg CO2 saved')
    
    balance = WalletService.get_wallet_balance(user)
    print(f'  - Wallet Balance: {balance["total_balance"]:.2f} credits')
    
    # Check gamification data
    badges = UserBadge.objects.filter(user=user)
    print(f'  - User Badges: {badges.count()}')
    
    points = UserPoints.objects.filter(user=user)
    total_points = points.aggregate(total=models.Sum('points'))['total'] or 0
    print(f'  - Total Points: {total_points}')

print('\n=== BADGES IN SYSTEM ===')
badges = Badge.objects.all()
print(f'Total badges available: {badges.count()}')
for badge in badges[:5]:
    print(f'  - {badge.name}: {badge.description}')

print('\n=== USER PROGRESS ===')
progress = UserProgress.objects.all()
print(f'Total progress records: {progress.count()}')

print('\n=== STREAKS ===')
streaks = Streak.objects.all()
print(f'Total streak records: {streaks.count()}')
