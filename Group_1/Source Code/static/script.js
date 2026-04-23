// Global variables - Now using separate HTML files
let currentPage = 'home';

// Page navigation functions - Removed since using separate files
// Navigation is now handled by HTML href links

// Crop Recommendation - Event listener is now added in DOMContentLoaded

// --- USER AUTHENTICATION & PROFILE UI ---
function checkLoginState() {
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    const username = localStorage.getItem('username');

    if (isLoggedIn && username) {
        updateNavForLoggedInUser(username);
    }
}

function updateNavForLoggedInUser(username) {
    // Hide old auth-links (legacy)
    const authLinks = document.querySelector('.auth-links');
    if (authLinks) authLinks.style.display = 'none';

    // Hide new nav-auth (desktop) and mobile-auth containers
    const navAuth = document.querySelector('.nav-auth');
    if (navAuth) navAuth.style.display = 'none';
    const mobileAuth = document.querySelector('.mobile-auth');
    if (mobileAuth) mobileAuth.style.display = 'none';

    // Add "Dashboard" & "Organisations" links to desktop nav
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        if (!document.getElementById('nav-dash-link')) {
            const dashLink = document.createElement('a');
            dashLink.href = "/dashboard";
            dashLink.id = "nav-dash-link";
            dashLink.textContent = "Dashboard";
            navLinks.insertBefore(dashLink, navLinks.firstChild);
        }
        if (!document.getElementById('nav-org-link')) {
            const orgLink = document.createElement('a');
            orgLink.href = "/organisations";
            orgLink.id = "nav-org-link";
            orgLink.textContent = "Organisations";
            const dashLink = document.getElementById('nav-dash-link');
            if (dashLink && dashLink.nextSibling) {
                navLinks.insertBefore(orgLink, dashLink.nextSibling);
            } else {
                navLinks.appendChild(orgLink);
            }
        }
    }

    // Also inject links into mobile menu (before .mobile-auth)
    const mobileMenu = document.querySelector('.mobile-menu');
    if (mobileMenu && !document.getElementById('mobile-dash-link')) {
        const mDash = document.createElement('a');
        mDash.href = "/dashboard";
        mDash.id = "mobile-dash-link";
        mDash.textContent = "Dashboard";
        mobileMenu.insertBefore(mDash, mobileMenu.firstChild);

        const mOrg = document.createElement('a');
        mOrg.href = "/organisations";
        mOrg.id = "mobile-org-link";
        mOrg.textContent = "Organisations";
        mobileMenu.insertBefore(mOrg, mDash.nextSibling);

        // Add logout button in mobile menu
        const logoutBtn = document.createElement('a');
        logoutBtn.href = "#";
        logoutBtn.textContent = "Logout";
        logoutBtn.style.color = "#e74c3c";
        logoutBtn.addEventListener('click', (e) => { e.preventDefault(); logout(); });
        mobileMenu.appendChild(logoutBtn);
    }

    // Create User Profile Section in desktop nav
    const nav = document.querySelector('.nav');
    if (nav && !document.querySelector('.user-profile-section')) {
        const profileSection = document.createElement('div');
        profileSection.className = 'user-profile-section';
        profileSection.innerHTML = `
            <div class="user-profile-info" style="display:flex;align-items:center;gap:8px;">
                <span class="profile-icon">👤</span>
                <span class="profile-name" style="color:#c8e6c9;font-weight:600;">${username}</span>
            </div>
            <button onclick="logout()" class="btn-signin" style="margin-left:12px;font-size:0.82rem;padding:6px 14px;cursor:pointer;">Logout</button>
        `;
        profileSection.style.display = 'flex';
        profileSection.style.alignItems = 'center';
        nav.appendChild(profileSection);
    }

    // Optional: Update Hero section if on Home Page
    const heroContent = document.querySelector('.hero .container');
    if (heroContent && !document.getElementById('hero-dash-btn')) {
        const dashBtn = document.createElement('button');
        dashBtn.id = 'hero-dash-btn';
        dashBtn.className = 'btn';
        dashBtn.style.marginTop = '20px';
        dashBtn.style.maxWidth = '300px';
        dashBtn.innerHTML = '🚀 Go to your Dashboard';
        dashBtn.onclick = () => window.location.href = '/dashboard';
        const p = heroContent.querySelector('p');
        if (p) p.insertAdjacentElement('afterend', dashBtn);
    }
}

function logout() {
    if (confirm("Are you sure you want to logout?")) {
        localStorage.removeItem('isLoggedIn');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
        window.location.reload();
    }
}

