// Pollution Dashboard JavaScript - OpenWeather AQI Tiles
let pollutionMap;
let aqiLayer;
let currentPollutant = 'pm2_5';
let industrialZonesVisible = true;
let industrialZoneCircles = [];

document.addEventListener('DOMContentLoaded', function() {
    // Map will be initialized by Google Maps callback
    console.log('DOM loaded, waiting for Google Maps callback...');
});

function initPollutionMap() {
    console.log('Initializing pollution map...');
    
    // Initialize map centered on Mumbai-Thane region
    const mapOptions = {
        center: { lat: 19.2183, lng: 72.9781 }, // Thane, India
        zoom: 11,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        styles: [
            {
                featureType: "poi",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            }
        ],
        // Restrict to Mumbai-Thane region with expanded coverage
        restriction: {
            latLngBounds: {
                north: 19.45,  // Expanded north
                south: 18.75,  // Expanded south  
                west: 72.65,   // Expanded west
                east: 73.25,   // Expanded east
            },
            strictBounds: false
        }
    };
    
    pollutionMap = new google.maps.Map(document.getElementById('pollution-map'), mapOptions);
    console.log('Map created successfully');
    
    // Add a test marker to verify map is working
    const testMarker = new google.maps.Marker({
        position: { lat: 19.2183, lng: 72.9781 },
        map: pollutionMap,
        title: 'Thane Center - Test Marker',
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 10,
            fillColor: '#FF0000',
            fillOpacity: 0.8,
            strokeColor: '#FFFFFF',
            strokeWeight: 2
        }
    });
    console.log('Test marker added');
    
    // Load AQI tiles for Mumbai-Thane region
    loadAQILayer(currentPollutant);
    
    // Load industrial zones with pollution data
    loadIndustrialZones();
}

function loadIndustrialZones() {
    const zonesScript = document.getElementById('industrial-zones-data');
    if (!zonesScript) {
        console.warn('No industrial zones data found in DOM.');
        return;
    }

    let industrialZones = [];
    try {
        industrialZones = JSON.parse(zonesScript.textContent || '[]');
    } catch (error) {
        console.error('Failed to parse industrial zones data:', error);
        return;
    }

    if (!industrialZones.length) {
        console.warn('Industrial zones list is empty.');
        return;
    }

    // Add circles for each industrial zone with soft fading boundaries
    industrialZones.forEach(zone => {
        const zoneType = zone.zone_type || zone.type || 'other_industrial';
        const zoneLat = parseFloat(zone.latitude || zone.lat);
        const zoneLng = parseFloat(zone.longitude || zone.lng);

        if (Number.isNaN(zoneLat) || Number.isNaN(zoneLng)) {
            return;
        }

        // Create multiple circles for gradient effect
        const circles = [];
        const maxRadius = 2500; // 2.5km max radius
        const steps = 5; // Number of gradient steps
        
        for (let i = 0; i < steps; i++) {
            const radius = maxRadius * (1 - i / steps);
            const opacity = 0.15 * (1 - i / steps); // Fade out
            
            const circle = new google.maps.Circle({
                strokeColor: getRiskColor(zoneType),
                strokeOpacity: opacity * 0.5,
                strokeWeight: 1,
                fillColor: getRiskColor(zoneType),
                fillOpacity: opacity,
                map: pollutionMap,
                center: { lat: zoneLat, lng: zoneLng },
                radius: radius,
                title: zone.name,
                clickable: i === 0 // Only make outermost circle clickable
            });
            
            circles.push(circle);
        }

        // Store all circles for toggling
        industrialZoneCircles.push(...circles);

        // Add info window with detailed pollution data (attach to outermost circle)
        const infoWindow = new google.maps.InfoWindow({
            content: `
                <div style="padding: 10px; max-width: 300px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">${zone.name}</h4>
                    <table style="width: 100%; font-size: 12px;">
                        <tr><td><strong>Type:</strong></td><td>${zoneType.replace('_', ' ')}</td></tr>
                        <tr><td><strong>Emission Intensity:</strong></td><td>${zone.emission_intensity ?? 'N/A'} t/yr</td></tr>
                    </table>
                </div>
            `
        });

        // Add click listener to show info window (only on outermost circle)
        circles[0].addListener('click', () => {
            infoWindow.setPosition({ lat: zoneLat, lng: zoneLng });
            infoWindow.open(pollutionMap);
        });

        // Add hover effect to all circles
        circles.forEach((circle, index) => {
            circle.addListener('mouseover', () => {
                const baseOpacity = 0.15 * (1 - index / steps);
                circle.setOptions({ fillOpacity: baseOpacity * 1.5, strokeWeight: 2 });
            });

            circle.addListener('mouseout', () => {
                const baseOpacity = 0.15 * (1 - index / steps);
                circle.setOptions({ fillOpacity: baseOpacity, strokeWeight: 1 });
            });
        });
    });

    console.log(`Loaded ${industrialZones.length} industrial zones from backend data`);
}

function toggleIndustrialZones() {
    industrialZonesVisible = !industrialZonesVisible;
    
    industrialZoneCircles.forEach(circle => {
        circle.setMap(industrialZonesVisible ? pollutionMap : null);
    });
    
    console.log(`Industrial zones ${industrialZonesVisible ? 'shown' : 'hidden'}`);
}

