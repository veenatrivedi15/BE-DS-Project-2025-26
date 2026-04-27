/**
 * Predictive Analytics Frontend for Carbon Credits Platform
 * Handles carbon footprint forecasting, trip pattern analysis, and trend prediction
 */

class PredictiveAnalytics {
    constructor() {
        this.apiBase = '/employee/analytics/api';
        this.charts = {};
        this.currentData = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDashboardData();
        this.initializeCharts();
    }

    setupEventListeners() {
        // Train model button
        document.getElementById('trainModelBtn')?.addEventListener('click', () => {
            this.trainModel();
        });

        // Prediction controls
        document.getElementById('predictionDays')?.addEventListener('change', (e) => {
            this.updatePredictions(parseInt(e.target.value));
        });

        // Refresh data button
        document.getElementById('refreshDataBtn')?.addEventListener('click', () => {
            this.loadDashboardData();
        });

        // Export data button
        document.getElementById('exportDataBtn')?.addEventListener('click', () => {
            this.exportAnalyticsData();
        });

        // Tab navigation
        document.querySelectorAll('[data-analytics-tab]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.analyticsTab);
            });
        });
    }

    async loadDashboardData() {
        try {
            this.showLoading(true);
            
            const response = await fetch(`${this.apiBase}/overview/`);
            const result = await response.json();
            
            if (result.success) {
                this.currentData = result.overview;
                this.updateDashboard();
                this.updateCharts();
                this.updateInsights();
            } else {
                this.showError('Failed to load analytics data: ' + result.error);
            }
        } catch (error) {
            this.showError('Error loading analytics data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    updateDashboard() {
        // Update summary cards
        this.updateSummaryCards();
        
        // Update patterns section
        this.updatePatternsSection();
        
        // Update goals section
        this.updateGoalsSection();
        
        // Update predictions section
        this.updatePredictionsSection();
    }

    updateCharts() {
        const patterns = this.currentData.patterns;
        const predictions = this.currentData.predictions;

        if (patterns?.success) {
            this.updateHourlyPatternChart(patterns.patterns?.hourly || {});
            this.updateTransportAnalysis(patterns.transport_analysis || {});
        }

        if (predictions?.success) {
            this.updatePredictionChart(predictions.predictions || []);
        }
    }

    updateSummaryCards() {
        const patterns = this.currentData.patterns;
        const goals = this.currentData.goals;
        const predictions = this.currentData.predictions;

        if (patterns?.success) {
            document.getElementById('totalTrips').textContent = patterns.total_trips || 0;
            document.getElementById('totalSavings').textContent = `${patterns.total_carbon_savings || 0} kg CO₂`;
            document.getElementById('avgSavingsPerTrip').textContent = `${patterns.average_savings_per_trip || 0} kg CO₂`;
        }

        if (predictions?.success) {
            document.getElementById('predictedWeeklySavings').textContent = `${predictions.total_predicted_savings || 0} kg CO₂`;
        }

        if (goals?.success) {
            const currentProgress = goals.current_savings || 0;
            const predictedTotal = goals.predicted_total || 0;
            document.getElementById('monthlyProgress').textContent = `${currentProgress} kg CO₂`;
            document.getElementById('monthlyPrediction').textContent = `${predictedTotal} kg CO₂`;
        }
    }

    updatePatternsSection() {
        const patterns = this.currentData.patterns;
        if (!patterns?.success) return;

        // Update hourly pattern chart
        this.updateHourlyPatternChart(patterns.patterns?.hourly || {});

        // Update transport mode analysis
        this.updateTransportAnalysis(patterns.transport_analysis || {});

        // Update trend information
        this.updateTrendSection(patterns.trend || {});
    }

    updateGoalsSection() {
        const goals = this.currentData.goals;
        if (!goals?.success) return;

        const goalsContainer = document.getElementById('goalsContainer');
        if (!goalsContainer) return;

        goalsContainer.innerHTML = '';

        goals.goals?.forEach(goal => {
            const goalCard = this.createGoalCard(goal);
            goalsContainer.appendChild(goalCard);
        });
    }

    updatePredictionsSection() {
        const predictions = this.currentData.predictions;
        if (!predictions?.success) return;

        // Update prediction chart
        this.updatePredictionChart(predictions.predictions || []);

        // Update summary
        document.getElementById('predictionSummary').innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-white p-4 rounded-lg border">
                    <div class="text-sm text-gray-500">Total Predicted</div>
                    <div class="text-2xl font-bold text-green-600">${predictions.total_predicted_savings || 0} kg CO₂</div>
                </div>
                <div class="bg-white p-4 rounded-lg border">
                    <div class="text-sm text-gray-500">Daily Average</div>
                    <div class="text-2xl font-bold text-blue-600">${predictions.daily_average || 0} kg CO₂</div>
                </div>
                <div class="bg-white p-4 rounded-lg border">
                    <div class="text-sm text-gray-500">Prediction Period</div>
                    <div class="text-2xl font-bold text-purple-600">${predictions.prediction_period_days || 0} days</div>
                </div>
            </div>
        `;
    }

    updateInsights() {
        const insights = this.currentData.insights;
        if (!insights?.success) return;

        const insightsContainer = document.getElementById('insightsContainer');
        const recommendationsContainer = document.getElementById('recommendationsContainer');

        if (insightsContainer) {
            insightsContainer.innerHTML = '';
            insights.insights?.forEach(insight => {
                const insightCard = this.createInsightCard(insight);
                insightsContainer.appendChild(insightCard);
            });
        }

        if (recommendationsContainer) {
            recommendationsContainer.innerHTML = '';
            insights.recommendations?.forEach(recommendation => {
                const recommendationCard = this.createRecommendationCard(recommendation);
                recommendationsContainer.appendChild(recommendationCard);
            });
        }
    }

    createGoalCard(goal) {
        const card = document.createElement('div');
        card.className = `bg-white p-4 rounded-lg border ${goal.on_track ? 'border-green-200' : 'border-red-200'}`;
        
        const percentage = Math.min(goal.percentage_achieved, 100);
        const progressColor = goal.on_track ? 'bg-green-500' : 'bg-red-500';

        card.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <h4 class="font-semibold">${goal.target_kg} kg CO₂ Goal</h4>
                <span class="text-sm px-2 py-1 rounded ${goal.on_track ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                    ${goal.on_track ? 'On Track' : 'At Risk'}
                </span>
            </div>
            <div class="mb-2">
                <div class="flex justify-between text-sm text-gray-600 mb-1">
                    <span>Progress: ${goal.current_progress} kg</span>
                    <span>${percentage.toFixed(1)}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="${progressColor} h-2 rounded-full transition-all duration-300" style="width: ${percentage}%"></div>
                </div>
            </div>
            <div class="text-sm text-gray-600">
                Predicted: ${goal.predicted_total} kg (${goal.confidence} confidence)
            </div>
        `;

        return card;
    }

    createInsightCard(insight) {
        const card = document.createElement('div');
        card.className = 'bg-white p-4 rounded-lg border border-blue-200';
        
        const priorityColors = {
            high: 'text-red-600',
            medium: 'text-yellow-600',
            low: 'text-green-600'
        };

        card.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <svg class="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                            <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                </div>
                <div class="ml-3 flex-1">
                    <h4 class="font-semibold text-gray-900">${insight.title}</h4>
                    <p class="text-sm text-gray-600 mt-1">${insight.description}</p>
                    <span class="text-xs ${priorityColors[insight.priority]} mt-2 inline-block">
                        ${insight.priority} priority
                    </span>
                </div>
            </div>
        `;

        return card;
    }

    createRecommendationCard(recommendation) {
        const card = document.createElement('div');
        card.className = 'bg-white p-4 rounded-lg border border-green-200';
        
        const priorityColors = {
            high: 'text-red-600',
            medium: 'text-yellow-600',
            low: 'text-green-600'
        };

        card.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <svg class="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                </div>
                <div class="ml-3 flex-1">
                    <h4 class="font-semibold text-gray-900">${recommendation.title}</h4>
                    <p class="text-sm text-gray-600 mt-1">${recommendation.description}</p>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-xs ${priorityColors[recommendation.priority]}">
                            ${recommendation.priority} priority
                        </span>
                        ${recommendation.actionable ? '<span class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Actionable</span>' : ''}
                    </div>
                </div>
            </div>
        `;

        return card;
    }

    initializeCharts() {
        // Initialize Chart.js charts
        this.initializeHourlyPatternChart();
        this.initializePredictionChart();
        this.initializeTransportAnalysisChart();
    }

    initializeHourlyPatternChart() {
        const ctx = document.getElementById('hourlyPatternChart');
        if (!ctx) return;

        this.charts.hourlyPattern = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 24}, (_, i) => `${i}:00`),
                datasets: [{
                    label: 'Average Carbon Savings (kg CO₂)',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Hourly Carbon Savings Pattern'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'kg CO₂'
                        }
                    }
                }
            }
        });
    }

    initializePredictionChart() {
        const ctx = document.getElementById('predictionChart');
        if (!ctx) return;

        this.charts.prediction = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Predicted Carbon Savings (kg CO₂)',
                    data: [],
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderColor: 'rgb(34, 197, 94)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Carbon Savings Prediction'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'kg CO₂'
                        }
                    }
                }
            }
        });
    }

    initializeTransportAnalysisChart() {
        const ctx = document.getElementById('transportAnalysisChart');
        if (!ctx) return;

        this.charts.transportAnalysis = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(34, 197, 94, 0.8)',
                        'rgba(251, 146, 60, 0.8)',
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(147, 51, 234, 0.8)',
                        'rgba(236, 72, 153, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Transport Mode Analysis'
                    }
                }
            }
        });
    }

    updateHourlyPatternChart(hourlyData) {
        if (!this.charts.hourlyPattern) return;

        const labels = Object.keys(hourlyData || {}).sort((a, b) => parseInt(a) - parseInt(b));
        const data = labels.map(hour => hourlyData[hour] ?? 0);

        this.charts.hourlyPattern.data.labels = labels.map(hour => `${hour}:00`);
        this.charts.hourlyPattern.data.datasets[0].data = data;
        this.charts.hourlyPattern.update();
    }

    updatePredictionChart(predictions) {
        if (!this.charts.prediction) return;

        const labels = predictions.map(p => new Date(p.date).toLocaleDateString());
        const data = predictions.map(p => p.predicted_savings);

        this.charts.prediction.data.labels = labels;
        this.charts.prediction.data.datasets[0].data = data;
        this.charts.prediction.update();
    }

    updateTransportAnalysis(transportData) {
        if (!this.charts.transportAnalysis) return;

        const labels = Object.keys(transportData || {});
        const data = labels.map(mode => {
            const metrics = transportData[mode] || {};
            const mean = metrics.carbon_savings?.mean;
            return mean ?? 0;
        });

        this.charts.transportAnalysis.data.labels = labels;
        this.charts.transportAnalysis.data.datasets[0].data = data;
        this.charts.transportAnalysis.update();
    }

    async trainModel() {
        try {
            this.showLoading(true);
            
            const response = await fetch(`${this.apiBase}/train-model/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Model trained successfully!');
                this.loadDashboardData(); // Reload data with new predictions
            } else {
                this.showError('Failed to train model: ' + result.error);
            }
        } catch (error) {
            this.showError('Error training model: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async updatePredictions(days) {
        try {
            const response = await fetch(`${this.apiBase}/predict-savings/?days=${days}`);
            const result = await response.json();
            
            if (result.success) {
                this.currentData.predictions = result;
                this.updatePredictionsSection();
                this.updatePredictionChart(result.predictions || []);
            } else {
                this.showError('Failed to update predictions: ' + result.error);
            }
        } catch (error) {
            this.showError('Error updating predictions: ' + error.message);
        }
    }

    switchTab(tabName) {
        // Hide all tab contents
        document.querySelectorAll('[data-analytics-content]').forEach(content => {
            content.classList.add('hidden');
        });

        // Show selected tab content
        const selectedContent = document.querySelector(`[data-analytics-content="${tabName}"]`);
        if (selectedContent) {
            selectedContent.classList.remove('hidden');
        }

        // Update tab buttons
        document.querySelectorAll('[data-analytics-tab]').forEach(tab => {
            tab.classList.remove('bg-blue-500', 'text-white');
            tab.classList.add('bg-gray-200', 'text-gray-700');
        });

        const selectedTab = document.querySelector(`[data-analytics-tab="${tabName}"]`);
        if (selectedTab) {
            selectedTab.classList.remove('bg-gray-200', 'text-gray-700');
            selectedTab.classList.add('bg-blue-500', 'text-white');
        }
    }

    exportAnalyticsData() {
        const dataStr = JSON.stringify(this.currentData, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `carbon-analytics-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    showLoading(show) {
        const loadingElement = document.getElementById('analyticsLoading');
        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
        }
    }

    showError(message) {
        const errorElement = document.getElementById('analyticsError');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            setTimeout(() => {
                errorElement.style.display = 'none';
            }, 5000);
        }
    }

    showSuccess(message) {
        const successElement = document.getElementById('analyticsSuccess');
        if (successElement) {
            successElement.textContent = message;
            successElement.style.display = 'block';
            setTimeout(() => {
                successElement.style.display = 'none';
            }, 3000);
        }
    }

    getCSRFToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    updateTrendSection(trend) {
        const trendElement = document.getElementById('trendSection');
        if (!trendElement) return;

        const trendColors = {
            increasing: 'text-green-600',
            decreasing: 'text-red-600',
            stable: 'text-blue-600'
        };

        const trendIcons = {
            increasing: '↑',
            decreasing: '↓',
            stable: '→'
        };

        trendElement.innerHTML = `
            <div class="bg-white p-4 rounded-lg border">
                <h4 class="font-semibold mb-2">Weekly Trend</h4>
                <div class="flex items-center">
                    <span class="text-2xl mr-2 ${trendColors[trend.direction]}">${trendIcons[trend.direction]}</span>
                    <div>
                        <div class="font-medium ${trendColors[trend.direction]}">${trend.direction.charAt(0).toUpperCase() + trend.direction.slice(1)}</div>
                        <div class="text-sm text-gray-600">${trend.percentage_change?.toFixed(1) || 0}% change</div>
                    </div>
                </div>
            </div>
        `;
    }
}

// Initialize the predictive analytics when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('predictiveAnalyticsDashboard')) {
        window.predictiveAnalytics = new PredictiveAnalytics();
    }
});