function displayCropResults(result) {
    const resultsDiv = document.getElementById('crop-results');
    resultsDiv.style.display = 'block';

    const confidencePercentage = (result.prediction_confidence * 100).toFixed(1);

    resultsDiv.innerHTML = `
        <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(45, 74, 62, 0.95) 100%); border: 2px solid rgba(74, 124, 89, 0.4); border-radius: 16px; padding: 28px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #9FE29F; font-weight: 700; font-size: 1.5rem;">
                <span style=\"font-size: 1.8rem;\">🌿</span> Recommended Crop
            </div>
            <div style="font-size: 2rem; color: #b6f5b6; font-weight: 800; margin-bottom: 8px;">${result.predicted_crop}</div>
            <div style="color: #6b9c7a; margin-bottom: 12px;">Confidence: ${confidencePercentage}%</div>
            <div style="color: #c8e6c9;">Based on your soil and environmental conditions, this crop is most suitable for cultivation.</div>
        </div>
    `;
}

// Weather functions - Revised Flow
async function initializeWeatherPage() {
    const dateDisplay = document.getElementById('current-date-display');
    if (dateDisplay) {
        const now = new Date();
        dateDisplay.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    await loadCities();

    // Add event listener for city change
    const citySelect = document.getElementById('city-select');
    if (citySelect) {
        citySelect.addEventListener('change', function () {
            const selectedCity = this.value;
            if (selectedCity) {
                fetchCityForecast(selectedCity);
            }
        });
    }
}

async function loadCities() {
    try {
        const response = await fetch('/api/cities');
        const data = await response.json();

        const citySelect = document.getElementById('city-select');
        if (citySelect && data.cities) {
            // Clear existing options except first
            citySelect.innerHTML = '<option value="" disabled selected>-- Choose a City --</option>';

            data.cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                citySelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading cities:', error);
    }
}

async function fetchCityForecast(city) {
    const loadingDiv = document.getElementById('weather-loading');
    const forecastDiv = document.getElementById('weather-forecast');
    const gridDiv = document.getElementById('forecast-grid');
    const cityNameSpan = document.getElementById('forecast-city-name');

    // UI State: Loading
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (forecastDiv) forecastDiv.style.display = 'none';

    try {
        const response = await fetch('/api/predict-weather', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ city: city })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // UI State: Success
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (forecastDiv) forecastDiv.style.display = 'block';
        if (cityNameSpan) cityNameSpan.textContent = `for ${data.city}`;

        // Render Forecast
        if (gridDiv && data.forecast) {
            let html = '';
            data.forecast.forEach(day => {
                const dateObj = new Date(day.date);
                const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
                const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

                // Determine icon (simple logic)
                let icon = '🌤️';
                const cond = (day.weather_condition || '').toLowerCase();
                if (cond.includes('rain')) icon = '🌧️';
                else if (cond.includes('cloud')) icon = '☁️';
                else if (cond.includes('clear') || cond.includes('sun')) icon = '☀️';
                else if (cond.includes('storm')) icon = '⛈️';

                html += `
                    <div class="weather-card" style="text-align: center;">
                        <div style="background: rgba(107, 156, 122, 0.2); padding: 5px 10px; border-radius: 10px; display: inline-block; margin-bottom: 10px; font-weight: bold; color: #9FE29F;">
                            ${dayName}, ${dateStr}
                        </div>
                        <div style="font-size: 3rem; margin: 10px 0;">${icon}</div>
                        <div style="font-size: 1.2rem; font-weight: bold; color: white; margin-bottom: 5px;">${day.weather_condition}</div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 15px; font-size: 0.9rem; color: #c8e6c9;">
                            <div style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 8px;">
                                <div>🌡️ Temp</div>
                                <div style="font-weight: bold; color: #fff;">${day.avg_temp}°C</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 8px;">
                                <div>💧 Hum</div>
                                <div style="font-weight: bold; color: #fff;">${day.avg_humidity}%</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 8px;">
                                <div>💨 Wind</div>
                                <div style="font-weight: bold; color: #fff;">${day.wind_speed} <small>km/h</small></div>
                            </div>
                            <!-- You can add pressure or other fields if needed, layout permits -->
                        </div>
                    </div>
                `;
            });
            gridDiv.innerHTML = html;
        }

    } catch (error) {
        console.error('Forecast Error:', error);
        if (loadingDiv) loadingDiv.style.display = 'none';
        alert("Failed to load forecast: " + error.message);
    }
}

// DB status helper (development visibility)
async function fetchDbStatus() {
    try {
        const resp = await fetch('/api/db-status');
        const data = await resp.json();
        console.log('DB status:', data);
        // optionally display at bottom of page
        const footer = document.querySelector('footer');
        if (footer && data && data.collections) {
            const info = JSON.stringify(data.collections);
            const div = document.createElement('div');
            div.style.fontSize = '0.7rem';
            div.style.color = '#aaa';
            div.textContent = info;
            footer.appendChild(div);
        }
    } catch (err) {
        console.error('Failed to fetch DB status', err);
    }
}

// Market functions
async function fetchMarketData() {
    try {
        const response = await fetch('/api/market-trends');
        const data = await response.json();
        displayMarketData(data);
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('market-tbody').innerHTML = '<tr><td colspan="4" style="color: #e74c3c; text-align: center;">Error loading market data</td></tr>';
    }
}

function displayMarketData(data) {
    const tbody = document.getElementById('market-tbody');
    const lastUpdated = document.getElementById('last-updated');
    const insightsGrid = document.getElementById('insights-grid');

    // Update last updated time
    lastUpdated.textContent = `Last updated: ${new Date(data.last_updated).toLocaleString()}`;

    // Market table
    let tableHTML = '';
    data.trends.forEach(trend => {
        const trendColor = trend.trend === 'Rising' ? '#27ae60' : trend.trend === 'Falling' ? '#e74c3c' : '#f39c12';
        const demandColor = trend.demand === 'High' ? '#27ae60' : trend.demand === 'Medium' ? '#f39c12' : '#e74c3c';

        tableHTML += `
            <tr>
                <td>${trend.crop}</td>
                <td><strong>₹${trend.price}</strong></td>
                <td style="color: ${trendColor};">${trend.trend}</td>
                <td style="color: ${demandColor};">${trend.demand}</td>
            </tr>
        `;
    });
    tbody.innerHTML = tableHTML;

    // Market insights
    let insightsHTML = '';
    data.trends.forEach(trend => {
        if (trend.trend === 'Rising') {
            insightsHTML += `
                <div style="background: rgba(39, 174, 96, 0.1); padding: 20px; border-radius: 15px; border: 2px solid rgba(39, 174, 96, 0.3);">
                    <h4 style="color: #27ae60;">📈 ${trend.crop} - Rising Trend</h4>
                    <p style="color: #c8e6c9;">Good time to sell ${trend.crop.toLowerCase()} at current prices.</p>
                </div>
            `;
        } else if (trend.trend === 'Falling') {
            insightsHTML += `
                <div style="background: rgba(231, 76, 60, 0.1); padding: 20px; border-radius: 15px; border: 2px solid rgba(231, 76, 60, 0.3);">
                    <h4 style="color: #e74c3c;">📉 ${trend.crop} - Falling Trend</h4>
                    <p style="color: #c8e6c9;">Consider holding ${trend.crop.toLowerCase()} or selling at better prices.</p>
                </div>
            `;
        }
    });
    insightsGrid.innerHTML = insightsHTML;
}

let marketTrendChart = null;

async function fetchSpecificMarketTrend(crop, city) {
    const statusEl = document.getElementById('market-status');
    const outputEl = document.getElementById('market-trend-output');
    const titleEl = document.getElementById('market-trend-title');
    const summaryEl = document.getElementById('market-trend-summary');

    if (statusEl) {
        statusEl.style.color = '#7f8c8d';
        statusEl.textContent = 'Loading trend from market dataset...';
    }

    try {
        const response = await fetch('/api/market-trend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ crop, city })
        });
        const contentType = response.headers.get('content-type') || '';
        let data;
        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            throw new Error('Server returned non-JSON response. Please check if the backend is running and the API route exists.');
        }

        if (!response.ok) {
            const msg = data && data.message ? data.message : 'Something went wrong';
            throw new Error(msg);
        }

        if (data.status === 'no_data') {
            if (statusEl) {
                statusEl.style.color = '#e74c3c';
                statusEl.textContent = data.message || 'No data found for this selection.';
            }
            if (outputEl) outputEl.style.display = 'none';
            return;
        }

        const trend = data.trend;
        if (!trend || !trend.has_data) {
            if (statusEl) {
                statusEl.style.color = '#e74c3c';
                statusEl.textContent = 'No data found for this selection.';
            }
            if (outputEl) outputEl.style.display = 'none';
            return;
        }

        if (titleEl) {
            titleEl.textContent = `${trend.crop} price trend in ${trend.city} (2020–2025)`;
        }

        // Render chart
        const ctx = document.getElementById('market-trend-chart').getContext('2d');
        if (marketTrendChart) {
            marketTrendChart.destroy();
        }

        marketTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trend.years,
                datasets: [
                    {
                        label: 'Min Price',
                        data: trend.min_prices,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderDash: [4, 4],
                        tension: 0.2
                    },
                    {
                        label: 'Modal Price',
                        data: trend.modal_prices,
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.15)',
                        borderWidth: 3,
                        tension: 0.3
                    },
                    {
                        label: 'Max Price',
                        data: trend.max_prices,
                        borderColor: '#e67e22',
                        backgroundColor: 'rgba(230, 126, 34, 0.1)',
                        borderDash: [4, 4],
                        tension: 0.2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#ecf0f1'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#bdc3c7' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    y: {
                        ticks: {
                            color: '#bdc3c7',
                            callback: value => `₹${value}`
                        },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                }
            }
        });

        // Summary cards
        if (summaryEl) {
            summaryEl.innerHTML = `
                <div style="background: rgba(26, 26, 26, 0.9); border-radius: 14px; padding: 18px; border: 1px solid rgba(74, 124, 89, 0.5);">
                    <h4 style="margin-bottom: 8px;">Average Sale Price</h4>
                    <p style="font-size: 1.4rem;"><strong>₹${trend.avg_sale_price.toFixed(0)}</strong> / quintal</p>
                    <p style="color: #7f8c8d; font-size: 0.9rem;">Based on modal prices across years.</p>
                </div>
                <div style="background: rgba(26, 26, 26, 0.9); border-radius: 14px; padding: 18px; border: 1px solid rgba(74, 124, 89, 0.5);">
                    <h4 style="margin-bottom: 8px;">Price Range (2020–2025)</h4>
                    <p>Min: <strong>₹${trend.min_price.toFixed(0)}</strong> / quintal</p>
                    <p>Max: <strong>₹${trend.max_price.toFixed(0)}</strong> / quintal</p>
                    <p style="color: #7f8c8d; font-size: 0.9rem;">Average spread: ₹${trend.avg_spread.toFixed(0)} (${trend.volatility} volatility)</p>
                </div>
                <div style="background: rgba(26, 26, 26, 0.9); border-radius: 14px; padding: 18px; border: 1px solid rgba(74, 124, 89, 0.5);">
                    <h4 style="margin-bottom: 8px;">Market Status</h4>
                    <p style="font-size: 1.2rem;">
                        <span style="margin-right: 6px;">${trend.status_icon}</span>
                        <strong>${trend.market_status}</strong>
                    </p>
                    <p style="color: #7f8c8d; font-size: 0.9rem;">Comparison of first vs last year modal price.</p>
                </div>
            `;
        }

        if (statusEl) {
            statusEl.style.color = '#2ecc71';
            statusEl.textContent = 'Trend loaded successfully.';
        }
        if (outputEl) {
            outputEl.style.display = 'block';
        }
    } catch (error) {
        console.error('Error:', error);
        if (statusEl) {
            statusEl.style.color = '#e74c3c';
            statusEl.textContent = error.message || 'Error loading market trend';
        }
        const outputEl = document.getElementById('market-trend-output');
        if (outputEl) outputEl.style.display = 'none';
    }
}

