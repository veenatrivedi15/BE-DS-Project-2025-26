#!/usr/bin/env python
"""
Simple Google Maps API Test - No Django dependency
"""

import requests
import json

# Your API key from settings
API_KEY = "AIzaSyDDmDuM0Y6ldYJ65BQ4qttBzhkr78jW42M"
BASE_URL = "https://maps.googleapis.com/maps/api"

def test_api():
    print(f"🔑 Testing API Key: {API_KEY[:20]}...")
    print("=" * 60)
    
    # Test 1: Geocoding
    print("\n📍 Test 1: Geocoding API")
    url = f"{BASE_URL}/geocode/json"
    params = {
        'address': 'Mumbai, India',
        'key': API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if response.status_code == 200 and data.get('status') == 'OK':
            location = data['results'][0]['geometry']['location']
            print(f"✅ Geocoding SUCCESS: {location['lat']}, {location['lng']}")
        else:
            print(f"❌ Geocoding FAILED: {data.get('status', 'Unknown error')}")
            if 'error_message' in data:
                print(f"   Error: {data['error_message']}")
    except Exception as e:
        print(f"❌ Geocoding ERROR: {str(e)}")
    
    # Test 2: Directions
    print("\n🛣️ Test 2: Directions API")
    url = f"{BASE_URL}/directions/json"
    params = {
        'origin': '19.0760,72.8777',  # Mumbai
        'destination': '19.2183,72.9781',  # Thane
        'key': API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
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
            if 'error' in data:
                print(f"   Error Details: {json.dumps(data['error'], indent=4)}")
    except Exception as e:
        print(f"❌ Directions ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("📋 Analysis:")
    print("   - If tests show REQUEST_DENIED:")
    print("     → API key restrictions blocking access")
    print("     → Add localhost* to HTTP referrers in Google Cloud Console")
    print("   - If tests show BILLING_NOT_ENABLED:")
    print("     → Billing account issue")
    print("     → Check billing settings in Google Cloud Console")

if __name__ == "__main__":
    test_api()
