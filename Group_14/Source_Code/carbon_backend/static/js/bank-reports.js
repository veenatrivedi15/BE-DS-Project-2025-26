/**
 * Bank Reports JavaScript
 * Handles report generation and export functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initCharts();
    
    // Elements
    const reportForm = document.getElementById('reportForm');
    const dateRangeSelect = document.getElementById('date_range');
    const generateReportBtn = document.getElementById('generateReportBtn');
    const csvExportBtn = document.getElementById('csvExport');
    const reportContent = document.getElementById('reportContent');
    const loadingIndicator = document.getElementById('loadingIndicator');
    
    // Stats elements
    const totalUsersElement = document.getElementById('total-users');
    const totalTripsElement = document.getElementById('total-trips');
    const totalCreditsElement = document.getElementById('total-credits');
    const carbonSavedElement = document.getElementById('carbon-saved');
    
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
        // Credits trend chart
        const creditsTrendCtx = document.getElementById('creditsTrendChart');
        if (creditsTrendCtx) {
            window.creditsTrendChart = new Chart(creditsTrendCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                    datasets: [{
                        label: 'Credits Generated',
                        data: [1245, 1854, 1600, 2105, 2400, 2800, 2725],
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderColor: '#0ea5e9',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
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
                            cornerRadius: 4
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
        
        // Transport mode chart
        const transportModeCtx = document.getElementById('transportModeChart');
        if (transportModeCtx) {
            window.transportModeChart = new Chart(transportModeCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Public Transit', 'Electric Vehicle', 'Carpool', 'Bicycle', 'Walking'],
                    datasets: [{
                        data: [35, 25, 15, 20, 5],
                        backgroundColor: [
                            '#0ea5e9', // sky blue
                            '#10b981', // green
                            '#8b5cf6', // purple
                            '#f59e0b', // amber
                            '#ef4444'  // red
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
            creditsData = [142, 165, 159, 180, 181, 156, 140];
            transportData = [32, 28, 15, 20, 5];
        } else if (range === '30d') {
            labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
            creditsData = [680, 790, 820, 910];
            transportData = [35, 25, 15, 20, 5];
        } else if (range === '90d') {
            labels = ['Jan', 'Feb', 'Mar'];
            creditsData = [1845, 2103, 2540];
            transportData = [40, 20, 18, 17, 5];
        } else if (range === '1y') {
            labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            creditsData = [1245, 1854, 1600, 2105, 2400, 2800, 2725, 3105, 3450, 3680, 4020, 4350];
            transportData = [38, 27, 14, 16, 5];
        }
        
        // Update credits chart
        if (window.creditsTrendChart) {
            window.creditsTrendChart.data.labels = labels;
            window.creditsTrendChart.data.datasets[0].data = creditsData;
            window.creditsTrendChart.update();
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
                case 'transactions':
                    displayTransactionReport(range);
                    break;
                case 'price':
                    displayPriceReport(range);
                    break;
                case 'employer':
                    displayEmployerActivityReport(range);
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
                credits: '1,245.60',
                carbon: '156.24',
                trend: '+214.30',
                percent: '8.4%'
            },
            '30d': {
                users: 16,
                trips: 42,
                credits: '2,725.85',
                carbon: '312.36',
                trend: '+1,482.15',
                percent: '12.7%'
            },
            '90d': {
                users: 23,
                trips: 103,
                credits: '5,847.20',
                carbon: '645.75',
                trend: '+3,256.40',
                percent: '21.4%'
            },
            '1y': {
                users: 34,
                trips: 438,
                credits: '15,236.40',
                carbon: '1,723.90',
                trend: '+8,752.60',
                percent: '35.2%'
            }
        };
        
        const currentStats = stats[range] || stats['30d'];
        
        // Update stats
        totalUsersElement.textContent = currentStats.users;
        totalTripsElement.textContent = currentStats.trips;
        totalCreditsElement.textContent = currentStats.credits;
        carbonSavedElement.textContent = currentStats.carbon;
        
        // Update trend indicators
        const transactionsTrendElement = document.querySelector('.metric-card:nth-child(2) .metric-trend');
        if (transactionsTrendElement) {
            transactionsTrendElement.innerHTML = `↑ ${currentStats.percent} from last period`;
        }
        
        const creditsTrendElement = document.querySelector('.metric-card:nth-child(3) .metric-trend');
        if (creditsTrendElement) {
            creditsTrendElement.innerHTML = `↑ ${currentStats.trend} in last ${range === '1y' ? 'year' : range.replace('d', ' days')}`;
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
                <h3 class="mb-2 text-lg font-medium">Credit Distribution</h3>
                <table class="w-100 table mb-4">
                    <thead class="bg-gray-50">
                        <tr>
                            <th scope="col">Employer</th>
                            <th scope="col" class="text-end">Credits Earned</th>
                            <th scope="col" class="text-end">Credits Used</th>
                            <th scope="col" class="text-end">Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Acme Corporation</td>
                            <td class="text-end">854.25</td>
                            <td class="text-end">325.50</td>
                            <td class="text-end fw-semibold">528.75</td>
                        </tr>
                        <tr>
                            <td>Tech Innovations</td>
                            <td class="text-end">652.10</td>
                            <td class="text-end">210.80</td>
                            <td class="text-end fw-semibold">441.30</td>
                        </tr>
                        <tr>
                            <td>Green Solutions</td>
                            <td class="text-end">725.35</td>
                            <td class="text-end">415.20</td>
                            <td class="text-end fw-semibold">310.15</td>
                        </tr>
                        <tr>
                            <td>Global Enterprises</td>
                            <td class="text-end">494.15</td>
                            <td class="text-end">115.75</td>
                            <td class="text-end fw-semibold">378.40</td>
                        </tr>
                    </tbody>
                </table>
                
                <h3 class="mb-2 text-lg font-medium">Credit Activity</h3>
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
                        labels: ["Earned", "Used", "Expired", "Transferred"],
                        datasets: [{
                            label: 'Credits',
                            backgroundColor: [
                                '#0ea5e9', // sky blue
                                '#10b981', // green
                                '#f59e0b', // amber
                                '#8b5cf6'  // purple
                            ],
                            data: [2725.85, 1067.25, 156.40, 425.75],
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
                            }
                        }
                    }
                });
            }
        }, 100);
    }
    
    /**
     * Display transaction report
     */
    function displayTransactionReport(range) {
        reportContent.innerHTML = `
            <div class="row">
                <div class="col-md-12">
                    <h4 class="mb-3">Transaction Report - ${getDateRangeText(range)}</h4>
                    <p class="text-muted">Detailed breakdown of all credit transactions</p>
                    
                    <div class="card shadow mb-4">
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-bordered" width="100%" cellspacing="0">
                                    <thead>
                                        <tr>
                                            <th>Date</th>
                                            <th>Transaction ID</th>
                                            <th>Source</th>
                                            <th>Destination</th>
                                            <th>Amount</th>
                                            <th>Type</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>2023-07-15</td>
                                            <td>TX-12345</td>
                                            <td>Acme Corp (Employee Trip)</td>
                                            <td>Acme Corp</td>
                                            <td>25.60</td>
                                            <td>Trip Reward</td>
                                            <td><span class="badge bg-success">Completed</span></td>
                                        </tr>
                                        <tr>
                                            <td>2023-07-14</td>
                                            <td>TX-12344</td>
                                            <td>Tech Innovations</td>
                                            <td>Green Solutions</td>
                                            <td>150.00</td>
                                            <td>Transfer</td>
                                            <td><span class="badge bg-success">Completed</span></td>
                                        </tr>
                                        <tr>
                                            <td>2023-07-10</td>
                                            <td>TX-12343</td>
                                            <td>Global Enterprises</td>
                                            <td>Bank</td>
                                            <td>85.25</td>
                                            <td>Exchange</td>
                                            <td><span class="badge bg-success">Completed</span></td>
                                        </tr>
                                        <tr>
                                            <td>2023-07-08</td>
                                            <td>TX-12342</td>
                                            <td>Tech Innovations (Employee Trip)</td>
                                            <td>Tech Innovations</td>
                                            <td>18.75</td>
                                            <td>Trip Reward</td>
                                            <td><span class="badge bg-success">Completed</span></td>
                                        </tr>
                                        <tr>
                                            <td>2023-07-05</td>
                                            <td>TX-12341</td>
                                            <td>Green Solutions</td>
                                            <td>Bank</td>
                                            <td>120.50</td>
                                            <td>Exchange</td>
                                            <td><span class="badge bg-success">Completed</span></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            <div class="text-center mt-3">
                                <button class="btn btn-outline-primary btn-sm">Load More</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Display price report
     */
    function displayPriceReport(range) {
        reportContent.innerHTML = `
            <div class="row">
                <div class="col-md-12">
                    <h4 class="mb-3">Price Analysis - ${getDateRangeText(range)}</h4>
                    <p class="text-muted">Credit price trends and market analysis</p>
                    
                    <div class="row mt-4">
                        <div class="col-md-8">
                            <div class="card shadow mb-4">
                                <div class="card-header py-3">
                                    <h6 class="m-0 font-weight-bold text-primary">Price Trend</h6>
                                </div>
                                <div class="card-body">
                                    <canvas id="price-trend-chart" style="height: 300px;"></canvas>
                                </div>
                            </div>
                        </div>
                        
                        <div class="col-md-4">
                            <div class="card shadow mb-4">
                                <div class="card-header py-3">
                                    <h6 class="m-0 font-weight-bold text-primary">Market Summary</h6>
                                </div>
                                <div class="card-body">
                                    <div class="mb-3">
                                        <h5 class="small font-weight-bold">Current Price <span class="float-end">$12.85</span></h5>
                                    </div>
                                    <div class="mb-3">
                                        <h5 class="small font-weight-bold">7-Day High <span class="float-end">$13.25</span></h5>
                                    </div>
                                    <div class="mb-3">
                                        <h5 class="small font-weight-bold">7-Day Low <span class="float-end">$12.40</span></h5>
                                    </div>
                                    <div class="mb-3">
                                        <h5 class="small font-weight-bold">30-Day Change <span class="float-end text-success">+8.2%</span></h5>
                                    </div>
                                    <div class="mb-3">
                                        <h5 class="small font-weight-bold">Trading Volume <span class="float-end">2,854 credits</span></h5>
                                    </div>
                                    <div class="mb-3">
                                        <h5 class="small font-weight-bold">Market Cap <span class="float-end">$195,745</span></h5>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Initialize price trend chart
        setTimeout(() => {
            const priceCtx = document.getElementById('price-trend-chart').getContext('2d');
            new Chart(priceCtx, {
                type: 'line',
                data: {
                    labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
                    datasets: [{
                        label: "Price (USD)",
                        lineTension: 0.3,
                        backgroundColor: "rgba(28, 200, 138, 0.05)",
                        borderColor: "rgba(28, 200, 138, 1)",
                        pointRadius: 3,
                        pointBackgroundColor: "rgba(28, 200, 138, 1)",
                        pointBorderColor: "rgba(28, 200, 138, 1)",
                        pointHoverRadius: 3,
                        pointHoverBackgroundColor: "rgba(28, 200, 138, 1)",
                        pointHoverBorderColor: "rgba(28, 200, 138, 1)",
                        pointHitRadius: 10,
                        pointBorderWidth: 2,
                        data: [11.25, 11.50, 11.80, 12.15, 12.40, 12.70, 12.85],
                    }],
                },
                options: {
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: {
                                display: false
                            }
                        },
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value;
                                }
                            }
                        },
                    }
                }
            });
        }, 100);
    }
    
    /**
     * Display employer activity report
     */
    function displayEmployerActivityReport(range) {
        reportContent.innerHTML = `
            <div class="row">
                <div class="col-md-12">
                    <h4 class="mb-3">Employer Activity - ${getDateRangeText(range)}</h4>
                    <p class="text-muted">Analysis of employer participation and performance</p>
                    
                    <div class="row mt-4">
                        <div class="col-md-12">
                            <div class="card shadow mb-4">
                                <div class="card-header py-3">
                                    <h6 class="m-0 font-weight-bold text-primary">Employer Performance</h6>
                                </div>
                                <div class="card-body">
                                    <div class="table-responsive">
                                        <table class="table table-bordered" width="100%" cellspacing="0">
                                            <thead>
                                                <tr>
                                                    <th>Employer</th>
                                                    <th>Total Credits</th>
                                                    <th>Employee Participation</th>
                                                    <th>Avg. Credits/Employee</th>
                                                    <th>Most Used Transport</th>
                                                    <th>CO₂ Saved (tons)</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td>Acme Corporation</td>
                                                    <td>854.25</td>
                                                    <td>
                                                        <div class="progress mb-1" style="height: 10px">
                                                            <div class="progress-bar bg-success" style="width: 85%" aria-valuenow="85" aria-valuemin="0" aria-valuemax="100"></div>
                                                        </div>
                                                        <small>85% (17/20 employees)</small>
                                                    </td>
                                                    <td>50.25</td>
                                                    <td>Public Transit</td>
                                                    <td>97.6</td>
                                                </tr>
                                                <tr>
                                                    <td>Tech Innovations</td>
                                                    <td>652.10</td>
                                                    <td>
                                                        <div class="progress mb-1" style="height: 10px">
                                                            <div class="progress-bar bg-success" style="width: 76%" aria-valuenow="76" aria-valuemin="0" aria-valuemax="100"></div>
                                                        </div>
                                                        <small>76% (19/25 employees)</small>
                                                    </td>
                                                    <td>34.32</td>
                                                    <td>Electric Vehicle</td>
                                                    <td>74.5</td>
                                                </tr>
                                                <tr>
                                                    <td>Green Solutions</td>
                                                    <td>725.35</td>
                                                    <td>
                                                        <div class="progress mb-1" style="height: 10px">
                                                            <div class="progress-bar bg-success" style="width: 92%" aria-valuenow="92" aria-valuemin="0" aria-valuemax="100"></div>
                                                        </div>
                                                        <small>92% (12/13 employees)</small>
                                                    </td>
                                                    <td>60.45</td>
                                                    <td>Bicycle</td>
                                                    <td>82.8</td>
                                                </tr>
                                                <tr>
                                                    <td>Global Enterprises</td>
                                                    <td>494.15</td>
                                                    <td>
                                                        <div class="progress mb-1" style="height: 10px">
                                                            <div class="progress-bar bg-warning" style="width: 60%" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100"></div>
                                                        </div>
                                                        <small>60% (18/30 employees)</small>
                                                    </td>
                                                    <td>27.45</td>
                                                    <td>Carpool</td>
                                                    <td>56.4</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-12">
                            <div class="card shadow mb-4">
                                <div class="card-header py-3">
                                    <h6 class="m-0 font-weight-bold text-primary">Transport Mode by Employer</h6>
                                </div>
                                <div class="card-body">
                                    <canvas id="employer-transport-chart" style="height: 300px;"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Initialize employer transport chart
        setTimeout(() => {
            const employerCtx = document.getElementById('employer-transport-chart').getContext('2d');
            new Chart(employerCtx, {
                type: 'bar',
                data: {
                    labels: ["Acme Corporation", "Tech Innovations", "Green Solutions", "Global Enterprises"],
                    datasets: [
                        {
                            label: 'EV Credits',
                            backgroundColor: 'rgba(78, 115, 223, 0.7)',
                            data: [180, 320, 95, 120]
                        },
                        {
                            label: 'Public Transit',
                            backgroundColor: 'rgba(28, 200, 138, 0.7)',
                            data: [340, 115, 180, 75]
                        },
                        {
                            label: 'Carpool',
                            backgroundColor: 'rgba(54, 185, 204, 0.7)',
                            data: [120, 80, 150, 210]
                        },
                        {
                            label: 'Bike/Walk',
                            backgroundColor: 'rgba(246, 194, 62, 0.7)',
                            data: [215, 135, 300, 90]
                        }
                    ]
                },
                options: {
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            stacked: true
                        },
                        y: {
                            stacked: true,
                            beginAtZero: true
                        }
                    }
                }
            });
        }, 100);
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
            case '1y':
                return 'Last Year';
            default:
                return 'Custom Range';
        }
    }
    
    /**
     * Export a report
     */
    function exportReport(type, range, format) {
        // In a real implementation, this would construct a URL to an export endpoint
        const url = `/api/reports/export?type=${type}&range=${range}&format=${format}`;
        
        // For the demo, just alert that export would happen
        alert(`Exporting ${type} report for ${getDateRangeText(range)}`);
        
        // In a real implementation, this might trigger a download
        // window.location.href = url;
    }
}); 