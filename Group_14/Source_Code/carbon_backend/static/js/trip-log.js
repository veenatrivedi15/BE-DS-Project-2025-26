// Global variables for map components
let map, startMarker, endMarker, directionsService, directionsRenderer;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM Content Loaded");
    
    // Setup transport mode selection
    setupTransportOptions();
    
    // Additional direct event handling for transport options - using event delegation
    const optionsContainer = document.getElementById('transport-options-container');
    if (optionsContainer) {
        optionsContainer.addEventListener('click', function(e) {
            // Find the closest transport option
            const option = e.target.closest('.transport-option');
            if (option) {
                const transportMode = option.getAttribute('data-mode');
                console.log("Direct click handler triggered for:", transportMode);
                
                // Clear all selections
                document.querySelectorAll('.transport-option').forEach(opt => {
                    opt.classList.remove('selected');
                });
                
                // Set this option as selected
                option.classList.add('selected');
                
                // Update form value
                const transportInput = document.getElementById('transport-mode');
                if (transportInput) {
                    transportInput.value = transportMode;
                    console.log("Set transport mode to:", transportMode);
                    
                    // Special handling for work from home
                    if (transportMode === 'work_from_home') {
                        const mapSection = document.getElementById('map-section');
                        if (mapSection) mapSection.style.display = 'none';
                        
                        const distanceInput = document.getElementById('distance-km');
                        if (distanceInput) distanceInput.value = '0';
                        
                        updateTripPreview(0, 0);
                    } else {
                        const mapSection = document.getElementById('map-section');
                        if (mapSection) mapSection.style.display = 'block';
                        
                        calculateRouteIfPossible();
                    }
                }
            }
        });
    }
    
    // Set up location change handlers
    const startLocationSelect = document.getElementById('start-location');
    const endLocationSelect = document.getElementById('end-location');
    
    if (startLocationSelect) {
        startLocationSelect.addEventListener('change', function() {
            handleLocationSelection(this.value, 'start');
        });
        
        // Default to home for start location
        if (document.querySelector('#start-location option[value="home"]')) {
            startLocationSelect.value = 'home';
            // Trigger change event after map is loaded
        }
    }
    
    if (endLocationSelect) {
        endLocationSelect.addEventListener('change', function() {
            handleLocationSelection(this.value, 'end');
        });
        
        // Look for the first employer location (likely FAU)
        const firstEmployerOption = document.querySelector('#end-location option:not([value="home"]):not([value="other"]):not([value=""])');
        if (firstEmployerOption) {
            endLocationSelect.value = firstEmployerOption.value;
            // Will be triggered after map load
        }
    }
});

// Set up transport option clicks
function setupTransportOptions() {
    console.log("Setting up transport options");
    const transportOptions = document.querySelectorAll('.transport-option');
    
    if (transportOptions.length === 0) {
        console.warn("No transport options found");
        return;
    }
    
    console.log(`Found ${transportOptions.length} transport options`);
    
    transportOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Transport option clicked:", this.getAttribute('data-mode'));
            
            // Remove selected class from all options
            transportOptions.forEach(opt => {
                opt.classList.remove('selected');
            });
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update hidden input with selected transport mode
            const transportMode = this.getAttribute('data-mode');
            const transportModeInput = document.getElementById('transport-mode');
            
            if (!transportModeInput) {
                console.error("Transport mode input not found");
                return;
            }
            
            transportModeInput.value = transportMode;
            console.log("Selected transport mode:", transportMode);
            
            // Special handling for work from home
            const mapSection = document.getElementById('map-section');
            const distanceInput = document.getElementById('distance-km');
            
            if (transportMode === 'work_from_home') {
                if (mapSection) mapSection.style.display = 'none';
                if (distanceInput) distanceInput.value = '0';
                updateTripPreview(0, 0);
            } else {
                if (mapSection) mapSection.style.display = 'block';
                calculateRouteIfPossible();
            }
        });
    });
}

