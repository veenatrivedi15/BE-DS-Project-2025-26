#!/usr/bin/env python
"""
Quick script to verify Google Maps API key is set correctly.
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
print("Google Maps API Key Verification")
print("=" * 60)

api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)

if not api_key:
    print("❌ ERROR: GOOGLE_MAPS_API_KEY is not set")
    sys.exit(1)

if api_key == 'AIzaSyA-test-key-for-development-only':
    print("⚠️  WARNING: Using default test key")
    print("   This key will not work. Please set a real API key.")
    sys.exit(1)

print(f"✅ API Key is configured")
print(f"   Length: {len(api_key)} characters")
print(f"   First 15 chars: {api_key[:15]}...")
print(f"   Last 10 chars: ...{api_key[-10:]}")

# Check if it matches the new key
if api_key.startswith('AIzaSyCwcFvh1vVe979dldumRkBnV01VU3msn30'):
    print("✅ Matches the new API key you provided!")
else:
    print("⚠️  Note: API key doesn't match the one you mentioned")
    print("   Make sure you've set it in the environment variable")

print("\n" + "=" * 60)
print("Next Steps:")
print("=" * 60)
print("1. Restart Django server if you just set the environment variable")
print("2. Clear browser cache")
print("3. Refresh the trip log page")
print("4. Check browser console for any errors")
print("=" * 60)


