/**
 * Carbon Credits Calculation Engine (Frontend)
 * Based on WRI 2015 + IPCC 2006 formulas
 * 
 * Formula: CC = (EF_baseline - EF_actual) × Distance × Time_Weight × Context_Factor
 */

// Emission factors (WRI India 2015)
if (typeof EMISSION_FACTORS === 'undefined') {
    window.EMISSION_FACTORS = {
        'car': { baseline: 0.130, actual: 0.130 },
        'carpool': { baseline: 0.130, actual: 0.071 },
        'two_wheeler_single': { baseline: 0.130, actual: 0.029 },
        'two_wheeler_double': { baseline: 0.130, actual: 0.0145 },
        'public_transport': { baseline: 0.130, actual: 0.015161 },
        'bicycle': { baseline: 0.120, actual: 0.000 },
        'walking': { baseline: 0.150, actual: 0.000 },
        'work_from_home': { baseline: 0.130, actual: 0.000 }
    };
}

// Peak factors (IPCC-based)
if (typeof PEAK_FACTORS === 'undefined') {
    window.PEAK_FACTORS = {
        'peak_morning': 1.2,
        'peak_evening': 1.2,
        'off_peak': 1.0,
        'late_night': 0.8
    };
}

// Traffic multipliers (UNFCCC 2004)
if (typeof TRAFFIC_MULTIPLIERS === 'undefined') {
    window.TRAFFIC_MULTIPLIERS = {
        'heavy': 1.3,
        'moderate': 1.1,
        'light': 1.0
    };
}

// Weather factors (CRRI India)
const WEATHER_FACTORS = {
    'heavy_rain': 1.2,
    'light_rain': 1.1,
    'normal': 1.0,
    'favorable': 0.95
};

// Route factors (IPCC-based)
const ROUTE_FACTORS = {
    'hilly': 1.3,
    'city_center': 1.2,
    'suburban': 1.0,
    'highway': 0.9
};

// AQI factors (Clean Air Asia standards)
const AQI_FACTORS = {
    'hazardous': 1.2,
    'very_poor': 1.1,
    'moderate': 1.0,
    'good': 0.95
};

// Seasonal factors (India-specific)
const SEASONAL_FACTORS = {
    'winter': 0.95,
    'summer': 1.1,
    'monsoon': 1.2,
    'post_monsoon': 1.0
};

/**
 * Select transport mode and show calculation parameters
 */
