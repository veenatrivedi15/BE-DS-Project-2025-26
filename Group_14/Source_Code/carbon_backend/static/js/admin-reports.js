/**
 * Admin Reports JavaScript
 * Handles report generation and export functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initCharts();
    
    // Elements
    const reportForm = document.getElementById('reportForm');
    const dateRangeSelect = document.getElementById('date-range');
    const generateReportBtn = document.getElementById('generateReportBtn');
    const csvExportBtn = document.getElementById('csvExport');
    const reportContent = document.getElementById('report-content');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Stats elements
    const totalUsersElement = document.getElementById('total-users');
    const totalTripsElement = document.getElementById('total-trips');
    const totalCreditsElement = document.getElementById('total-credits');
    const carbonSavedElement = document.getElementById('carbon-saved');
    const avgTripsElement = document.getElementById('avg-trips');
    const redeemedCreditsElement = document.getElementById('redeemed-credits');
    
    // Event listeners
    reportForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const reportType = document.querySelector('.tab.active').dataset.reportType;
        const dateRange = dateRangeSelect.value;
        generateReport(reportType, dateRange);
    });
    
    // Export button event listener
    csvExportBtn.addEventListener('click', function() {
        const reportType = document.querySelector('.tab.active').dataset.reportType;
        const dateRange = dateRangeSelect.value;
        exportReport(reportType, dateRange, 'csv');
    });
    
    // Date range change
    dateRangeSelect.addEventListener('change', function() {
        updateStats(this.value);
        updateCharts(this.value);
    });
    
    // Generate default report on load
    generateReport('summary', '30d');
    
    /**
     * Initialize dashboard charts
     */
    function initCharts() {
        // Transport mode chart
        const transportModeCtx = document.getElementById('transport-mode-chart');
        if (transportModeCtx) {
            window.transportModeChart = new Chart(transportModeCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Car', 'Public Transport', 'Bike', 'Walk', 'Carpool'],
                    datasets: [{
                        data: [30, 25, 20, 15, 10],
                        backgroundColor: [
                            '#ef4444', // red
                            '#0ea5e9', // sky blue
                            '#10b981', // green
                            '#f59e0b', // amber
                            '#8b5cf6'  // purple
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 10,
                                font: {
                                    size: 11
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Credits monthly chart
        const creditsMonthlyCtx = document.getElementById('credits-monthly-chart');
        if (creditsMonthlyCtx) {
            window.creditsMonthlyChart = new Chart(creditsMonthlyCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Credits Earned',
                        data: [1245.25, 1854.50, 2300.75, 2580.30, 3240.85, 3650.40],
                        borderColor: '#0ea5e9',
                        backgroundColor: 'rgba(14, 165, 233, 0.1)',
                        tension: 0.3,
                        fill: true,
                        borderWidth: 2,
                        pointRadius: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.8)',
                            padding: 8,
                            cornerRadius: 4,
                            callbacks: {
                                label: function(context) {
                                    let value = context.raw;
                                    return `Credits: ${formatNumber(value)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                font: {
                                    size: 11
                                },
                                callback: function(value) {
                                    return formatNumber(value);
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                font: {
                                    size: 11
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    
    /**
     * Format number to 2 decimal places and add commas for thousands
     */
    function formatNumber(value) {
        return parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
    
    /**
     * Update charts with new data
     */
    function updateCharts(range) {
        // Simple mock data for different periods
        let creditsData;
        let transportData;
        let labels;
        
        if (range === '7d') {
            labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            creditsData = [150.25, 165.50, 190.30, 210.45, 185.75, 160.20, 145.80];
            transportData = [25, 30, 15, 20, 10];
        } else if (range === '30d') {
            labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
            creditsData = [720.35, 820.50, 940.75, 1050.25];
            transportData = [30, 25, 20, 15, 10];
        } else if (range === '90d') {
            labels = ['Jan', 'Feb', 'Mar'];
            creditsData = [2300.45, 2580.30, 2950.75];
            transportData = [35, 20, 22, 13, 10];
        } else if (range === 'ytd') {
            labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'];
            creditsData = [1245.25, 1854.50, 2300.75, 2580.30, 3240.85, 3650.40, 4120.60];
            transportData = [32, 27, 18, 15, 8];
        } else if (range === 'all') {
            labels = ['Q1', 'Q2', 'Q3', 'Q4', 'Q1', 'Q2', 'Q3', 'Q4'];
            creditsData = [1200.50, 1500.25, 1850.75, 2100.30, 3200.85, 4500.40, 5100.25, 5800.65];
            transportData = [28, 29, 20, 13, 10];
        }
        
        // Update monthly credits chart
        if (window.creditsMonthlyChart) {
            window.creditsMonthlyChart.data.labels = labels;
            window.creditsMonthlyChart.data.datasets[0].data = creditsData;
            window.creditsMonthlyChart.update();
        }
        
        // Update transport chart
        if (window.transportModeChart) {
            window.transportModeChart.data.datasets[0].data = transportData;
            window.transportModeChart.update();
        }
    }
    
    /**
     * Generate a report based on type and date range
     */
    function generateReport(type, range) {
        // Show loading
        loadingIndicator.classList.remove('d-none');
        reportContent.style.opacity = '0.6';
        
        // Update dashboard stats based on selected date range
        updateStats(range);
        
        // Update charts with new data
        updateCharts(range);
        
        // Simulate API fetch (replace with actual API call)
        setTimeout(() => {
            // Hide loading
            loadingIndicator.classList.add('d-none');
            reportContent.style.opacity = '1';
            
            // Generate appropriate report
            switch(type) {
                case 'summary':
                    displaySummaryReport(range);
                    break;
                case 'trips':
                    displayTripsReport(range);
                    break;
                case 'credits':
                    displayCreditsReport(range);
                    break;
                case 'employers':
                    displayEmployersReport(range);
                    break;
                default:
                    displaySummaryReport(range);
            }
        }, 800); // Simulate loading time
    }
    
    /**
     * Update dashboard stats based on date range
     */
    function updateStats(range) {
        // These would normally come from an API
        const stats = {
            '7d': {
                users: 12,
                trips: 18,
                credits: 1245.60,
                carbon: 156.24,
                avgTrips: 2.75,
                redeemed: 854.30,
                trend: '+214.30',
                percent: '8.4%'
            },
            '30d': {
                users: 16,
                trips: 25,
                credits: 2725.85,
                carbon: 312.36,
                avgTrips: 3.57,
                redeemed: 3254.70,
                trend: '+2,345.15',
                percent: '15.3%'
            },
            '90d': {
                users: 23,
                trips: 68,
                credits: 5847.20,
                carbon: 645.75,
                avgTrips: 4.82,
                redeemed: 6254.40,
                trend: '+5,256.40',
                percent: '24.6%'
            },
            'ytd': {
                users: 34,
                trips: 95,
                credits: 8236.40,
                carbon: 923.90,
                avgTrips: 5.46,
                redeemed: 9425.20,
                trend: '+7,850.30',
                percent: '32.2%'
            },
            'all': {
                users: 42,
                trips: 128,
                credits: 15452.60,
                carbon: 1825.80,
                avgTrips: 6.25,
                redeemed: 14625.35,
                trend: '+10,450.25',
                percent: '41.5%'
            }
        };
        
        const currentStats = stats[range] || stats['30d'];
        
        // Update stats with 2 decimal places
        totalUsersElement.textContent = currentStats.users;
        totalTripsElement.textContent = currentStats.trips;
        totalCreditsElement.textContent = formatNumber(currentStats.credits);
        carbonSavedElement.textContent = formatNumber(currentStats.carbon);
        avgTripsElement.textContent = formatNumber(currentStats.avgTrips);
        redeemedCreditsElement.textContent = formatNumber(currentStats.redeemed);
        
        // Update trend indicators
        const tripsTrendElement = document.querySelector('.metric-card:nth-child(2) .metric-trend');
        if (tripsTrendElement) {
            tripsTrendElement.innerHTML = `↑ ${currentStats.percent} from last period`;
        }
        
        const creditsTrendElement = document.querySelector('.metric-card:nth-child(3) .metric-trend');
        if (creditsTrendElement) {
            creditsTrendElement.innerHTML = `↑ ${currentStats.trend} in last ${range === 'all' ? 'period' : (range === 'ytd' ? 'year' : range.replace('d', ' days'))}`;
        }
        
        const redeemedTrendElement = document.querySelector('.metric-card:nth-child(6) .metric-trend');
        if (redeemedTrendElement) {
            redeemedTrendElement.innerHTML = `↑ ${currentStats.percent} utilization rate`;
        }
    }
    
    /**
     * Display summary report
     */
    function displaySummaryReport(range) {
        // This would normally fetch from an API
        reportContent.innerHTML = `
            <h2 class="chart-title">Summary Report - ${getDateRangeText(range)}</h2>
            <p class="mb-4">Overview of platform activity and carbon credit transactions</p>
            
            <div>
                <h3 class="mb-2 text-lg font-medium">User Signups by Role</h3>
                <table class="w-100 table mb-4">
                    <thead class="bg-gray-50">
                        <tr>
                            <th scope="col">User Type</th>
                            <th scope="col" class="text-end">Total Users</th>
                            <th scope="col" class="text-end">Active Users</th>
                            <th scope="col" class="text-end">Completion Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Employees</td>
                            <td class="text-end">12</td>
                            <td class="text-end">10</td>
                            <td class="text-end fw-semibold">83%</td>
                        </tr>
                        <tr>
                            <td>Employers</td>
                            <td class="text-end">4</td>
                            <td class="text-end">4</td>
                            <td class="text-end fw-semibold">100%</td>
                        </tr>
                        <tr>
                            <td>Banks</td>
                            <td class="text-end">2</td>
                            <td class="text-end">2</td>
                            <td class="text-end fw-semibold">100%</td>
                        </tr>
                        <tr>
                            <td>Admins</td>
                            <td class="text-end">2</td>
                            <td class="text-end">2</td>
                            <td class="text-end fw-semibold">100%</td>
                        </tr>
                    </tbody>
                </table>
                
                <h3 class="mb-2 text-lg font-medium">Platform Activity</h3>
                <div style="height: 250px;">
                    <canvas id="activity-chart"></canvas>
                </div>
            </div>
        `;
        
        // Initialize activity chart
        setTimeout(() => {
            const activityCtx = document.getElementById('activity-chart');
            if (activityCtx) {
                new Chart(activityCtx, {
                    type: 'bar',
                    data: {
                        labels: ["Trips Logged", "Credits Earned", "Credits Redeemed", "Credits Transferred"],
                        datasets: [{
                            label: 'Count',
                            backgroundColor: [
                                '#0ea5e9', // sky blue
                                '#10b981', // green
                                '#f59e0b', // amber
                                '#8b5cf6'  // purple
                            ],
                            data: [25, 2725.85, 3254.70, 1425.50],
                            borderRadius: 4,
                            borderWidth: 0
                        }]
                    },
                    options: {
                        maintainAspectRatio: false,
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.05)'
                                },
                                ticks: {
                                    callback: function(value) {
                                        return formatNumber(value);
                                    }
                                }
                            },
                            x: {
                                grid: {
                                    display: false
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        let value = context.raw;
                                        return `${context.label}: ${formatNumber(value)}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
        }, 100);
    }
    
    /**
     * Display trips report
     */
    function displayTripsReport(range) {
        reportContent.innerHTML = `
            <h2 class="chart-title">Trip Analytics - ${getDateRangeText(range)}</h2>
            <p class="mb-4">Detailed analysis of commute trips</p>
            
            <div>
                <h3 class="mb-2 text-lg font-medium">Trip Details</h3>
                <table class="w-100 table mb-4">
                    <thead class="bg-gray-50">
                        <tr>
                            <th scope="col">Transport Mode</th>
                            <th scope="col" class="text-end">Total Trips</th>
                            <th scope="col" class="text-end">Total Distance (km)</th>
                            <th scope="col" class="text-end">Avg Carbon Saved (kg)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Public Transport</td>
                            <td class="text-end">9</td>
                            <td class="text-end">242.50</td>
                            <td class="text-end fw-semibold">15.20</td>
                        </tr>
                        <tr>
                            <td>Electric Vehicle</td>
                            <td class="text-end">5</td>
                            <td class="text-end">125.75</td>
                            <td class="text-end fw-semibold">8.40</td>
                        </tr>
                        <tr>
                            <td>Bicycle</td>
                            <td class="text-end">7</td>
                            <td class="text-end">58.25</td>
                            <td class="text-end fw-semibold">12.50</td>
                        </tr>
                        <tr>
                            <td>Carpool</td>
                            <td class="text-end">4</td>
                            <td class="text-end">85.30</td>
                            <td class="text-end fw-semibold">9.80</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
    }
    
    /**
     * Display credits report
     */
    function displayCreditsReport(range) {
        reportContent.innerHTML = `
            <h2 class="chart-title">Credit Usage - ${getDateRangeText(range)}</h2>
            <p class="mb-4">Analysis of carbon credit earning and usage</p>
            
            <div>
                <h3 class="mb-2 text-lg font-medium">Credit Activity</h3>
                <table class="w-100 table mb-4">
                    <thead class="bg-gray-50">
                        <tr>
                            <th scope="col">Credit Type</th>
                            <th scope="col" class="text-end">Total Credits</th>
                            <th scope="col" class="text-end">% of Total</th>
                            <th scope="col" class="text-end">Avg Value ($)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Earned (From Trips)</td>
                            <td class="text-end">${formatNumber(2725.85)}</td>
                            <td class="text-end">75%</td>
                            <td class="text-end fw-semibold">$12.40</td>
                        </tr>
                        <tr>
                            <td>Traded</td>
                            <td class="text-end">${formatNumber(1254.25)}</td>
                            <td class="text-end">15%</td>
                            <td class="text-end fw-semibold">$13.25</td>
                        </tr>
                        <tr>
                            <td>Redeemed</td>
                            <td class="text-end">${formatNumber(3254.70)}</td>
                            <td class="text-end">38%</td>
                            <td class="text-end fw-semibold">$12.85</td>
                        </tr>
                        <tr>
                            <td>Expired</td>
                            <td class="text-end">${formatNumber(285.40)}</td>
                            <td class="text-end">3%</td>
                            <td class="text-end fw-semibold">$11.95</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
    }
    
    /**
     * Display employers report
     */
    function displayEmployersReport(range) {
        reportContent.innerHTML = `
            <h2 class="chart-title">Employer Comparison - ${getDateRangeText(range)}</h2>
            <p class="mb-4">Compare performance across employers</p>
            
            <div>
                <h3 class="mb-2 text-lg font-medium">Employer Rankings</h3>
                <table class="w-100 table mb-4">
                    <thead class="bg-gray-50">
                        <tr>
                            <th scope="col">Employer</th>
                            <th scope="col" class="text-end">Active Employees</th>
                            <th scope="col" class="text-end">Credits Earned</th>
                            <th scope="col" class="text-end">Participation Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Acme Corporation</td>
                            <td class="text-end">5</td>
                            <td class="text-end">${formatNumber(854.25)}</td>
                            <td class="text-end fw-semibold">92%</td>
                        </tr>
                        <tr>
                            <td>Tech Innovations</td>
                            <td class="text-end">3</td>
                            <td class="text-end">${formatNumber(652.10)}</td>
                            <td class="text-end fw-semibold">85%</td>
                        </tr>
                        <tr>
                            <td>Green Solutions</td>
                            <td class="text-end">2</td>
                            <td class="text-end">${formatNumber(725.35)}</td>
                            <td class="text-end fw-semibold">95%</td>
                        </tr>
                        <tr>
                            <td>Global Enterprises</td>
                            <td class="text-end">4</td>
                            <td class="text-end">${formatNumber(494.15)}</td>
                            <td class="text-end fw-semibold">78%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
    }
    
    /**
     * Get human-readable date range text
     */
    function getDateRangeText(range) {
        switch(range) {
            case '7d':
                return 'Last 7 Days';
            case '30d':
                return 'Last 30 Days';
            case '90d':
                return 'Last 90 Days';
            case 'ytd':
                return 'Year to Date';
            case 'all':
                return 'All Time';
            default:
                return 'Custom Range';
        }
    }
    
    /**
     * Export a report
     */
    function exportReport(type, range, format) {
        // Construct export URL
        const params = new URLSearchParams({
            report_type: type,
            date_range: range,
            format: format
        });
        
        const exportUrl = `/admin/reports/export/?${params.toString()}`;
        
        // For the demo, just alert that export would happen
        alert(`Exporting ${type} report for ${getDateRangeText(range)}`);
        
        // In a real implementation, this would trigger a download
        // window.location.href = exportUrl;
    }
}); 