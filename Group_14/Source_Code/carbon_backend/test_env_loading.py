#!/usr/bin/env python
"""
Test if Django is loading the correct API key from .env
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

# Check what API key Django is loading
api_key = settings.GOOGLE_MAPS_API_KEY
print(f"Django loaded API key: {api_key[:20]}...{api_key[-10:]}")
print(f"API key length: {len(api_key)}")

# Check which key it is
if api_key == "AIzaSyDDmDuM0Y6ldYJ65BQ4qttBzhkr78jW42M":
    print("CORRECT: Using working API key")
elif api_key == "AIzaSyCwcFvh1vVe979dldumRkBnV01VU3msn30":
    print("WRONG: Still using old non-working API key")
else:
    print(f"UNKNOWN: Using unexpected API key")

# Check environment variable directly
env_key = os.getenv('GOOGLE_MAPS_API_KEY')
print(f"Environment variable: {env_key[:20] if env_key else 'None'}...{env_key[-10:] if env_key else 'None'}")