function selectTransportMode(mode) {
    // Remove selected class from all options
    document.querySelectorAll('.transport-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // Add selected class to clicked option
    const selectedOption = document.querySelector(`[data-mode="${mode}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
    }
    
    // Set transport mode value
    const transportInput = document.getElementById('transport-mode');
    if (transportInput) {
        transportInput.value = mode;
    }
    
    // Show/hide calculation parameters
    const paramsSection = document.getElementById('calculation-params');
    if (mode === 'work_from_home') {
        if (paramsSection) paramsSection.classList.add('hidden');
        const mapSection = document.getElementById('map-section');
        if (mapSection) mapSection.style.display = 'none';
        const distanceInput = document.getElementById('distance-km');
        if (distanceInput) distanceInput.value = '0';
    } else {
        if (paramsSection) paramsSection.classList.remove('hidden');
        const mapSection = document.getElementById('map-section');
        if (mapSection) mapSection.style.display = 'block';
    }
    
    // Update credit preview
    updateCreditPreview();
    
    // Update credit display for each mode
    updateModeCredits();
}

/**
 * Calculate time weight: Peak_Factor × Traffic_Multiplier
 */
function calculateTimeWeight(timePeriod, trafficCondition) {
    const peakFactor = PEAK_FACTORS[timePeriod] || 1.0;
    const trafficMultiplier = TRAFFIC_MULTIPLIERS[trafficCondition] || 1.0;
    return peakFactor * trafficMultiplier;
}

/**
 * Calculate context factor: Weather × Route × AQI × Seasonal
 */
function calculateContextFactor(weather, routeType, aqiLevel, season, mode) {
    const weatherFactor = WEATHER_FACTORS[weather] || 1.0;
    const routeFactor = ROUTE_FACTORS[routeType] || 1.0;
    const aqiFactor = AQI_FACTORS[aqiLevel] || 1.0;
    const seasonalFactor = SEASONAL_FACTORS[season] || 1.0;
    const loadFactor = mode === 'two_wheeler_double' ? 1.02 : (mode === 'two_wheeler_single' ? 0.95 : 1.0);
    return weatherFactor * routeFactor * aqiFactor * seasonalFactor * loadFactor;
}

/**
 * Calculate carbon credits using the formula
 * CC = (EF_baseline - EF_actual) × Distance × Time_Weight × Context_Factor
 */
function calculateCredits(mode, distance, timePeriod, trafficCondition, weather, routeType, aqiLevel, season) {
    if (mode === 'work_from_home') {
        return 10.0; // Fixed credits for WFH
    }
    
    const factors = window.EMISSION_FACTORS[mode] || { baseline: 0.130, actual: 0.130 };
    const emissionDiff = factors.baseline - factors.actual;
    const timeWeight = calculateTimeWeight(timePeriod, trafficCondition);
    const contextFactor = calculateContextFactor(weather, routeType, aqiLevel, season, mode);
    
    const credits = emissionDiff * distance * timeWeight * contextFactor;
    return Math.max(0, credits);
}

/**
 * Update real-time credit preview
 */
function updateCreditPreview() {
    const mode = document.getElementById('transport-mode')?.value;
    const distanceInput = document.getElementById('distance-km');
    const distance = distanceInput ? parseFloat(distanceInput.value) || 0 : 0;
    
    if (!mode || mode === 'work_from_home') {
        if (mode === 'work_from_home') {
            const previewCredits = document.getElementById('preview-credits');
            const previewSavings = document.getElementById('preview-savings');
            const previewTimeWeight = document.getElementById('preview-time-weight');
            const previewContext = document.getElementById('preview-context');
            const previewDistance = document.getElementById('preview-distance');
            if (previewCredits) previewCredits.textContent = '10.00';
            if (previewSavings) previewSavings.textContent = 'N/A';
            if (previewTimeWeight) previewTimeWeight.textContent = '1.0x';
            if (previewContext) previewContext.textContent = '1.0x';
            if (previewDistance) previewDistance.textContent = '0 km';
        }
        return;
    }
    
    const timePeriod = document.getElementById('time_period')?.value || 'off_peak';
    const trafficCondition = document.getElementById('traffic_condition')?.value || 'moderate';
    const weather = document.getElementById('weather_condition')?.value || 'normal';
    const routeType = document.getElementById('route_type')?.value || 'suburban';
    const aqiLevel = document.getElementById('aqi_level')?.value || 'moderate';
    const season = document.getElementById('season')?.value || 'normal';
    
    const factors = window.EMISSION_FACTORS[mode] || { baseline: 0.130, actual: 0.130 };
    const emissionDiff = factors.baseline - factors.actual;
    const timeWeight = calculateTimeWeight(timePeriod, trafficCondition);
    const contextFactor = calculateContextFactor(weather, routeType, aqiLevel, season, mode);
    const credits = calculateCredits(mode, distance, timePeriod, trafficCondition, weather, routeType, aqiLevel, season);
    
    // Update preview
    const previewCredits = document.getElementById('preview-credits');
    const previewSavings = document.getElementById('preview-savings');
    const previewTimeWeight = document.getElementById('preview-time-weight');
    const previewContext = document.getElementById('preview-context');
    const previewDistance = document.getElementById('preview-distance');
    
    if (previewCredits) previewCredits.textContent = credits.toFixed(2);
    if (previewSavings) previewSavings.textContent = emissionDiff.toFixed(4) + ' kg/km';
    if (previewTimeWeight) previewTimeWeight.textContent = timeWeight.toFixed(2) + 'x';
    if (previewContext) previewContext.textContent = contextFactor.toFixed(2) + 'x';
    if (previewDistance) previewDistance.textContent = distance.toFixed(1) + ' km';
}

/**
 * Update credit display for each transport mode (example for 1 km)
 */
function updateModeCredits() {
    Object.keys(window.EMISSION_FACTORS).forEach(mode => {
        const creditElement = document.getElementById(`credits-${mode}`);
        if (creditElement && mode !== 'work_from_home') {
            const defaultTimePeriod = 'off_peak';
            const defaultTraffic = 'moderate';
            const defaultWeather = 'normal';
            const defaultRoute = 'suburban';
            const defaultAQI = 'moderate';
            const defaultSeason = 'normal';
            const exampleDistance = 1.0; // 1 km example
            
            const credits = calculateCredits(mode, exampleDistance, defaultTimePeriod, defaultTraffic, defaultWeather, defaultRoute, defaultAQI, defaultSeason);
            creditElement.textContent = `~${credits.toFixed(2)} kg CO₂/km`;
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Carbon calculation engine initialized');
    
    // Initialize credit displays
    updateModeCredits();
    
    // Add event listeners for distance changes
    const distanceInput = document.getElementById('distance-km');
    if (distanceInput) {
        distanceInput.addEventListener('input', updateCreditPreview);
        distanceInput.addEventListener('change', updateCreditPreview);
    }
    
    // Backup click handlers for transport options
    document.querySelectorAll('.transport-option').forEach(option => {
        option.addEventListener('click', function() {
            const mode = this.getAttribute('data-mode');
            if (mode) {
                selectTransportMode(mode);
            }
        });
    });
});