// Add a temporary notification
function addNotification(message, type = 'info') {
    const container = document.createElement('div');
    container.className = `p-4 rounded-lg mb-4 ${
        type === 'success' ? 'bg-green-100 text-green-800' : 
        type === 'error' ? 'bg-red-100 text-red-800' : 
        type === 'warning' ? 'bg-yellow-100 text-yellow-800' :
        'bg-blue-100 text-blue-800'
    }`;
    container.textContent = message;
    
    // Find the messages section or create one
    let messagesSection = document.querySelector('.messages-section');
    if (!messagesSection) {
        messagesSection = document.createElement('div');
        messagesSection.className = 'messages-section mb-6';
        
        // Insert after the header section
        const header = document.querySelector('.relative.mb-8');
        header.parentNode.insertBefore(messagesSection, header.nextSibling);
    }
    
    // Add the notification
    messagesSection.appendChild(container);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        container.style.opacity = '0';
        container.style.transition = 'opacity 0.5s ease';
        
        setTimeout(() => {
            if (container.parentNode) {
                container.parentNode.removeChild(container);
            }
        }, 500);
    }, 5000);
}

// Initialize Google Maps when API is loaded
function initMap() {
    console.log("initMap called - Google Maps API callback triggered");
    
    // Wait a moment to ensure DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initializeMap();
        });
    } else {
        // Small delay to ensure everything is ready
        setTimeout(initializeMap, 100);
    }
}

