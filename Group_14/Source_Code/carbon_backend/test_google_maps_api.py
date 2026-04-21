#!/usr/bin/env python
"""
Google Maps API Test Script
Tests all required Google Maps APIs to verify functionality
"""

import os
import requests
import json
from django.conf import settings

def test_google_maps_api():
    """Test Google Maps API functionality"""
    
    api_key = settings.GOOGLE_MAPS_API_KEY
    base_url = "https://maps.googleapis.com/maps/api"
    
    print(f"🔑 Testing with API Key: {api_key[:20]}...")
    print("=" * 60)
    
    # Test 1: Geocoding API
    print("\n📍 Test 1: Geocoding API")
    geocode_url = f"{base_url}/geocode/json"
    params = {
        'address': 'Mumbai, India',
        'key': api_key
    }
    
    try:
        response = requests.get(geocode_url, params=params)
        data = response.json()
        if response.status_code == 200 and data.get('status') == 'OK':
            location = data['results'][0]['geometry']['location']
            print(f"✅ Geocoding SUCCESS: {location['lat']}, {location['lng']}")
        else:
            print(f"❌ Geocoding FAILED: {data.get('status', 'Unknown error')}")
            print(f"   Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"❌ Geocoding ERROR: {str(e)}")
    
    # Test 2: Directions API
    print("\n🛣️ Test 2: Directions API")
    directions_url = f"{base_url}/directions/json"
    params = {
        'origin': '19.0760,72.8777',  # Mumbai
        'destination': '19.2183,72.9781',  # Thane
        'key': api_key
    }
    
    try:
        response = requests.get(directions_url, params=params)
        data = response.json()
        if response.status_code == 200 and data.get('status') == 'OK':
            route = data['routes'][0]
            distance = route['legs'][0]['distance']['text']
            duration = route['legs'][0]['duration']['text']
            print(f"✅ Directions SUCCESS: {distance}, {duration}")
        else:
            print(f"❌ Directions FAILED: {data.get('status', 'Unknown error')}")
            if 'error_message' in data:
                print(f"   Error: {data['error_message']}")
            print(f"   Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"❌ Directions ERROR: {str(e)}")
    
    # Test 3: Places API (Nearby Search)
    print("\n🏪 Test 3: Places API")
    places_url = f"{base_url}/place/nearbysearch/json"
    params = {
        'location': '19.0760,72.8777',
        'radius': '5000',
        'type': 'restaurant',
        'key': api_key
    }
    
    try:
        response = requests.get(places_url, params=params)
        data = response.json()
        if response.status_code == 200 and data.get('status') == 'OK':
            places_count = len(data.get('results', []))
            print(f"✅ Places SUCCESS: Found {places_count} places")
        else:
            print(f"❌ Places FAILED: {data.get('status', 'Unknown error')}")
            print(f"   Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"❌ Places ERROR: {str(e)}")
    
    # Test 4: Static Maps API
    print("\n🗺️ Test 4: Static Maps API")
    static_url = f"{base_url}/staticmap"
    params = {
        'center': '19.0760,72.8777',
        'zoom': '13',
        'size': '600x400',
        'key': api_key
    }
    
    try:
        response = requests.get(static_url, params=params)
        if response.status_code == 200:
            print(f"✅ Static Maps SUCCESS: Image retrieved ({len(response.content)} bytes)")
        else:
            print(f"❌ Static Maps FAILED: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Static Maps ERROR: {str(e)}")
    
    # Test 5: Distance Matrix API
    print("\n📏 Test 5: Distance Matrix API")
    distance_url = f"{base_url}/distancematrix/json"
    params = {
        'origins': '19.0760,72.8777',
        'destinations': '19.2183,72.9781',
        'key': api_key
    }
    
    try:
        response = requests.get(distance_url, params=params)
        data = response.json()
        if response.status_code == 200 and data.get('status') == 'OK':
            element = data['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                distance = element['distance']['text']
                duration = element['duration']['text']
                print(f"✅ Distance Matrix SUCCESS: {distance}, {duration}")
            else:
                print(f"❌ Distance Matrix FAILED: {element['status']}")
        else:
            print(f"❌ Distance Matrix FAILED: {data.get('status', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Distance Matrix ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print("   - If most tests show 'REQUEST_DENIED' or 'BILLING_NOT_ENABLED':")
    print("     → Check API key restrictions in Google Cloud Console")
    print("     → Ensure localhost is added to HTTP referrers")
    print("   - If tests work but app doesn't:")
    print("     → Check how API key is loaded in frontend")
    print("     → Verify browser network requests")

if __name__ == "__main__":
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbon_backend.settings')
    
    import django
    django.setup()
    
    test_google_maps_api()
