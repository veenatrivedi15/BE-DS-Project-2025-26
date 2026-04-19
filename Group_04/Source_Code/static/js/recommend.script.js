let map;
let markers = [];
let userMarker;
const clinicsListEl = document.getElementById('clinics-list');

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    document.getElementById('user-input').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') sendMessage();
    });
});

function initMap() {
    map = L.map('map').setView([20.5937, 78.9629], 5); // Default: India
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
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

    // Show typing indicator while waiting for bot response
    const typingEl = showTyping();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, language })
        });
        const data = await response.json();

        removeTyping(typingEl);

        if (data.error) {
            await addBotMessageWithTyping('Error: ' + data.error);
        } else {
            await addBotMessageWithTyping(data.response || '');
            if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
                addSuggestionChips(data.suggestions);
            }
        }
    } catch (err) {
        removeTyping(typingEl);
        await addBotMessageWithTyping('Error communicating with server.');
    }
}

function showTyping() {
    const chatWindow = document.getElementById('chat-window');
    const el = document.createElement('div');
    el.classList.add('typing-indicator');
    el.innerHTML = '<span></span><span></span><span></span>';
    chatWindow.appendChild(el);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return el;
}

function removeTyping(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

function addMessage(text, sender) {
    const chatWindow = document.getElementById('chat-window');
    const div = document.createElement('div');
    div.classList.add('message', sender);
    div.textContent = text;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function addBotMessageWithTyping(text) {
    const chatWindow = document.getElementById('chat-window');
    const div = document.createElement('div');
    div.classList.add('message', 'bot');
    chatWindow.appendChild(div);

    const fullText = String(text || '');
    const baseDelay = fullText.length > 240 ? 7 : 12;

    for (let i = 0; i < fullText.length; i += 1) {
        div.textContent += fullText.charAt(i);
        chatWindow.scrollTop = chatWindow.scrollHeight;

        // Slightly slower pause after punctuation for natural typing rhythm.
        const ch = fullText.charAt(i);
        const pause = /[.,!?;:]/.test(ch) ? 30 : baseDelay;
        await new Promise((resolve) => setTimeout(resolve, pause));
    }
}

function addSuggestionChips(suggestions) {
    const chatWindow = document.getElementById('chat-window');
    const wrapper = document.createElement('div');
    wrapper.classList.add('suggestion-wrap');

    suggestions.slice(0, 3).forEach((text) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'suggestion-chip';
        btn.textContent = text;
        btn.addEventListener('click', () => {
            const input = document.getElementById('user-input');
            input.value = text;
            sendMessage();
        });
        wrapper.appendChild(btn);
    });

    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

/* --------------------------------------------------
   Geolocation -> Overpass API -> Leaflet Map
-------------------------------------------------- */

function getClinics() {
    if (!navigator.geolocation) {
        addMessage('Geolocation is not supported by your browser.', 'bot');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;

            map.setView([lat, lng], 14);

            if (userMarker) map.removeLayer(userMarker);
            userMarker = L.marker([lat, lng], { icon: makeIcon('#6366f1', 16) })
                .addTo(map)
                .bindPopup('<b>You are here</b>')
                .openPopup();

            fetchEyeClinics(lat, lng);
        },
        (err) => {
            const msgs = {
                1: 'Location permission denied. Please allow location access in your browser.',
                2: 'Your location is currently unavailable.',
                3: 'Location request timed out. Please try again.'
            };
            addMessage(msgs[err.code] || 'Unable to retrieve your location.', 'bot');
        },
        { timeout: 10000, maximumAge: 60000 }
    );
}

async function fetchEyeClinics(lat, lng) {
    try {
        const response = await fetch('/search_clinics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ location: lat + ',' + lng })
        });
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.error || 'Failed to fetch clinics.');
        }

        const clinics = payload.clinics || [];
        const source = payload.source || 'provider';

        if (clinics.length > 0) {
            updateMap(clinics);
            renderClinicCards(clinics);
            if (payload.warning) {
                addMessage('Note: ' + payload.warning, 'bot');
            }
            return;
        }

        renderClinicCards([]);
        if (payload.warning) {
            addMessage('Clinic search warning: ' + payload.warning, 'bot');
        }
        addMessage("No clinics found in your area. Try searching online for 'eye clinic near me'.", 'bot');
    } catch (err) {
        console.error(err);
        renderClinicCards([]);
        addMessage('Could not load clinics. ' + (err.message || 'Please check your internet connection and try again.'), 'bot');
    }
}

