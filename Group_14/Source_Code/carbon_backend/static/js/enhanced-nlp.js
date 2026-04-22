/**
 * Enhanced NLP Frontend for Advanced Sustainability Insights
 * Handles natural language queries, carbon insights, and personalized tips
 */

class EnhancedNLPManager {
    constructor() {
        this.apiBaseUrl = '/nlp/api/';
        this.queryHistory = [];
        this.currentInsights = null;
        this.isProcessing = false;
    }

    // Initialize the NLP interface
    init() {
        this.setupEventListeners();
        this.loadCarbonInsights();
        this.loadSustainabilityTips();
        console.log('Enhanced NLP Manager initialized');
    }

    // Setup event listeners
    setupEventListeners() {
        // Query input handling
        const queryInput = document.getElementById('nlp-query-input');
        const submitButton = document.getElementById('nlp-submit-btn');
        
        if (queryInput && submitButton) {
            submitButton.addEventListener('click', () => this.processQuery());
            queryInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.processQuery();
                }
            });
        }

        // Quick action buttons
        this.setupQuickActions();
    }

    // Setup quick action buttons
    setupQuickActions() {
        const quickActions = [
            { text: 'How much CO₂ did I save this week?', icon: '📊' },
            { text: 'What\'s my carbon footprint this month?', icon: '🌍' },
            { text: 'Compare my savings to planting trees', icon: '🌳' },
            { text: 'How many factory hours did I offset?', icon: '🏭' },
            { text: 'Predict my next month\'s impact', icon: '🔮' },
            { text: 'Give me eco-friendly tips', icon: '💡' }
        ];

        const container = document.getElementById('quick-actions');
        if (container) {
            container.innerHTML = quickActions.map(action => `
                <button class="quick-action-btn" onclick="nlpManager.setQuery('${action.text}')">
                    <span class="action-icon">${action.icon}</span>
                    <span class="action-text">${action.text}</span>
                </button>
            `).join('');
        }
    }

    // Set query from quick action
    setQuery(query) {
        const input = document.getElementById('nlp-query-input');
        if (input) {
            input.value = query;
            this.processQuery();
        }
    }

    // Process NLP query
    async processQuery() {
        const queryInput = document.getElementById('nlp-query-input');
        const query = queryInput?.value?.trim();
        
        if (!query || this.isProcessing) return;

        this.isProcessing = true;
        this.showLoading();

        try {
            const response = await fetch(`${this.apiBaseUrl}process-query/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({ query })
            });

            const result = await response.json();
            
            if (result.success) {
                this.displayResponse(result.response);
                this.addToHistory(query, result.response);
                this.updateInsights(result.data);
            } else {
                this.displayError(result.error || 'Failed to process query');
            }

        } catch (error) {
            console.error('NLP Query Error:', error);
            this.displayError('Network error. Please try again.');
        } finally {
            this.isProcessing = false;
            this.hideLoading();
        }
    }

    // Load carbon insights
    async loadCarbonInsights() {
        try {
            const response = await fetch(`${this.apiBaseUrl}carbon-insights/`);
            const result = await response.json();
            
            if (result.success) {
                this.currentInsights = result.insights;
                this.displayInsights(result.insights);
            }
        } catch (error) {
            console.error('Failed to load carbon insights:', error);
        }
    }

    // Load sustainability tips
    async loadSustainabilityTips() {
        try {
            const response = await fetch(`${this.apiBaseUrl}sustainability-tips/`);
            const result = await response.json();
            
            if (result.success) {
                this.displayTips(result.tips);
            }
        } catch (error) {
            console.error('Failed to load sustainability tips:', error);
        }
    }

    // Display NLP response
    displayResponse(response) {
        const responseContainer = document.getElementById('nlp-response');
        if (responseContainer) {
            responseContainer.innerHTML = `
                <div class="nlp-response-card">
                    <div class="response-content">
                        ${this.formatResponse(response)}
                    </div>
                    <div class="response-actions">
                        <button class="action-btn secondary" onclick="nlpManager.shareResponse()">
                            📤 Share Impact
                        </button>
                        <button class="action-btn primary" onclick="nlpManager.saveInsight()">
                            💾 Save Insight
                        </button>
                    </div>
                </div>
            `;
            responseContainer.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Format response with markdown-like styling
    formatResponse(response) {
        return response
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>')
            .replace(/🌟/g, '<span class="emoji-highlight">🌟</span>')
            .replace(/🌱/g, '<span class="emoji-highlight">🌱</span>')
            .replace(/🌍/g, '<span class="emoji-highlight">🌍</span>')
            .replace(/🏭/g, '<span class="emoji-highlight">🏭</span>')
            .replace(/🌳/g, '<span class="emoji-highlight">🌳</span>')
            .replace(/📊/g, '<span class="emoji-highlight">📊</span>')
            .replace(/💚/g, '<span class="emoji-green">💚</span>');
    }

    // Display carbon insights
    displayInsights(insights) {
        const container = document.getElementById('carbon-insights');
        if (!container) return;

        const current = insights.current_month;
        const impact = insights.environmental_impact;

        container.innerHTML = `
            <div class="insights-grid">
                <div class="insight-card primary">
                    <h3>📊 This Month's Impact</h3>
                    <div class="insight-metrics">
                        <div class="metric">
                            <span class="value">${current.savings_kg.toFixed(1)}</span>
                            <span class="label">kg CO₂ Saved</span>
                        </div>
                        <div class="metric">
                            <span class="value">${current.trips_count}</span>
                            <span class="label">Eco Trips</span>
                        </div>
                        <div class="metric">
                            <span class="value">${current.credits_earned}</span>
                            <span class="label">Credits Earned</span>
                        </div>
                    </div>
                </div>

                <div class="insight-card secondary">
                    <h3>🌳 Environmental Equivalents</h3>
                    <div class="equivalents">
                        <div class="equivalent-item">
                            <span class="equivalent-icon">🌳</span>
                            <div class="equivalent-text">
                                <strong>${impact.trees_planted.toFixed(1)}</strong> trees planted
                            </div>
                        </div>
                        <div class="equivalent-item">
                            <span class="equivalent-icon">🏭</span>
                            <div class="equivalent-text">
                                <strong>${impact.factory_hours_offset.toFixed(1)}</strong> factory hours offset
                            </div>
                        </div>
                        <div class="equivalent-item">
                            <span class="equivalent-icon">🚗</span>
                            <div class="equivalent-text">
                                <strong>${impact.cars_off_road.toFixed(1)}</strong> cars off road
                            </div>
                        </div>
                    </div>
                </div>

                <div class="insight-card tertiary">
                    <h3>📈 Weekly Average</h3>
                    <div class="weekly-stats">
                        <div class="stat">
                            <span class="stat-value">${insights.weekly_average.savings_kg.toFixed(1)} kg</span>
                            <span class="stat-label">CO₂ per week</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${insights.weekly_average.trips_count}</span>
                            <span class="stat-label">Trips per week</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Display sustainability tips
    displayTips(tips) {
        const container = document.getElementById('sustainability-tips');
        if (!container) return;

        container.innerHTML = `
            <div class="tips-container">
                <h3>💡 Personalized Eco-Tips</h3>
                <div class="tips-grid">
                    ${tips.map(tip => `
                        <div class="tip-card priority-${tip.priority}">
                            <div class="tip-header">
                                <span class="tip-icon">${tip.icon}</span>
                                <h4>${tip.title}</h4>
                            </div>
                            <p class="tip-description">${tip.description}</p>
                            <div class="tip-actions">
                                <button class="tip-action" onclick="nlpManager.acceptTip('${tip.type}')">
                                    ✓ Got it!
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Display error message
    displayError(message) {
        const responseContainer = document.getElementById('nlp-response');
        if (responseContainer) {
            responseContainer.innerHTML = `
                <div class="error-card">
                    <div class="error-icon">⚠️</div>
                    <div class="error-message">${message}</div>
                </div>
            `;
        }
    }

    // Show loading state
    showLoading() {
        const submitBtn = document.getElementById('nlp-submit-btn');
        if (submitBtn) {
            submitBtn.innerHTML = '🤔 Thinking...';
            submitBtn.disabled = true;
        }
    }

    // Hide loading state
    hideLoading() {
        const submitBtn = document.getElementById('nlp-submit-btn');
        if (submitBtn) {
            submitBtn.innerHTML = '🚀 Ask';
            submitBtn.disabled = false;
        }
    }

    // Add to query history
    addToHistory(query, response) {
        this.queryHistory.unshift({ query, response, timestamp: new Date() });
        if (this.queryHistory.length > 10) {
            this.queryHistory.pop();
        }
        this.updateHistoryDisplay();
    }

    // Update history display
    updateHistoryDisplay() {
        const historyContainer = document.getElementById('query-history');
        if (!historyContainer) return;

        historyContainer.innerHTML = `
            <h4>Recent Queries</h4>
            <div class="history-list">
                ${this.queryHistory.slice(0, 5).map(item => `
                    <div class="history-item" onclick="nlpManager.setQuery('${item.query}')">
                        <div class="history-query">${item.query}</div>
                        <div class="history-time">${this.formatTime(item.timestamp)}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // Update insights data
    updateInsights(data) {
        // Trigger dashboard updates if insights container exists
        const event = new CustomEvent('insightsUpdated', { detail: data });
        document.dispatchEvent(event);
    }

    // Share response
    shareResponse() {
        const responseText = document.querySelector('.response-content')?.textContent;
        if (responseText) {
            this.logSocialEngagement('share_impact', 'Shared your sustainability insights.')
            if (navigator.share) {
                navigator.share({
                    title: 'My Carbon Impact',
                    text: responseText
                });
            } else {
                navigator.clipboard.writeText(responseText);
                this.showNotification('Response copied to clipboard!');
            }
        }
    }

    // Save insight
    saveInsight() {
        this.showNotification('Insight saved to your profile!');
    }

    // Accept tip
    acceptTip(tipType) {
        this.logSocialEngagement('accept_tip', `Accepted a sustainability tip for ${tipType}.`);
        this.showNotification(`Great! You're working on ${tipType} improvement!`);
    }

    // Log awareness & motivation actions
    async logSocialEngagement(action, context, link = '') {
        try {
            await fetch('/api/notifications/social-engagement/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({ action, context, link })
            });
        } catch (error) {
            console.error('Social engagement log failed:', error);
        }
    }

    // Show notification
    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Format time
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return `${days}d ago`;
    }

    // Get CSRF token
    getCookie(name) {
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
}

// Initialize the NLP manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.nlpManager = new EnhancedNLPManager();
    window.nlpManager.init();
});
