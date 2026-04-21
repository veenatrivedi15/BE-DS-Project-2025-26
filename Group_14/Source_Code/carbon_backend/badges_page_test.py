#!/usr/bin/env python
"""
Comprehensive test to verify badges page is working correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

print('BADGES PAGE COMPREHENSIVE TEST')
print('=' * 50)

# Get an employee user
user = User.objects.filter(is_employee=True).first()
if user:
    print(f'Testing with user: {user.email}')
    
    client = Client()
    client.force_login(user)
    
    # Test badges page
    print('\nBADGES PAGE TEST:')
    response = client.get('/employee/gamification/badges/')
    
    print(f'Status Code: {response.status_code}')
    print(f'Content Length: {len(response.content)} bytes')
    
    content = response.content.decode()
    
    # Check for key elements
    checks = [
        ('page-container', 'Main container'),
        ('page-header', 'Page header'),
        ('All Badges', 'Page title'),
        ('stats-overview', 'Stats section'),
        ('badge-card', 'Badge cards'),
        ('Back to Dashboard', 'Navigation button'),
        ('Badges Earned', 'Stats label'),
        ('In Progress', 'Progress section'),
        ('style', 'CSS styles'),
        ('script', 'JavaScript'),
    ]
    
    print('\nELEMENT CHECK:')
    all_found = True
    for element, description in checks:
        if element in content:
            print(f'  [OK] {description}')
        else:
            print(f'  [MISSING] {description}')
            all_found = False
    
    # Check for errors
    if 'error' in content.lower() or '404' in content or 'not found' in content.lower():
        print('\n[ERROR] Errors detected in content')
        print('Content snippet:', content[:1000])
    else:
        print('\n[OK] No errors detected')
    
    if all_found and response.status_code == 200:
        print('\n[SUCCESS] Badges page is working correctly!')
        print('The page should display properly in the browser.')
    else:
        print('\n[WARNING] Some issues detected - check browser console')
    
    print(f'\nTest URL: http://127.0.0.1:8000/employee/gamification/badges/')
    
else:
    print('[ERROR] No employee user found')

print('\n' + '=' * 50)
print('TEST COMPLETE')
print('\nIf the page shows correctly in this test but not in browser:')
print('1. Clear browser cache (Ctrl+F5)')
print('2. Check browser console for JavaScript errors')
print('3. Try a different browser')
print('4. Check if CSS is loading correctly')