function loadAQILayer(pollutant) {
    // Clear existing AQI layer
    if (aqiLayer) {
        pollutionMap.overlayMapTypes.clear();
    }
    
    currentPollutant = pollutant;
    
    // Create AQI tile overlay with multiple approaches
    aqiLayer = new google.maps.ImageMapType({
        getTileUrl: function(coord, zoom) {
            // Only load tiles for Mumbai-Thane region (zoom 8-15)
            if (zoom < 8 || zoom > 15) {
                return null;
            }
            
            // Temporarily remove bounds restriction to test tile loading
            // Check if tile is within Mumbai-Thane bounds
            // const tileBounds = getTileBounds(coord, zoom);
            // const mumbaiThaneBounds = {
            //     north: 19.45,  // Expanded north
            //     south: 18.75,  // Expanded south  
            //     west: 72.65,   // Expanded west
            //     east: 73.25    // Expanded east
            // };
            
            // if (!boundsIntersect(tileBounds, mumbaiThaneBounds)) {
            //     return null;
            // }
            
            const tileUrl = `/pollution/aqi-tiles/${pollutant}/${zoom}/${coord.x}/${coord.y}.png`;
            console.log('Loading tile:', tileUrl);
            return tileUrl;
        },
        tileSize: new google.maps.Size(256, 256),
        opacity: 0.95,
        name: "AQI",
        maxZoom: 15,
        minZoom: 8
    });
    
    // Add overlay to map
    pollutionMap.overlayMapTypes.push(aqiLayer);
    
    // Alternative approach: Create ground overlay
    setTimeout(() => {
        console.log('AQI overlay length:', pollutionMap.overlayMapTypes.getLength());
        console.log('Map zoom level:', pollutionMap.getZoom());
        
        // Force map refresh to trigger overlay rendering
        const currentZoom = pollutionMap.getZoom();
        pollutionMap.setZoom(currentZoom);
        
        console.log(`Loaded ${pollutant} AQI tiles for Mumbai-Thane region`);
    }, 500);
}

function getTileBounds(coord, zoom) {
    const n = Math.pow(2, zoom);
    const x = coord.x;
    const y = coord.y;
    
    const lonWest = (x / n) * 360.0 - 180.0;
    const latNorth = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * (180.0 / Math.PI);
    
    const lonEast = ((x + 1) / n) * 360.0 - 180.0;
    const latSouth = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n))) * (180.0 / Math.PI);
    
    return {
        north: latNorth,
        south: latSouth,
        west: lonWest,
        east: lonEast
    };
}

function boundsIntersect(bounds1, bounds2) {
    return !(bounds1.east < bounds2.west || 
             bounds1.west > bounds2.east || 
             bounds1.north < bounds2.south || 
             bounds1.south > bounds2.north);
}

function refreshMapData() {
    // Reload current AQI layer
    loadAQILayer(currentPollutant);
    
    // Show feedback
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = '🔄 Refreshing...';
    button.disabled = true;
    
    setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
    }, 2000);
}

// Toggle AQI layer visibility
function toggleAQILayer() {
    if (aqiLayer) {
        const isVisible = pollutionMap.overlayMapTypes.getLength() > 0;
        if (isVisible) {
            pollutionMap.overlayMapTypes.clear();
            console.log('AQI layer hidden');
        } else {
            pollutionMap.overlayMapTypes.push(aqiLayer);
            console.log('AQI layer shown');
        }
    }
}

// Handle map resize
window.addEventListener('resize', function() {
    if (pollutionMap) {
        google.maps.event.trigger(pollutionMap, 'resize');
    }
});

// Error handling for map initialization
window.addEventListener('load', function() {
    setTimeout(function() {
        const mapElement = document.getElementById('pollution-map');
        if (mapElement && mapElement.innerHTML.includes('Loading')) {
            mapElement.innerHTML = `
                <div class="p-4 bg-yellow-100 text-yellow-800 rounded">
                    <strong>Map Loading Issue</strong><br>
                    <p class="mt-2 text-sm">The map is taking longer than expected to load. Please:</p>
                    <ul class="list-disc list-inside mt-2 text-sm">
                        <li>Check your internet connection</li>
                        <li>Refresh page</li>
                        <li>Try a different browser</li>
                    </ul>
                </div>
            `;
        }
    }, 15000);
});

function getRiskColor(zoneType) {
    const colors = {
        'heavy_industry': '#dc2626',
        'manufacturing': '#ef4444',
        'power_plant': '#f59e0b',
        'chemical_plant': '#ef4444',
        'steel_plant': '#ef4444',
        'textile_industry': '#f59e0b',
        'other_industrial': '#6b7280'
    };
    return colors[zoneType] || '#6b7280';
}

function getAQIColor(aqi) {
    if (aqi <= 50) return '#10b981';
    if (aqi <= 100) return '#f59e0b';
    if (aqi <= 150) return '#f97316';
    return '#ef4444';
}

function getAQILevel(aqi) {
    if (aqi <= 50) return 'Good';
    if (aqi <= 100) return 'Moderate';
    if (aqi <= 150) return 'Unhealthy';
    return 'Hazardous';
}

function getAQIDescription(aqi) {
    if (aqi <= 50) return 'Air quality is satisfactory, and air pollution poses little or no risk.';
    if (aqi <= 100) return 'Air quality is acceptable; however, for some pollutants there may be a moderate health concern for a very small number of people.';
    if (aqi <= 150) return 'Members of sensitive groups may experience health effects. The general public is less likely to be affected.';
    return 'Health warnings of emergency conditions. Everyone is more likely to be affected.';
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function markAlertRead(alertId) {
    fetch(`/pollution/api/mark-alert-read/${alertId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    })
    .catch(error => console.error('Error:', error));
}
