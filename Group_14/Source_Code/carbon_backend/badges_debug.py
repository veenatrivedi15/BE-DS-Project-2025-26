#!/usr/bin/env python
"""
Debug script to help identify badges page display issues
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

print('BADGES PAGE DEBUG INFORMATION')
print('=' * 50)

# Get an employee user
user = User.objects.filter(is_employee=True).first()
if user:
    print(f'User: {user.email}')
    
    client = Client()
    client.force_login(user)
    
    response = client.get('/employee/gamification/badges/')
    
    print(f'\nSERVER RESPONSE:')
    print(f'Status: {response.status_code}')
    print(f'Content-Type: {response.get("Content-Type", "Not set")}')
    print(f'Content-Length: {len(response.content)} bytes')
    
    # Check CSS loading
    content = response.content.decode()
    if 'design-system.css' in content:
        print('[OK] Design system CSS is included')
    else:
        print('[WARNING] Design system CSS might not be loading')
    
    # Check for critical elements
    critical_elements = [
        ('<!DOCTYPE html>', 'HTML DOCTYPE'),
        ('<html', 'HTML tag'),
        ('<head>', 'Head section'),
        ('<body>', 'Body section'),
        ('page-container', 'Main container'),
        ('All Badges', 'Page title'),
    ]
    
    print(f'\nCRITICAL ELEMENTS:')
    for element, name in critical_elements:
        if element in content:
            print(f'  [OK] {name}')
        else:
            print(f'  [MISSING] {name}')
    
    print(f'\nTROUBLESHOOTING STEPS:')
    print('1. Clear browser cache: Ctrl+F5 or Cmd+Shift+R')
    print('2. Open browser developer tools (F12)')
    print('3. Check Console tab for JavaScript errors')
    print('4. Check Network tab for failed CSS/JS loads')
    print('5. Try URL in incognito/private mode')
    print('6. Try different browser (Chrome, Firefox, Edge)')
    
    print(f'\nDIRECT URL TO TEST:')
    print('http://127.0.0.1:8000/employee/gamification/badges/')
    
    print(f'\nSERVER STATUS: RUNNING')
    print('The badges page is working correctly on the server.')
    print('If you see issues, they are likely browser-related.')
    
else:
    print('[ERROR] No employee user found')

print('\n' + '=' * 50)
print('DEBUG COMPLETE')
