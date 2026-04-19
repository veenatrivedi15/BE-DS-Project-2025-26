let map;
let markers = [];
let userMarker;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    
    // Allow pressing Enter to send message
    document.getElementById('user-input').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});

function initMap() {
    map = L.map('map').setView([40.7128, -74.0060], 13); // Default to NY

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const languageSelect = document.getElementById('language-select');
    const message = userInput.value.trim();
    const language = languageSelect.value;
    
    if (!message) return;

    addMessage(message, 'user');
    userInput.value = '';

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, language: language })
        });
        const data = await response.json();

        if (data.error) {
            addMessage('Error: ' + data.error, 'bot');
        } else {
            addMessage(data.response, 'bot');
            if (data.should_search) {
                addMessage("I'm locating nearby eye specialists for you...", 'bot');
                getClinics();
            }
        }
    } catch (error) {
        addMessage('Error communicating with server.', 'bot');
    }
}

function addMessage(text, sender) {
    const chatWindow = document.getElementById('chat-window');
    const div = document.createElement('div');
    div.classList.add('message', sender);
    div.innerText = text;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function getClinics() {
    if (navigator.geolocation) {
        addMessage("Requesting your location...", 'bot');
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                // Center map on user
                map.setView([lat, lng], 13);
                
                // Add user marker
                if (userMarker) {
                    map.removeLayer(userMarker);
                }
                userMarker = L.marker([lat, lng]).addTo(map)
                    .bindPopup("You are here")
                    .openPopup();

                fetchClinics(`${lat},${lng}`);
            },
            (error) => {
                let errorMsg = "Unable to retrieve your location.";
                if(error.code == error.PERMISSION_DENIED) {
                     errorMsg += " Permission denied.";
                }
                addMessage(errorMsg, 'bot');
            }
        );
    } else {
        addMessage("Geolocation is not supported by this browser.", 'bot');
    }
}

async function fetchClinics(location) {
    try {
        const response = await fetch('/search_clinics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ location: location })
        });
        const data = await response.json();

        if (data.clinics) {
            updateMap(data.clinics);
            if (data.clinics.length > 0) {
                 addMessage(`Found ${data.clinics.length} clinics nearby.`, 'bot');
            }
        } else if (data.error) {
            addMessage(`Error finding clinics: ${data.error}`, 'bot');
        }
    } catch (error) {
        console.error('Error fetching clinics:', error);
        addMessage('Error communicating with server to fetch clinics.', 'bot');
    }
}

function updateMap(clinics) {
    // Clear existing clinic markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];

    if (!clinics) return;

    const bounds = L.latLngBounds();
    // Include user location in bounds if exists
    if (userMarker) {
        bounds.extend(userMarker.getLatLng());
    }

    clinics.forEach(clinic => {
        if (clinic.latitude && clinic.longitude) {
            const marker = L.marker([clinic.latitude, clinic.longitude]).addTo(map);
            marker.bindPopup(`<b>${clinic.name}</b><br>${clinic.address}<br>Rating: ${clinic.rating || 'N/A'}`);
            markers.push(marker);
            bounds.extend([clinic.latitude, clinic.longitude]);
        }
    });
    
    // Fit bounds only if we have markers
    if (markers.length > 0) {
        map.fitBounds(bounds);
    }
}
