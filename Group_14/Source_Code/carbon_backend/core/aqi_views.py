# World Air Quality Index Tile Proxy - Secure and Cached
import os
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
import requests

# No API key needed for WAQI tiles
@cache_page(60 * 15)  # Cache for 15 minutes
def aqi_tile_proxy(request, layer, z, x, y):
    """
    Proxy for World Air Quality Index tiles to improve performance
    """
    # Map pollutant names to WAQI layer names
    layer_mapping = {
        'pm2_5': 'usepa-pm25',
        'pm10': 'usepa-pm10', 
        'no2': 'usepa-no2',
        'o3': 'usepa-o3',
        'so2': 'usepa-so2',
        'co': 'usepa-co',
        'aqi': 'usepa-aqi'
    }
    
    waqi_layer = layer_mapping.get(layer, 'usepa-aqi')
    
    url = f"https://tiles.aqicn.org/tiles/{waqi_layer}/{z}/{x}/{y}.png"
    
    try:
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        
        return HttpResponse(
            r.content,
            content_type="image/png"
        )
    except requests.RequestException as e:
        # Return transparent 1x1 PNG on error
        transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82'
        return HttpResponse(
            transparent_png,
            content_type="image/png"
        )