// Organizations page functions
async function fetchOrganizations() {
    const orgGrid = document.getElementById('org-grid');
    if (!orgGrid) return;

    try {
        const response = await fetch('/api/admin/list');
        const organizations = await response.json();
        displayOrganizations(organizations);
    } catch (error) {
        console.error('Error fetching organizations:', error);
        orgGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #e74c3c; padding: 40px;">Error loading organizations. Please try again.</div>';
    }
}

function displayOrganizations(organizations) {
    const orgGrid = document.getElementById('org-grid');
    if (!orgGrid) return;

    if (!organizations || organizations.length === 0) {
        orgGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666; padding: 40px;"><p style="font-size: 1.1rem; margin-bottom: 10px;">📋 No organizations registered yet</p><p style="opacity: 0.7;">Check back soon to discover agricultural partners and organizations!</p></div>';
        return;
    }

    let html = '';
    organizations.forEach((org, idx) => {
        const icon = ['🏢', '🌾', '🚜', '🏭'][idx % 4];
        const joinedDate = org.created_at ? new Date(org.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : null;
        
        html += `
            <div class="org-card">
                <span class="org-icon">${icon}</span>
                <div class="org-name">${org.name || 'N/A'}</div>
                <div class="org-detail">
                    <span>📧 <strong>Email:</strong> ${org.email || 'N/A'}</span>
                </div>
                <div class="org-detail">
                    <span>👤 <strong>Username:</strong> ${org.username || 'N/A'}</span>
                </div>
                ${org.contact_number ? `
                <div class="org-detail">
                    <span>📱 <strong>Phone:</strong> ${org.contact_number}</span>
                </div>
                ` : ''}
                ${org.address ? `
                <div class="org-detail">
                    <span>📍 <strong>Address:</strong> ${org.address}</span>
                </div>
                ` : ''}
                ${org.pincode ? `
                <div class="org-detail">
                    <span>🔖 <strong>Pincode:</strong> ${org.pincode}</span>
                </div>
                ` : ''}
                ${joinedDate ? `
                <div class="org-detail">
                    <span>🗓️ <strong>Joined:</strong> ${joinedDate}</span>
                </div>
                ` : ''}
            </div>
        `;
    });
    orgGrid.innerHTML = html;
}

// E-commerce functions
function toggleAddProductForm() {
    const form = document.getElementById('add-product-form');
    const btn = document.getElementById('add-product-btn');

    if (form.style.display === 'none') {
        form.style.display = 'block';
        btn.textContent = '❌ Cancel';
    } else {
        form.style.display = 'none';
        btn.textContent = '➕ Add New Product';
    }
}

async function fetchProducts() {
    try {
        const response = await fetch('/api/marketplace/list');
        const products = await response.json();
        renderProducts(products);
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('products-grid').innerHTML = '<p style="color: #e74c3c;">Error loading products</p>';
    }
}

function renderProducts(products) {
    const productsGrid = document.getElementById('products-grid');
    const productsCount = document.getElementById('products-count');

    if (productsCount) productsCount.textContent = products.length;

    if (!products || products.length === 0) {
        if (productsGrid) productsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #999; padding: 40px;">No products available yet. Be the first to list one!</div>';
        return;
    }

    let productsHTML = '';
    products.forEach(product => {
        const seller = product.added_by || 'Unknown';
        const category = product.category || 'N/A';
        const isFresh = category.toLowerCase().includes('fruit') || category.toLowerCase().includes('vegetable');
        const badgeText = isFresh ? 'Fresh 🍃' : 'Organic ✨';

        // Image logic based on uploaded images array
        let imgSrc = 'https://via.placeholder.com/300x200?text=No+Image';
        if (product.images && product.images.length > 0) {
            imgSrc = `/static/${product.images[0]}`;
        } else if (product.image) {
            imgSrc = `/static/${product.image}`;
        }

        // Calculate a mock "original price" to show savings
        const currentPrice = parseFloat(product.price);
        const originalPrice = Math.round(currentPrice * 1.25);
        const savings = originalPrice - currentPrice;

        productsHTML += `
            <div class="ecom-card">
                <div class="ecom-img-wrapper">
                    <span class="ecom-badge">${badgeText}</span>
                    <img src="${imgSrc}" alt="${product.name}" class="ecom-img">
                    <div class="ecom-gradient"></div>
                    <button class="ecom-add-btn" onclick="addToCart('${product._id}', '${product.name.replace(/'/g, "\\'")}', ${currentPrice})">
                        + Add to Cart
                    </button>
                </div>
                <div class="ecom-content">
                    <h3 class="ecom-title">${product.name}</h3>
                    <div class="ecom-meta">
                        <span>${product.quantity || '1 unit'}</span>
                        <span>📍 ${seller}</span>
                    </div>
                    <div class="ecom-price-row">
                        <span class="ecom-price-current">₹${currentPrice}</span>
                        <span class="ecom-price-old">₹${originalPrice}</span>
                        <span class="ecom-save-badge">SAVE ₹${savings}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    if (productsGrid) {
        productsGrid.innerHTML = productsHTML;
    }
}

// Add to Cart stub function
function addToCart(productId, productName, price) {
    // In a real app, this would add to a cart state or send to backend
    alert(`Added ${productName} to your cart for ₹${price}!`);
}

// Add product form submission - Event listener is now added in DOMContentLoaded

// ===== MORPHING AI PANEL =====

function initMorphPanel() {
    const panel = document.getElementById('ai-morph-panel');
    if (!panel) return;

    const toggle = panel.querySelector('.ai-panel-toggle');
    const closeBtn = panel.querySelector('.ai-panel-close');
    const textarea = document.getElementById('ai-panel-textarea');
    const sendBtn = document.getElementById('ai-panel-send');
    const messagesEl = document.getElementById('ai-panel-messages');

    // --- Open panel ---
    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        panel.classList.add('is-open');
        setTimeout(() => textarea && textarea.focus(), 400);
    });

    // --- Close panel ---
    function closePanel() {
        panel.classList.remove('is-open');
        document.body.style.overflow = '';
    }

    if (closeBtn) closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closePanel();
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (panel.classList.contains('is-open') && !panel.contains(e.target)) {
            closePanel();
        }
    });

    // Prevent panel clicks from closing
    panel.addEventListener('click', (e) => e.stopPropagation());

    // --- Keyboard shortcuts ---
    if (textarea) {
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closePanel();
                textarea.blur();
            }
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendAiMessage();
            }
        });

        // Auto-resize textarea
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
        });
    }

    // --- Send button ---
    if (sendBtn) sendBtn.addEventListener('click', sendAiMessage);

    // --- Send message logic ---
    async function sendAiMessage() {
        if (!textarea) return;
        const message = textarea.value.trim();
        if (!message) return;

        appendMsg('user', message);
        textarea.value = '';
        textarea.style.height = 'auto';

        // Show typing indicator
        const typingEl = document.createElement('div');
        typingEl.className = 'msg-typing';
        typingEl.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
        messagesEl.appendChild(typingEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        try {
            const response = await fetch('/api/chatbot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            const data = await response.json();
            typingEl.remove();

            if (data.response) {
                appendMsg('ai', data.response);
            } else {
                appendMsg('ai', "Sorry, I couldn't process your question. Please try again.");
            }
        } catch (error) {
            typingEl.remove();
            console.error('AI Panel error:', error);
            appendMsg('ai', "I'm having trouble connecting right now. Please try again in a moment.");
        }
    }

    function appendMsg(role, text) {
        const div = document.createElement('div');
        div.className = role === 'user' ? 'msg msg-user' : 'msg msg-ai';
        div.textContent = text;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

// Legacy chatbot functions (kept as no-ops for backward compat)
function toggleChatbot() {}
function handleChatbotKeyPress() {}
function sendChatMessage() {}

// Initialize page
document.addEventListener('DOMContentLoaded', function () {
    console.log('AgriAid+ loaded successfully!');

    // ===== NAVBAR SCROLL EFFECT =====
    const siteHeader = document.getElementById('site-header') || document.querySelector('.header');
    if (siteHeader) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 10) {
                siteHeader.classList.add('scrolled');
            } else {
                siteHeader.classList.remove('scrolled');
            }
        }, { passive: true });
    }

    // ===== HAMBURGER MENU TOGGLE =====
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (hamburgerBtn && mobileMenu) {
        hamburgerBtn.addEventListener('click', function () {
            const isOpen = hamburgerBtn.classList.toggle('is-open');
            mobileMenu.classList.toggle('is-open');
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });

        // Close menu when a link inside it is clicked
        mobileMenu.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                hamburgerBtn.classList.remove('is-open');
                mobileMenu.classList.remove('is-open');
                document.body.style.overflow = '';
            });
        });

        // Close menu on resize above mobile breakpoint
        window.addEventListener('resize', function () {
            if (window.innerWidth > 768) {
                hamburgerBtn.classList.remove('is-open');
                mobileMenu.classList.remove('is-open');
                document.body.style.overflow = '';
            }
        });
    }

    // immediately adjust navigation if user is logged in
    checkLoginState();

    // ===== MORPHING AI PANEL =====
    initMorphPanel();

    // debug: log DB state to console
    fetchDbStatus();

    // Check if we're on a page that needs data loading
    if (document.getElementById('crop-form')) {
        console.log('Crop recommendation page loaded');
        // Add event listener for crop form
        document.getElementById('crop-form').addEventListener('submit', async function (e) {
            e.preventDefault();

            const formData = new FormData(e.target);
            const data = {
                N: parseInt(formData.get('N')),
                P: parseInt(formData.get('P')),
                K: parseInt(formData.get('K')),
                ph: parseFloat(formData.get('ph')),
                rainfall: parseFloat(formData.get('rainfall')),
                model_choice: formData.get('model_choice')
            };

            try {
                const response = await fetch('/api/crop-recommendation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                displayCropResults(result);
            } catch (error) {
                console.error('Error:', error);
                alert('Error getting crop recommendation. Please try again.');
            }
        });
    }
    // Nakshatra page handler
    if (document.getElementById('nakshatra-results')) {
        console.log('Nakshatra page loaded');
    }
    if (document.getElementById('city-select')) {
        console.log('Weather page loaded with revised flow');
        initializeWeatherPage();
    }
    if (document.getElementById('org-grid')) {
        console.log('Organizations page loaded');
        fetchOrganizations();
    }
    if (document.getElementById('market-results')) {
        console.log('Market page loaded');
        const form = document.getElementById('market-trend-form');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                const crop = document.getElementById('crop-select').value;
                const city = document.getElementById('city-select').value;
                if (!crop || !city) {
                    const statusEl = document.getElementById('market-status');
                    if (statusEl) {
                        statusEl.style.color = '#e74c3c';
                        statusEl.textContent = 'Please select both crop and city.';
                    }
                    return;
                }
                fetchSpecificMarketTrend(crop, city);
            });
        }
    }
    if (document.getElementById('products-results')) {
        console.log('E-commerce page loaded');
        fetchProducts();

        // Add event listener for add product form
        document.getElementById('add-product-form').addEventListener('submit', async function (e) {
            e.preventDefault();

            // Get logged-in user info from localStorage
            const username = localStorage.getItem('username');
            const role = localStorage.getItem('role') || 'user';

            if (!username) {
                alert('Please login to add a product');
                return;
            }

            const imageInput = document.getElementById('productImages');
            if (imageInput.files.length < 1 || imageInput.files.length > 3) {
                alert('Please upload between 1 and 3 images.');
                return;
            }

            const formData = new FormData();
            formData.append('name', document.getElementById('product-name').value);
            formData.append('price', document.getElementById('product-price').value);
            formData.append('category', document.getElementById('product-category').value);
            formData.append('mode', document.getElementById('product-mode').value);
            formData.append('quantity', document.getElementById('product-quantity').value);
            formData.append('description', document.getElementById('product-description').value);
            formData.append('username', username);
            formData.append('role', role);

            for (let i = 0; i < imageInput.files.length; i++) {
                formData.append('productImages', imageInput.files[i]);
            }

            try {
                const response = await fetch('/api/marketplace/add', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                if (response.ok) {
                    alert(result.message || 'Product added successfully!');
                    this.reset();
                    toggleAddProductForm();
                    fetchProducts();
                } else {
                    alert(result.message || 'Failed to add product');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error adding product. Please try again.');
            }
        });
    }

    // Fertilizer recommendation handler
    const fertBtn = document.getElementById('fertilizer-btn');
    if (fertBtn) {
        fertBtn.addEventListener('click', async function (e) {
            e.preventDefault();

            // Show loading state
            const fertResults = document.getElementById('fertilizer-results');
            fertResults.style.display = 'block';
            fertResults.innerHTML = `
                <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(45, 74, 62, 0.95) 100%); border: 2px solid rgba(74, 124, 89, 0.4); border-radius: 16px; padding: 28px; text-align: center;">
                    <div style="margin-bottom: 15px; color: #98B6FF; font-weight: 700; font-size: 1.2rem;">
                        <span style=\"font-size: 1.5rem;\">⏳</span> Processing your request...
                    </div>
                    <div style="color: #c8e6c9;">Analyzing soil parameters and crop requirements...</div>
                </div>
            `;

            // Get form values
            const soilColor = document.getElementById('soilColor').value.toLowerCase(); // Convert to lowercase
            const nitrogen = parseFloat(document.getElementById('fN').value);
            const phosphorus = parseFloat(document.getElementById('fP').value);
            const potassium = parseFloat(document.getElementById('fK').value);
            const pH = parseFloat(document.getElementById('fpH').value);
            const rainfall = parseFloat(document.getElementById('fRain').value);
            const temperature = parseFloat(document.getElementById('fTemp').value);
            const crop = document.getElementById('fCrop').value.toLowerCase(); // Convert to lowercase

            // Prepare data for API
            const data = {
                "Soil_color": soilColor,
                "Nitrogen": nitrogen,
                "Phosphorus": phosphorus,
                "Potassium": potassium,
                "pH": pH,
                "Rainfall": rainfall,
                "Temperature": temperature,
                "Crop": crop
            };

            try {
                // Call the fertilizer prediction API
                const response = await fetch('/predict', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || 'Error predicting fertilizer');
                }

                const result = await response.json();
                displayFertilizerResults(result);

            } catch (error) {
                console.error('Error:', error);
                fertResults.innerHTML = `
                    <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(45, 74, 62, 0.95) 100%); border: 2px solid rgba(231, 76, 60, 0.4); border-radius: 16px; padding: 28px;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #e74c3c; font-weight: 700; font-size: 1.5rem;">
                            <span style=\"font-size: 1.8rem;\">⚠️</span> Error
                        </div>
                        <div style="color: #e8f5e8; margin-bottom: 8px;">${error.message}</div>
                        <div style="color: #c8e6c9; font-size: 0.9rem;">
                            Please check your inputs and try again. Make sure all values are within acceptable ranges.
                            <br>If the problem persists, the model might not recognize some input values.
                        </div>
                    </div>
                `;
            }
        });
    }

    // Function to display fertilizer prediction results
    function displayFertilizerResults(result) {
        const fertResults = document.getElementById('fertilizer-results');

        fertResults.innerHTML = `
            <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(45, 74, 62, 0.95) 100%); border: 2px solid rgba(74, 124, 89, 0.4); border-radius: 16px; padding: 28px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #98B6FF; font-weight: 700; font-size: 1.5rem;">
                    <span style=\"font-size: 1.8rem;\">🧪</span> Recommended Fertilizer
                </div>
                <div style="font-size: 2rem; color: #B4C9FF; font-weight: 800; margin-bottom: 8px;">${result.predicted_fertilizer}</div>
                <div style="color: #c8e6c9; margin-bottom: 15px;">${result.explanation}</div>
                <div style="color: #6b9c7a; font-size: 0.9rem; border-top: 1px solid rgba(74, 124, 89, 0.3); padding-top: 15px; margin-top: 10px;">
                    Based on ML model analysis of your soil parameters and crop requirements.
                </div>
            </div>
        `;
    }
});

// Nakshatra API caller with validation and error handling
async function getNakshatra() {
    const resultsDiv = document.getElementById('nakshatra-results');
    if (!resultsDiv) return;

    const dateInput = document.getElementById('nakshatra-date');
    const date = dateInput ? dateInput.value : '';

    if (!date) {
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = `
            <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(231, 76, 60, 0.15) 100%); border: 2px solid rgba(231, 76, 60, 0.4); border-radius: 16px; padding: 28px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #e74c3c; font-weight: 700; font-size: 1.2rem;">
                    <span style=\"font-size: 1.5rem;\">⚠️</span> Please select a date
                </div>
                <div style="color: #e8f5e8;">A date in YYYY-MM-DD format is required.</div>
            </div>
        `;
        return;
    }

    // Loading state
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `
        <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(45, 74, 62, 0.95) 100%); border: 2px solid rgba(74, 124, 89, 0.4); border-radius: 16px; padding: 28px; text-align: center;">
            <div style="margin-bottom: 15px; color: #98B6FF; font-weight: 700; font-size: 1.2rem;">
                <span style=\"font-size: 1.5rem;\">⏳</span> Calculating Nakshatra...
            </div>
            <div style="color: #c8e6c9;">Please wait a moment.</div>
        </div>
    `;

    try {
        const response = await fetch('/nakshatra', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date })
        });

        const data = await response.json();

        if (!response.ok) {
            const message = data && data.message ? data.message : 'Unexpected error';
            throw new Error(message);
        }

        const crops = Array.isArray(data.Recommended_Crops) ? data.Recommended_Crops.join(', ') : '';

        resultsDiv.innerHTML = `
            <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(45, 74, 62, 0.95) 100%); border: 2px solid rgba(74, 124, 89, 0.4); border-radius: 16px; padding: 28px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #9FE29F; font-weight: 700; font-size: 1.5rem;">
                    <span style=\"font-size: 1.8rem;\">🌙</span> Nakshatra Result
                </div>
                <div style="font-size: 1.6rem; color: #b6f5b6; font-weight: 700; margin-bottom: 8px;">${data.Nakshatra_Name}</div>
                <div style="color: #c8e6c9; margin-bottom: 12px;">${data.Nakshatra_Details}</div>
                <div style="color: #6b9c7a; margin-bottom: 6px;">Rating: <strong>${data.Rating} / 5</strong></div>
                <div style="color: #c8e6c9;">Recommended Crops: <strong>${crops}</strong></div>
            </div>
        `;
    } catch (error) {
        console.error('Error:', error);
        resultsDiv.innerHTML = `
            <div style="background: linear-gradient(145deg, rgba(26, 26, 26, 0.95) 0%, rgba(231, 76, 60, 0.15) 100%); border: 2px solid rgba(231, 76, 60, 0.4); border-radius: 16px; padding: 28px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #e74c3c; font-weight: 700; font-size: 1.5rem;">
                    <span style=\"font-size: 1.8rem;\">⚠️</span> Error
                </div>
                <div style="color: #e8f5e8;">${error.message}</div>
            </div>
        `;
    }
}

// ============================================================
// TABBED FEATURE SHOWCASE LOGIC
// ============================================================
function initFeatureTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    if (tabBtns.length === 0 || tabContents.length === 0) return;

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // 1. Remove active class from all buttons and panes
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // 2. Add active class to clicked button
            btn.classList.add('active');

            // 3. Find target pane and add active class
            const targetId = btn.getAttribute('data-target');
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });
}

// Initialize tabs when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initFeatureTabs();
});