function initializeMap() {
    console.log("initializeMap() called");
    console.log("Document ready state:", document.readyState);
    console.log("Map element exists:", !!document.getElementById('trip-map'));
    
    // Declare settingLocationType at function scope level
    let settingLocationType = null;
    
    try {
        // Check if Google Maps is available
        if (typeof google === 'undefined') {
            throw new Error('Google Maps API not loaded - google object is undefined. Check API key and ensure Maps JavaScript API is enabled.');
        }
        
        if (typeof google.maps === 'undefined') {
            throw new Error('Google Maps API not loaded - google.maps object is undefined. Check if libraries are loading correctly.');
        }
        
        console.log("Google Maps API is available");
        console.log("Google Maps version:", google.maps.version || 'unknown');
        
        // Hide all map loading indicators
        document.querySelectorAll('.map-loading').forEach(loading => {
            loading.style.display = 'none';
        });
        
        // Create map
        const mapElement = document.getElementById('trip-map');
        if (!mapElement) {
            console.error("Map element not found");
            // Try again after a short delay
            setTimeout(function() {
                const retryElement = document.getElementById('trip-map');
                if (retryElement) {
                    initializeMap();
                } else {
                    console.error("Map element still not found after retry");
                }
            }, 500);
            return;
        }
    
        // Thane, Maharashtra, India coordinates (default location)
        var thaneLocation = { lat: 19.2183, lng: 72.9781 }; // Thane, Maharashtra, India
        
        // Create map first
        map = new google.maps.Map(mapElement, {
            zoom: 13,
            center: thaneLocation, // Center on Thane, India (fallback)
            mapTypeControl: true,
            streetViewControl: false,
            fullscreenControl: true,
            zoomControl: true
        });
        
        console.log("Map created successfully");
        
        // Try to get user's current location using GPS after map is created
        if (navigator.geolocation) {
            console.log("Requesting GPS location access...");
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    console.log("GPS location obtained:", userLocation);
                    map.setCenter(userLocation);
                    map.setZoom(15);
                    
                    // Optionally set start marker to user location if it exists
                    if (typeof startMarker !== 'undefined' && startMarker) {
                        startMarker.setPosition(userLocation);
                        if (!startMarker.getMap()) {
                            startMarker.setMap(map);
                        }
                    }
                },
                function(error) {
                    console.log("GPS access denied or error:", error.message);
                    // Keep default Thane location - already set
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            console.log("Geolocation not supported by browser");
        }
    
    // Create markers for start and end locations
    startMarker = new google.maps.Marker({
        position: thaneLocation,
        map: map,
        draggable: true,
        icon: {
            url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
            scaledSize: new google.maps.Size(40, 40)
        },
        animation: google.maps.Animation.DROP,
        title: 'Start Location'
    });
    
    // Default end location (Thane - different area)
    var defaultEndLocation = { lat: 19.2300, lng: 72.9900 }; // Thane, India (different area)
    
    endMarker = new google.maps.Marker({
        map: map,
        position: defaultEndLocation,
        draggable: true,
        icon: {
            url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
            scaledSize: new google.maps.Size(40, 40)
        },
        animation: google.maps.Animation.DROP,
        title: 'End Location'
    });
    
    // Hide markers initially
    startMarker.setMap(null);
    endMarker.setMap(null);
    
    // Create directions service and renderer
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
        map: map,
        suppressMarkers: true,
        polylineOptions: {
            strokeColor: '#10B981',
            strokeWeight: 5,
            strokeOpacity: 0.7
        }
    });
    
    // Set up search box with autocomplete for better UX
    const searchInput = document.getElementById('map-search-input');
    if (searchInput) {
        // Use Autocomplete instead of SearchBox for better functionality
        let autocomplete;
        try {
            autocomplete = new google.maps.places.Autocomplete(searchInput, {
                types: ['geocode', 'establishment'],
                componentRestrictions: { country: 'in' } // Restrict to India
            });
        } catch (e) {
            console.warn('Autocomplete not available, using SearchBox:', e);
            // Fallback to SearchBox
            autocomplete = new google.maps.places.SearchBox(searchInput);
        }
        
        // Bias search results to current map view
        map.addListener('bounds_changed', function() {
            if (autocomplete.setBounds) {
                autocomplete.setBounds(map.getBounds());
            }
        });
        
        // Update when dropdown changes
        const startSelect = document.getElementById('start-location');
        const endSelect = document.getElementById('end-location');
        
        if (startSelect) {
            startSelect.addEventListener('focus', function() {
                settingLocationType = 'start';
                searchInput.placeholder = 'Search for start location...';
            });
        }
        
        if (endSelect) {
            endSelect.addEventListener('focus', function() {
                settingLocationType = 'end';
                searchInput.placeholder = 'Search for end location...';
            });
        }
        
        // Handle search results
        const handlePlaceSelect = function() {
            let place;
            
            if (autocomplete.getPlace) {
                // Autocomplete
                place = autocomplete.getPlace();
            } else {
                // SearchBox fallback
                const places = autocomplete.getPlaces();
                if (places.length === 0) return;
                place = places[0];
            }
            
            if (!place || !place.geometry || !place.geometry.location) {
                console.warn('Place has no geometry');
                return;
            }
            
            // Get location coordinates
            const location = {
                lat: place.geometry.location.lat(),
                lng: place.geometry.location.lng(),
                address: place.formatted_address || place.name
            };
            
            console.log('Place selected:', location);
            
            // Determine which location to set
            const currentSettingType = settingLocationType || window.settingLocationType;
            const locationType = currentSettingType || 
                                (document.activeElement && document.activeElement.id === 'start-location' ? 'start' : 
                                 document.activeElement && document.activeElement.id === 'end-location' ? 'end' : null);
            
            if (locationType === 'start') {
                // Set start location
                startMarker.setPosition(location);
                startMarker.setMap(map);
                if (startSelect) {
                    startSelect.value = 'other';
                    // Create option if it doesn't exist
                    if (!startSelect.querySelector('option[value="other"]')) {
                        const option = document.createElement('option');
                        option.value = 'other';
                        option.textContent = location.address.substring(0, 50);
                        startSelect.appendChild(option);
                    }
                }
                
                // Update hidden fields
                const customLat = document.getElementById('custom-lat');
                const customLng = document.getElementById('custom-lng');
                const customAddress = document.getElementById('custom-address');
                if (customLat) customLat.value = location.lat;
                if (customLng) customLng.value = location.lng;
                if (customAddress) customAddress.value = location.address;
                
                // Show marker
                map.setCenter(location);
                map.setZoom(15);
            } else if (locationType === 'end') {
                // Set end location
                endMarker.setPosition(location);
                endMarker.setMap(map);
                if (endSelect) {
                    endSelect.value = 'other';
                    // Create option if it doesn't exist
                    if (!endSelect.querySelector('option[value="other"]')) {
                        const option = document.createElement('option');
                        option.value = 'other';
                        option.textContent = location.address.substring(0, 50);
                        endSelect.appendChild(option);
                    }
                }
                
                // Update hidden fields
                const customLat = document.getElementById('custom-lat');
                const customLng = document.getElementById('custom-lng');
                const customAddress = document.getElementById('custom-address');
                if (customLat) customLat.value = location.lat;
                if (customLng) customLng.value = location.lng;
                if (customAddress) customAddress.value = location.address;
                
                // Show marker
                map.setCenter(location);
                map.setZoom(15);
            } else {
                // Default: center map on location
                map.setCenter(location);
                map.setZoom(15);
            }
            
            // Clear search input
            searchInput.value = '';
            
            // Try to calculate route if both locations are set
            setTimeout(calculateRouteIfPossible, 500);
        };
        
        // Attach event listener based on type
        if (autocomplete.addListener) {
            // Autocomplete
            autocomplete.addListener('place_changed', handlePlaceSelect);
        } else if (autocomplete.getPlaces) {
            // SearchBox
            autocomplete.addListener('places_changed', handlePlaceSelect);
        }
        
        // Also handle Enter key
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handlePlaceSelect();
            }
        });
    }
    
    // Set up location selectors with search integration
    const startSelect = document.getElementById('start-location');
    const endSelect = document.getElementById('end-location');
    
    if (startSelect) {
        startSelect.addEventListener('change', function() {
            if (this.value === 'other') {
                // Focus search box when "Other" is selected
                if (searchInput) {
                    searchInput.focus();
                    searchInput.placeholder = 'Search for start location...';
                    settingLocationType = 'start';
                    if (window.updateSettingLocationType) {
                        window.updateSettingLocationType('start');
                    }
                }
            } else {
                handleLocationSelection(this.value, 'start');
            }
        });
        
        startSelect.addEventListener('focus', function() {
            settingLocationType = 'start';
            if (window.updateSettingLocationType) {
                window.updateSettingLocationType('start');
            }
            if (searchInput) {
                searchInput.placeholder = 'Search for start location...';
            }
        });
        
        // Trigger change for initial selection
        if (startSelect.value) {
            handleLocationSelection(startSelect.value, 'start');
        }
    }
    
    if (endSelect) {
        endSelect.addEventListener('change', function() {
            if (this.value === 'other') {
                // Focus search box when "Other" is selected
                if (searchInput) {
                    searchInput.focus();
                    searchInput.placeholder = 'Search for end location...';
                    settingLocationType = 'end';
                    if (window.updateSettingLocationType) {
                        window.updateSettingLocationType('end');
                    }
                }
            } else {
                handleLocationSelection(this.value, 'end');
            }
        });
        
        endSelect.addEventListener('focus', function() {
            settingLocationType = 'end';
            if (window.updateSettingLocationType) {
                window.updateSettingLocationType('end');
            }
            if (searchInput) {
                searchInput.placeholder = 'Search for end location...';
            }
        });
        
        // Trigger change for initial selection
        if (endSelect.value) {
            handleLocationSelection(endSelect.value, 'end');
        }
    }
    
        // Make settingLocationType available globally for search handler
        // Update it when dropdowns change
        const updateSettingLocationType = function(type) {
            settingLocationType = type;
            window.settingLocationType = type;
        };
        
        // Expose update function
        window.updateSettingLocationType = updateSettingLocationType;
    
    } catch (error) {
        console.error('Error initializing map:', error);
        console.error('Error details:', error.message, error.stack);
        
        // Show detailed error message
        const errorMessage = error.message || 'Unknown error occurred';
        document.querySelectorAll('.map-loading').forEach(loading => {
            loading.innerHTML = `
                <div class="p-4 bg-red-100 text-red-800 rounded">
                    <strong>Error loading map:</strong><br>
                    ${errorMessage}<br>
                    <small>Please check the browser console for more details.</small>
                </div>
            `;
            loading.style.display = 'flex';
        });
    }
}

