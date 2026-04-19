let map;
let markers = [];
let userMarker;
const clinicsListEl = document.getElementById('clinics-list');

function normalizeText(value) {
    return String(value || '').trim();
}

function toSafeHttpUrl(value) {
    const raw = normalizeText(value);
    if (!raw) return '';
    try {
        const parsed = new URL(raw, window.location.origin);
        const protocol = parsed.protocol.toLowerCase();
        if (protocol === 'http:' || protocol === 'https:') {
            return parsed.href;
        }
    } catch (_err) {
        return '';
    }
    return '';
}

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
    for (let i = 0; i < 3; i += 1) {
        el.appendChild(document.createElement('span'));
    }
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
        clinicsListEl.replaceChildren();
        const card = document.createElement('div');
        card.className = 'clinic-card';
        const name = document.createElement('div');
        name.className = 'clinic-name';
        name.textContent = 'No nearby clinics found';
        const meta = document.createElement('div');
        meta.className = 'clinic-meta';
        meta.textContent = 'Try again with location enabled, or search manually for eye hospitals in your city.';
        card.appendChild(name);
        card.appendChild(meta);
        clinicsListEl.appendChild(card);
        return;
    }

    clinicsListEl.replaceChildren();
    clinics.slice(0, 12).forEach(function (clinic) {
        const card = document.createElement('div');
        card.className = 'clinic-card';

        const name = document.createElement('div');
        name.className = 'clinic-name';
        name.textContent = normalizeText(clinic.name) || 'Eye Clinic';
        card.appendChild(name);

        const address = normalizeText(clinic.address);
        if (address) {
            const row = document.createElement('div');
            row.className = 'clinic-meta';
            row.textContent = 'Address: ' + address;
            card.appendChild(row);
        }

        const phone = normalizeText(clinic.phone);
        if (phone) {
            const row = document.createElement('div');
            row.className = 'clinic-meta';
            row.textContent = 'Phone: ' + phone;
            card.appendChild(row);
        }

        if (clinic.rating !== undefined && clinic.rating !== null) {
            const ratingRow = document.createElement('div');
            ratingRow.className = 'clinic-meta';
            const reviews = clinic.reviews ? ` (${clinic.reviews} reviews)` : '';
            ratingRow.textContent = `Rating: ${clinic.rating}${reviews}`;
            card.appendChild(ratingRow);
        }

        const safeWebsite = toSafeHttpUrl(clinic.website);
        if (safeWebsite) {
            const siteRow = document.createElement('div');
            siteRow.className = 'clinic-meta';
            const link = document.createElement('a');
            link.href = safeWebsite;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = 'Visit website';
            siteRow.appendChild(link);
            card.appendChild(siteRow);
        }

        clinicsListEl.appendChild(card);
    });
}

function updateMap(clinics) {
    markers.forEach(function(m) { map.removeLayer(m); });
    markers = [];

    if (!clinics.length) return;

    var bounds = L.latLngBounds();
    if (userMarker) bounds.extend(userMarker.getLatLng());

    clinics.forEach(function(clinic) {
        var popupContent = document.createElement('div');
        popupContent.style.fontFamily = 'Inter, sans-serif';
        popupContent.style.minWidth = '170px';
        popupContent.style.lineHeight = '1.5';

        var title = document.createElement('strong');
        title.style.color = '#1e293b';
        title.style.fontSize = '13px';
        title.textContent = normalizeText(clinic.name) || 'Eye Clinic';
        popupContent.appendChild(title);

        var address = normalizeText(clinic.address);
        if (address) {
            var addressRow = document.createElement('div');
            addressRow.style.color = '#64748b';
            addressRow.style.fontSize = '11px';
            addressRow.style.marginTop = '4px';
            addressRow.textContent = '📍 ' + address;
            popupContent.appendChild(addressRow);
        }

        var phone = normalizeText(clinic.phone);
        if (phone) {
            var phoneRow = document.createElement('div');
            phoneRow.style.color = '#64748b';
            phoneRow.style.fontSize = '11px';
            phoneRow.style.marginTop = '2px';
            phoneRow.textContent = '📞 ' + phone;
            popupContent.appendChild(phoneRow);
        }

        var safeWebsite = toSafeHttpUrl(clinic.website);
        if (safeWebsite) {
            var siteRow = document.createElement('div');
            siteRow.style.fontSize = '11px';
            siteRow.style.marginTop = '4px';
            var siteLink = document.createElement('a');
            siteLink.href = safeWebsite;
            siteLink.target = '_blank';
            siteLink.rel = 'noopener noreferrer';
            siteLink.style.color = '#6366f1';
            siteLink.textContent = '🌐 Visit website';
            siteRow.appendChild(siteLink);
            popupContent.appendChild(siteRow);
        }

        var marker = L.marker([clinic.latitude, clinic.longitude], { icon: makeIcon('#ef4444', 14) }).addTo(map);
        marker.bindPopup(popupContent);
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
