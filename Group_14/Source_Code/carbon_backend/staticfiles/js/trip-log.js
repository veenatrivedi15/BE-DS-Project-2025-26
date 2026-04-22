// Google Maps and trip logging functionality
let map, userMarker, destinationMarker, directionsService, directionsRenderer;
let homeLocation = null;
let officeLocation = null;
let selectedMode = null;
let calculatedDistance = 0;

// Initialize map when the page loads
function initMap() {
    console.log("Initializing map...");
    
    // Create map instance
    map = new google.maps.Map(document.getElementById('trip-map'), {
        zoom: 12,
        center: { lat: 19.0760, lng: 72.8777 }, // Default location (Mumbai)
        mapTypeControl: true,
        streetViewControl: false,
        fullscreenControl: true
    });
    
    // Create directions service and renderer
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
        map: map,
        suppressMarkers: true,
        polylineOptions: {
            strokeColor: '#10B981', // Green color for the route
            strokeWeight: 5,
            strokeOpacity: 0.7
        }
    });
    
    // Initialize location markers
    userMarker = new google.maps.Marker({
        map: map,
        icon: {
            url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
            scaledSize: new google.maps.Size(40, 40)
        },
        animation: google.maps.Animation.DROP,
        title: 'Your Location'
    });
    
    destinationMarker = new google.maps.Marker({
        map: map,
        icon: {
            url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
            scaledSize: new google.maps.Size(40, 40)
        },
        animation: google.maps.Animation.DROP,
        title: 'Destination'
    });
    
    // Hide markers initially
    userMarker.setMap(null);
    destinationMarker.setMap(null);
    
    // Get user's current location
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                // Set user marker
                userMarker.setPosition(userLocation);
                userMarker.setMap(map);
                
                // Center map on user location
                map.setCenter(userLocation);
                
                // Store home location
                homeLocation = userLocation;
                
                // Update hidden fields
                document.getElementById('home-lat').value = userLocation.lat;
                document.getElementById('home-lng').value = userLocation.lng;
                
                // Attempt to get address via reverse geocoding
                reverseGeocode(userLocation);
            },
            (error) => {
                console.error("Geolocation error:", error);
                alert("Error getting your location. Please enable location services.");
            }
        );
    } else {
        alert("Geolocation is not supported by your browser.");
    }
    
    // Set up map search box
    const searchInput = document.getElementById('map-search-input');
    const searchBox = new google.maps.places.SearchBox(searchInput);
    
    // Bias search results to current map view
    map.addListener('bounds_changed', () => {
        searchBox.setBounds(map.getBounds());
    });
    
    // Handle search box selection
    searchBox.addListener('places_changed', () => {
        const places = searchBox.getPlaces();
        if (places.length === 0) return;
        
        const place = places[0];
        if (!place.geometry || !place.geometry.location) return;
        
        // Set destination marker
        const destinationLocation = {
            lat: place.geometry.location.lat(),
            lng: place.geometry.location.lng()
        };
        
        destinationMarker.setPosition(destinationLocation);
        destinationMarker.setMap(map);
        
        // Store office location
        officeLocation = destinationLocation;
        
        // Update hidden fields
        document.getElementById('office-lat').value = destinationLocation.lat;
        document.getElementById('office-lng').value = destinationLocation.lng;
        document.getElementById('office-address').value = place.formatted_address || place.name;
        
        // Calculate route
        if (homeLocation) {
            calculateRoute();
        }
    });
    
    // Handle clicks on the map
    map.addListener('click', (event) => {
        if (!officeLocation) {
            // Set destination marker if not already set
            const clickedLocation = {
                lat: event.latLng.lat(),
                lng: event.latLng.lng()
            };
            
            destinationMarker.setPosition(clickedLocation);
            destinationMarker.setMap(map);
            
            // Store office location
            officeLocation = clickedLocation;
            
            // Update hidden fields
            document.getElementById('office-lat').value = clickedLocation.lat;
            document.getElementById('office-lng').value = clickedLocation.lng;
            
            // Get address via reverse geocoding
            reverseGeocode(clickedLocation, (address) => {
                document.getElementById('office-address').value = address;
            });
            
            // Calculate route
            if (homeLocation) {
                calculateRoute();
            }
        }
    });
    
    // Initialize start/end location dropdowns
    initializeLocationSelectors();
}

