#!/usr/bin/env python
import os
import django
from django.db import models

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.gamification_models import Badge, UserBadge, UserPoints, UserProgress, Streak, CommunityChallenge, ChallengeParticipant

User = get_user_model()

print('=== COMPREHENSIVE ERROR CHECK ===')

# Check 1: Model field existence
print('\n1. CHECKING MODEL FIELDS...')

# Check CommunityChallenge fields
try:
    challenge_fields = [f.name for f in CommunityChallenge._meta.get_fields()]
    print(f'CommunityChallenge fields: {challenge_fields}')
    
    # Check if target field exists
    has_target = 'target' in challenge_fields
    has_target_value = 'target_value' in challenge_fields
    has_action_text = 'action_text' in challenge_fields
    
    print(f'  - has "target": {has_target}')
    print(f'  - has "target_value": {has_target_value}')
    print(f'  - has "action_text": {has_action_text}')
    
except Exception as e:
    print(f'Error checking CommunityChallenge: {e}')

# Check ChallengeParticipant fields
try:
    participant_fields = [f.name for f in ChallengeParticipant._meta.get_fields()]
    print(f'ChallengeParticipant fields: {participant_fields}')
    
    has_progress = 'progress' in participant_fields
    has_current_value = 'current_value' in participant_fields
    
    print(f'  - has "progress": {has_progress}')
    print(f'  - has "current_value": {has_current_value}')
    
except Exception as e:
    print(f'Error checking ChallengeParticipant: {e}')

# Check 2: Test actual data access
print('\n2. TESTING DATA ACCESS...')

try:
    user = User.objects.filter(is_employee=True).first()
    if user:
        print(f'Testing with user: {user.email}')
        
        # Test user challenges
        user_challenges = ChallengeParticipant.objects.filter(user=user)
        print(f'User challenges: {user_challenges.count()}')
        
        for participant in user_challenges[:3]:
            try:
                print(f'  Challenge: {participant.challenge.title}')
                print(f'    - participant.current_value: {participant.current_value}')
                print(f'    - participant.challenge.target_value: {participant.challenge.target_value}')
                
                # Test the problematic calculation
                if participant.challenge.target_value and participant.challenge.target_value > 0:
                    percentage = (participant.current_value / participant.challenge.target_value) * 100
                    print(f'    - calculated percentage: {percentage}%')
                
            except Exception as e:
                print(f'    ERROR accessing challenge data: {e}')
                
except Exception as e:
    print(f'Error in data access test: {e}')

# Check 3: API Key issues
print('\n3. CHECKING API CONFIGURATION...')

from django.conf import settings
openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', None)
if openrouter_key:
    print(f'OpenRouter API key exists: {openrouter_key[:20]}...')
    if 'test-key' in openrouter_key or 'your-' in openrouter_key:
        print('  WARNING: Using test/placeholder API key')
else:
    print('OpenRouter API key not found')

print('\n4. RECOMMENDATIONS...')
print('- Fix CommunityChallenge.target -> target_value references')
print('- Fix ChallengeParticipant.progress -> current_value references') 
print('- Update OpenRouter API key if needed')
print('- Add proper error handling in gamification views')

print('\n=== ERROR CHECK COMPLETE ===')