// Handle location selection for start or end points
function handleLocationSelection(locationValue, locationType) {
    console.log(`Handling ${locationType} location selection: ${locationValue}`);
    
    // Define default locations (Thane, India)
    var thaneLocation = { lat: 19.2183, lng: 72.9781 }; // Thane, Maharashtra, India
    var thaneEastLocation = { lat: 19.2300, lng: 72.9900 }; // Thane East, India
    
    // Get the appropriate marker based on location type
    let marker = locationType === 'start' ? startMarker : endMarker;
    
    // Show marker by default
    marker.setMap(map);
    
    // Handle different location types
    if (locationValue === 'home') {
        // Use home location (Thane)
        marker.setPosition(thaneLocation);
        marker.setDraggable(false);
        
        // Store location in data attribute for later retrieval
        if (locationType === 'start') {
            document.getElementById('start-location').setAttribute('data-location', JSON.stringify(thaneLocation));
        } else {
            document.getElementById('end-location').setAttribute('data-location', JSON.stringify(thaneLocation));
        }
    } else if (locationValue === 'other') {
        // Custom location - allow dragging
        marker.setDraggable(true);
        
        // Position the marker in the center of the current map view if not already placed
        const currentPosition = marker.getPosition();
        if (!currentPosition) {
            marker.setPosition(map.getCenter());
        }
        
        // Focus on the search input to encourage user to search
        document.getElementById('map-search-input').focus();
    } else {
        // Check if this is a location ID (from employer locations)
        if (!isNaN(parseInt(locationValue))) {
            // Try to get lat/lng from the option
            const select = document.getElementById(`${locationType}-location`);
            const option = select.querySelector(`option[value="${locationValue}"]`);
            
            if (option) {
                const lat = parseFloat(option.getAttribute('data-lat'));
                const lng = parseFloat(option.getAttribute('data-lng'));
                
                if (!isNaN(lat) && !isNaN(lng)) {
                    const position = { lat, lng };
                    marker.setPosition(position);
                    marker.setDraggable(false);
                    
                    // Store location
                    if (locationType === 'start') {
                        document.getElementById('start-location').setAttribute('data-location', JSON.stringify(position));
                    } else {
                        document.getElementById('end-location').setAttribute('data-location', JSON.stringify(position));
                    }
                } else {
                    // Fallback to Thane if for some reason coordinates aren't available
                    marker.setPosition(thaneEastLocation);
                    marker.setDraggable(false);
                }
            } else {
                // Fallback to Thane if option not found
                marker.setPosition(thaneEastLocation);
                marker.setDraggable(false);
            }
        }
    }
    
    // Calculate route if both locations are set
    calculateRouteIfPossible();
}