// Handle transport mode selection
function selectMode(element) {
    console.log("Transport mode selected:", element.dataset.mode);
    
    // Remove selected from all
    document.querySelectorAll('.transport-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Add selected to clicked one
    element.classList.add('selected');
    
    // Store selected mode
    selectedMode = element.dataset.mode;
    
    // Update hidden input
    document.getElementById('transport-mode').value = selectedMode;
    
    // Special handling for work from home
    if (selectedMode === 'work_from_home') {
        document.getElementById('map-section').style.display = 'none';
        document.getElementById('distance-km').value = '0';
        
        // Show trip summary
        updateTripPreview(0);
    } else {
        document.getElementById('map-section').style.display = 'block';
        
        // Recalculate route with new transport mode
        if (homeLocation && officeLocation) {
            calculateRoute();
        }
    }
}

// Calculate route between home and office
function calculateRoute() {
    if (!homeLocation || !officeLocation || !selectedMode) {
        console.log("Cannot calculate route: missing location or transport mode");
        return;
    }
    
    // Map transport mode to Google Maps travel mode
    let travelMode;
    switch (selectedMode) {
        case 'walking':
            travelMode = google.maps.TravelMode.WALKING;
            break;
        case 'bicycle':
            travelMode = google.maps.TravelMode.BICYCLING;
            break;
        case 'public_transport':
            travelMode = google.maps.TravelMode.TRANSIT;
            break;
        case 'car':
        case 'carpool':
        default:
            travelMode = google.maps.TravelMode.DRIVING;
            break;
    }
    
    // Create route request
    const request = {
        origin: homeLocation,
        destination: officeLocation,
        travelMode: travelMode
    };
    
    // Get route
    directionsService.route(request, (result, status) => {
        if (status === google.maps.DirectionsStatus.OK) {
            // Display route
            directionsRenderer.setDirections(result);
            
            // Get distance and duration
            const route = result.routes[0];
            let distance = 0;
            let duration = 0;
            
            route.legs.forEach(leg => {
                distance += leg.distance.value;
                duration += leg.duration.value;
            });
            
            // Convert to km and minutes
            distance = (distance / 1000).toFixed(2);
            duration = Math.ceil(duration / 60);
            
            // Store calculated distance
            calculatedDistance = distance;
            
            // Update hidden field
            document.getElementById('distance-km').value = distance;
            
            // Update trip preview
            updateTripPreview(distance, duration);
        } else {
            console.error("Directions request failed:", status);
            alert("Could not calculate route. Please try again.");
        }
    });
}

// Update trip preview with calculated data
function updateTripPreview(distance, duration) {
    const preview = document.getElementById('trip-preview');
    if (!preview) return;
    
    preview.classList.remove('hidden');
    
    // Calculate credits based on transport mode and distance
    let credits = 0;
    if (selectedMode === 'work_from_home') {
        credits = 10; // Fixed credits for working from home
    } else {
        const creditRates = {
            'car': 0.5,
            'carpool': 2,
            'public_transport': 3,
            'bicycle': 5,
            'walking': 6
        };
        
        credits = distance * (creditRates[selectedMode] || 1);
    }
    
    // Format credits to 2 decimal places
    credits = credits.toFixed(2);
    
    // Update preview content
    const distanceText = document.getElementById('preview-distance');
    const durationText = document.getElementById('preview-duration');
    const creditsText = document.getElementById('preview-credits');
    const transportText = document.getElementById('preview-transport');
    
    if (distanceText) distanceText.textContent = `${distance} km`;
    if (durationText && duration) durationText.textContent = `${duration} min`;
    if (creditsText) creditsText.textContent = `${credits} credits`;
    
    if (transportText) {
        const modeNames = {
            'car': 'Car (Single)',
            'carpool': 'Carpool',
            'public_transport': 'Public Transport',
            'bicycle': 'Bicycle',
            'walking': 'Walking',
            'work_from_home': 'Work from Home'
        };
        
        transportText.textContent = modeNames[selectedMode] || selectedMode;
    }
}

// Initialize location selectors
function initializeLocationSelectors() {
    const startLocationSelect = document.getElementById('start-location');
    const endLocationSelect = document.getElementById('end-location');
    
    if (startLocationSelect && endLocationSelect) {
        // Handle location selection changes
        startLocationSelect.addEventListener('change', () => {
            if (startLocationSelect.value === 'home') {
                // Set start location to home
                if (homeLocation) {
                    userMarker.setPosition(homeLocation);
                    userMarker.setMap(map);
                    
                    // Calculate route if both locations are set
                    if (officeLocation && selectedMode) {
                        calculateRoute();
                    }
                }
            } else if (startLocationSelect.value === 'office') {
                // Set start location to office
                if (officeLocation) {
                    userMarker.setPosition(officeLocation);
                    userMarker.setMap(map);
                    
                    // Calculate route if both locations are set
                    if (homeLocation && selectedMode) {
                        calculateRoute();
                    }
                }
            } else if (startLocationSelect.value === 'other') {
                // Show map for custom location selection
                document.getElementById('map-section').style.display = 'block';
            }
        });
        
        endLocationSelect.addEventListener('change', () => {
            if (endLocationSelect.value === 'home') {
                // Set end location to home
                if (homeLocation) {
                    destinationMarker.setPosition(homeLocation);
                    destinationMarker.setMap(map);
                    
                    // Calculate route if both locations are set
                    if (officeLocation && selectedMode) {
                        calculateRoute();
                    }
                }
            } else if (endLocationSelect.value === 'office') {
                // Set end location to office
                if (officeLocation) {
                    destinationMarker.setPosition(officeLocation);
                    destinationMarker.setMap(map);
                    
                    // Calculate route if both locations are set
                    if (homeLocation && selectedMode) {
                        calculateRoute();
                    }
                }
            } else if (endLocationSelect.value === 'other') {
                // Show map for custom location selection
                document.getElementById('map-section').style.display = 'block';
            }
        });
    }
}

// Reverse geocode to get address from coordinates
function reverseGeocode(location, callback) {
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ 'location': location }, (results, status) => {
        if (status === 'OK') {
            if (results[0]) {
                const address = results[0].formatted_address;
                if (callback) {
                    callback(address);
                } else {
                    // Assume it's home address
                    document.getElementById('home-address').value = address;
                }
            }
        } else {
            console.error("Geocoder failed due to: " + status);
        }
    });
}

