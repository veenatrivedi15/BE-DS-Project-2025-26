#!/usr/bin/env python
"""
Quick script to check if Google Maps API key is configured correctly.
Run this from the carbon_backend directory.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
django.setup()

from django.conf import settings

print("=" * 60)
print("Google Maps API Key Configuration Check")
print("=" * 60)

api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)

if not api_key:
    print("❌ ERROR: GOOGLE_MAPS_API_KEY is not set in settings")
    print("\nTo fix this:")
    print("1. Set environment variable: GOOGLE_MAPS_API_KEY='your-key'")
    print("2. Or add to .env file: GOOGLE_MAPS_API_KEY=your-key")
    sys.exit(1)

if api_key == 'AIzaSyA-test-key-for-development-only':
    print("⚠️  WARNING: Using default test key")
    print("   This key will not work. Please set a real API key.")
    sys.exit(1)

if len(api_key) < 20:
    print("⚠️  WARNING: API key seems too short")
    print(f"   Length: {len(api_key)} characters")
    print("   Valid Google Maps API keys are usually 39 characters")
    sys.exit(1)

print(f"✅ API Key is configured")
print(f"   Length: {len(api_key)} characters")
print(f"   First 10 chars: {api_key[:10]}...")
print(f"   Last 10 chars: ...{api_key[-10:]}")

print("\n" + "=" * 60)
print("Next Steps:")
print("=" * 60)
print("1. Verify the API key in Google Cloud Console")
print("2. Ensure 'Maps JavaScript API' is enabled")
print("3. Ensure 'Places API' is enabled")
print("4. Check that billing is enabled")
print("5. If using restrictions, add localhost:8000 to allowed referrers")
print("=" * 60)