// Calculate route if possible
function calculateRouteIfPossible() {
    // Check if both locations are selected and visible
    if (startMarker && endMarker) {
        // Ensure markers are visible
        startMarker.setMap(map);
        endMarker.setMap(map);
        
        // Get marker positions
        const start = startMarker.getPosition();
        const end = endMarker.getPosition();
        
        // Make sure both positions exist
        if (start && end) {
            // Initialize directions service if needed
            if (!directionsService) {
                directionsService = new google.maps.DirectionsService();
                directionsRenderer = new google.maps.DirectionsRenderer({
                    map: map,
                    suppressMarkers: true,
                    polylineOptions: {
                        strokeColor: '#2B9348',
                        strokeWeight: 5
                    }
                });
            }
            
            // Calculate and display route
            directionsService.route({
                origin: start,
                destination: end,
                travelMode: getTravelMode()
            }, function(response, status) {
                if (status === 'OK') {
                    directionsRenderer.setDirections(response);
                    
                    // Get distance and duration
                    const route = response.routes[0];
                    if (route && route.legs && route.legs.length > 0) {
                        const leg = route.legs[0];
                        const distance = leg.distance.value / 1000; // Convert to km
                        const duration = leg.duration.value / 60; // Convert to minutes
                        
                        // Update form field with distance
                        const distanceInput = document.getElementById('distance-km');
                        if (distanceInput) {
                            distanceInput.value = distance.toFixed(2);
                        }
                        
                        // Update distance display
                        const distanceDisplay = document.getElementById('distance-display');
                        const distanceValue = document.getElementById('distance-value');
                        if (distanceDisplay && distanceValue) {
                            distanceValue.textContent = distance.toFixed(2) + ' km';
                            distanceDisplay.classList.remove('hidden');
                        }
                        
                        // Update preview
                        updateTripPreview(distance, duration);
                        
                        // Show preview section
                        const previewSection = document.getElementById('trip-preview');
                        if (previewSection) {
                            previewSection.classList.remove('hidden');
                        }
                        
                        // Update credit preview if calculation engine is loaded
                        if (typeof updateCreditPreview === 'function') {
                            updateCreditPreview();
                        }
                        
                        // Auto-trigger environment data detection if both locations are set
                        if (typeof autoDetectEnvironmentData === 'function') {
                            autoDetectEnvironmentData(true); // true = silent mode (no user notification)
                        }
                    }
                } else if (status === 'REQUEST_DENIED') {
                    console.warn('Directions API request denied. This usually means:');
                    console.warn('1. Directions API is not enabled in Google Cloud Console');
                    console.warn('2. Billing is not enabled for your project');
                    console.warn('3. API key restrictions are blocking the request');
                    
                    // Calculate distance using Haversine formula as fallback
                    const distance = calculateHaversineDistance(
                        start.lat(), start.lng(),
                        end.lat(), end.lng()
                    );
                    
                    // Update form field with distance
                    const distanceInput = document.getElementById('distance-km');
                    if (distanceInput) {
                        distanceInput.value = distance.toFixed(2);
                    }
                    
                    // Update distance display
                    const distanceDisplay = document.getElementById('distance-display');
                    const distanceValue = document.getElementById('distance-value');
                    if (distanceDisplay && distanceValue) {
                        distanceValue.textContent = distance.toFixed(2) + ' km (straight line)';
                        distanceDisplay.classList.remove('hidden');
                    }
                    
                    // Draw a simple line between points
                    const line = new google.maps.Polyline({
                        path: [start, end],
                        geodesic: true,
                        strokeColor: '#10B981',
                        strokeOpacity: 0.7,
                        strokeWeight: 3,
                        map: map
                    });
                    
                    // Update preview with estimated values
                    const estimatedDuration = (distance / 30) * 60; // Assume 30 km/h average
                    updateTripPreview(distance, estimatedDuration);
                    
                    addNotification('Route calculation unavailable. Using straight-line distance. Enable Directions API and billing for full route calculation.', 'info');
                } else {
                    console.error('Directions request failed:', status);
                    addNotification('Could not calculate route. Please try different locations.', 'error');
                }
            });
        } else {
            console.warn('Missing start or end position');
        }
    } else {
        console.warn('Missing markers');
    }
}