// Handle file upload preview
function handleFileSelect(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('file-preview');
            const previewContainer = document.getElementById('file-preview-container');
            const uploadContainer = document.getElementById('file-upload-container');
            
            if (preview && previewContainer && uploadContainer) {
                preview.src = e.target.result;
                previewContainer.style.display = 'block';
                uploadContainer.style.display = 'none';
            }
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// Remove uploaded file
function removeFile() {
    const fileInput = document.getElementById('proof-upload');
    const preview = document.getElementById('file-preview');
    const previewContainer = document.getElementById('file-preview-container');
    const uploadContainer = document.getElementById('file-upload-container');
    
    if (fileInput) fileInput.value = '';
    if (preview) preview.src = '';
    if (previewContainer) previewContainer.style.display = 'none';
    if (uploadContainer) uploadContainer.style.display = 'block';
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded");
    
    // Initialize map
    if (typeof google !== 'undefined' && google.maps) {
        initMap();
    } else {
        console.error("Google Maps API not loaded");
    }
    
    // Add click handlers to transport options
    document.querySelectorAll('.transport-option').forEach(option => {
        option.addEventListener('click', function() {
            selectMode(this);
        });
    });
    
    // Add file upload handler
    const fileInput = document.getElementById('proof-upload');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            handleFileSelect(this);
        });
    }
    
    // Add remove file handler
    const removeButton = document.getElementById('remove-file');
    if (removeButton) {
        removeButton.addEventListener('click', removeFile);
    }
});

// Make functions globally available
window.selectMode = selectMode;
window.handleFileSelect = handleFileSelect;
window.removeFile = removeFile; 