function renderClinicCards(clinics) {
    if (!clinicsListEl) {
        return;
    }

    if (!clinics || clinics.length === 0) {
        clinicsListEl.innerHTML = '<div class="clinic-card"><div class="clinic-name">No nearby clinics found</div><div class="clinic-meta">Try again with location enabled, or search manually for eye hospitals in your city.</div></div>';
        return;
    }

    clinicsListEl.innerHTML = clinics.slice(0, 12).map(function(clinic) {
        var ratingText = (clinic.rating !== undefined && clinic.rating !== null) ? ('Rating: ' + clinic.rating + (clinic.reviews ? ' (' + clinic.reviews + ' reviews)' : '')) : '';
        var site = clinic.website ? ('<div class="clinic-meta"><a href="' + clinic.website + '" target="_blank" rel="noopener noreferrer">Visit website</a></div>') : '';
        return (
            '<div class="clinic-card">' +
            '<div class="clinic-name">' + (clinic.name || 'Eye Clinic') + '</div>' +
            (clinic.address ? '<div class="clinic-meta">Address: ' + clinic.address + '</div>' : '') +
            (clinic.phone ? '<div class="clinic-meta">Phone: ' + clinic.phone + '</div>' : '') +
            (ratingText ? '<div class="clinic-meta">' + ratingText + '</div>' : '') +
            site +
            '</div>'
        );
    }).join('');
}

function updateMap(clinics) {
    markers.forEach(function(m) { map.removeLayer(m); });
    markers = [];

    if (!clinics.length) return;

    var bounds = L.latLngBounds();
    if (userMarker) bounds.extend(userMarker.getLatLng());

    clinics.forEach(function(clinic) {
        var popupHtml =
            '<div style="font-family:Inter,sans-serif;min-width:170px;line-height:1.5;">' +
            '<strong style="color:#1e293b;font-size:13px;">' + clinic.name + '</strong>' +
            (clinic.address ? '<div style="color:#64748b;font-size:11px;margin-top:4px;">📍 ' + clinic.address + '</div>' : '') +
            (clinic.phone ? '<div style="color:#64748b;font-size:11px;margin-top:2px;">📞 ' + clinic.phone + '</div>' : '') +
            (clinic.website ? '<div style="font-size:11px;margin-top:4px;"><a href="' + clinic.website + '" target="_blank" style="color:#6366f1;">🌐 Visit website</a></div>' : '') +
            '</div>';

        var marker = L.marker([clinic.latitude, clinic.longitude], { icon: makeIcon('#ef4444', 14) }).addTo(map);
        marker.bindPopup(popupHtml);
        markers.push(marker);
        bounds.extend([clinic.latitude, clinic.longitude]);
    });

    if (markers.length > 0) {
        map.fitBounds(bounds, { padding: [40, 40] });
    }
}

// Lightweight coloured circle icon (no image dependency)
function makeIcon(color, size) {
    var half = Math.floor(size / 2);
    return L.divIcon({
        html: '<div style="background:' + color + ';width:' + size + 'px;height:' + size + 'px;border-radius:50%;border:2.5px solid white;box-shadow:0 2px 8px ' + color + '80;"></div>',
        className: '',
        iconSize: [size, size],
        iconAnchor: [half, half],
        popupAnchor: [0, -(half + 4)]
    });
}