// Auto-detect environment data from API
async function autoDetectEnvironmentData(silent = false) {
    // Check if both locations are selected
    const startSelect = document.getElementById('start-location');
    const endSelect = document.getElementById('end-location');
    
    if (!startSelect || !endSelect || !startSelect.value || !endSelect.value) {
        if (!silent) {
            addNotification('Please select both start and end locations first.', 'warning');
        }
        return;
    }
    
    // Get coordinates from markers
    if (!startMarker || !endMarker) {
        if (!silent) {
            addNotification('Please wait for map to load completely.', 'warning');
        }
        return;
    }
    
    const startPos = startMarker.getPosition();
    const endPos = endMarker.getPosition();
    
    if (!startPos || !endPos) {
        if (!silent) {
            addNotification('Please select locations on the map first.', 'warning');
        }
        return;
    }
    
    // Get trip date
    const tripDateInput = document.getElementById('trip-date');
    const tripDate = tripDateInput ? tripDateInput.value : new Date().toISOString().split('T')[0];
    const tripTime = tripDate + 'T12:00:00'; // Default to noon
    
    // Show loading state
    const autoDetectBtn = document.getElementById('auto-detect-btn');
    const statusDiv = document.getElementById('auto-detect-status');
    
    if (autoDetectBtn) {
        autoDetectBtn.disabled = true;
        autoDetectBtn.innerHTML = '<svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Detecting...';
    }
    
    if (statusDiv && !silent) {
        statusDiv.classList.remove('hidden');
        statusDiv.innerHTML = '<div class="p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">🔄 Detecting environmental data...</div>';
    }
    
    try {
        // Call the API endpoint
        const response = await fetch('/api/environment-data/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                start_lat: startPos.lat(),
                start_lng: startPos.lng(),
                end_lat: endPos.lat(),
                end_lng: endPos.lng(),
                trip_time: tripTime
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update form fields with detected values
        if (data.time_period) {
            const timePeriodSelect = document.getElementById('time_period');
            if (timePeriodSelect) {
                timePeriodSelect.value = data.time_period;
            }
        }
        
        if (data.traffic_condition) {
            const trafficSelect = document.getElementById('traffic_condition');
            if (trafficSelect) {
                trafficSelect.value = data.traffic_condition;
            }
        }
        
        if (data.weather_condition) {
            const weatherSelect = document.getElementById('weather_condition');
            if (weatherSelect) {
                weatherSelect.value = data.weather_condition;
            }
        }
        
        if (data.route_type) {
            const routeSelect = document.getElementById('route_type');
            if (routeSelect) {
                routeSelect.value = data.route_type;
            }
        }
        
        if (data.aqi_level) {
            const aqiSelect = document.getElementById('aqi_level');
            if (aqiSelect) {
                aqiSelect.value = data.aqi_level;
            }
        }
        
        if (data.season) {
            const seasonSelect = document.getElementById('season');
            if (seasonSelect) {
                seasonSelect.value = data.season;
            }
        }
        
        // Update credit preview
        if (typeof updateCreditPreview === 'function') {
            updateCreditPreview();
        }
        
        // Show success message
        if (statusDiv && !silent) {
            statusDiv.innerHTML = '<div class="p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">✅ Environment data detected and updated!</div>';
            setTimeout(() => {
                statusDiv.classList.add('hidden');
            }, 3000);
        }
        
        if (autoDetectBtn) {
            autoDetectBtn.disabled = false;
            autoDetectBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg><span>Auto-Detect All</span>';
        }
        
    } catch (error) {
        console.error('Error detecting environment data:', error);
        
        if (statusDiv && !silent) {
            statusDiv.innerHTML = '<div class="p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">⚠️ Could not auto-detect. Please set values manually.</div>';
        }
        
        if (autoDetectBtn) {
            autoDetectBtn.disabled = false;
            autoDetectBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg><span>Auto-Detect All</span>';
        }
    }
}

// Helper function to get CSRF token from cookies
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

// Update trip preview with calculated values
function updateTripPreview(distance, duration) {
    const previewSection = document.getElementById('trip-preview');
    if (!previewSection) return;
    
    // Show preview section
    previewSection.classList.remove('hidden');
    
    // Get selected transport mode
    const transportMode = document.getElementById('transport-mode').value;
    
    // Set mode name and credit rate (fallback only)
    let modeName = 'Unknown';
    let creditsPerKm = 0.5;
    
    switch (transportMode) {
        case 'walking':
            modeName = 'Walking';
            creditsPerKm = 6;
            break;
        case 'bicycle':
            modeName = 'Bicycle';
            creditsPerKm = 5;
            break;
        case 'public_transport':
            modeName = 'Public Transport';
            creditsPerKm = 3;
            break;
        case 'two_wheeler_single':
            modeName = 'Two Wheeler (Solo)';
            creditsPerKm = 2.5;
            break;
        case 'two_wheeler_double':
            modeName = 'Two Wheeler (Carpool)';
            creditsPerKm = 3.2;
            break;
        case 'carpool':
            modeName = 'Carpool';
            creditsPerKm = 2;
            break;
        case 'car':
            modeName = 'Car (Single)';
            creditsPerKm = 0.5;
            break;
        case 'work_from_home':
            modeName = 'Work from Home';
            creditsPerKm = 0;
            break;
    }
    
    // Calculate credits
    let totalCredits = 0;
    if (transportMode === 'work_from_home') {
        totalCredits = 10; // Fixed amount for WFH
    } else if (typeof calculateCredits === 'function') {
        const timePeriod = document.getElementById('time_period')?.value || 'off_peak';
        const trafficCondition = document.getElementById('traffic_condition')?.value || 'moderate';
        const weather = document.getElementById('weather_condition')?.value || 'normal';
        const routeType = document.getElementById('route_type')?.value || 'suburban';
        const aqiLevel = document.getElementById('aqi_level')?.value || 'moderate';
        const season = document.getElementById('season')?.value || 'normal';
        totalCredits = calculateCredits(
            transportMode,
            distance,
            timePeriod,
            trafficCondition,
            weather,
            routeType,
            aqiLevel,
            season
        );
    } else {
        totalCredits = Math.round(distance * creditsPerKm * 10) / 10;
    }
    
    // Update preview elements
    document.getElementById('trip-preview-transport').textContent = modeName;
    document.getElementById('trip-preview-distance').textContent = distance.toFixed(2) + ' km';
    document.getElementById('trip-preview-duration').textContent = Math.round(duration) + ' min';
    document.getElementById('trip-preview-credits').textContent = totalCredits.toFixed(2) + ' credits';
}

// Get the Google Maps travel mode based on selected transport mode
function getTravelMode() {
    const transportMode = document.getElementById('transport-mode').value;
    
    // Map our transport modes to Google Maps travel modes
    switch(transportMode) {
        case 'walking':
            return google.maps.TravelMode.WALKING;
        case 'bicycle':
            return google.maps.TravelMode.BICYCLING;
        case 'public_transport':
            return google.maps.TravelMode.TRANSIT;
        case 'two_wheeler_single':
        case 'two_wheeler_double':
        case 'carpool':
        case 'car':
        default:
            return google.maps.TravelMode.DRIVING;
    }
}

// Helper function to calculate distance using Haversine formula
function calculateHaversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Radius of the Earth in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

// Make sure initMap is available globally for Google Maps API callback
// This must be set before Google Maps API script loads
if (typeof window.initMap === 'undefined' || window.initMap.toString().includes('Waiting for')) {
    window.initMap = initMap;
} else {
    // If already defined, replace it with our implementation
    window.initMap = initMap;
}

// Make autoDetectEnvironmentData globally available
window.autoDetectEnvironmentData = autoDetectEnvironmentData;

// Also export for direct access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initMap, calculateHaversineDistance, autoDetectEnvironmentData };
}