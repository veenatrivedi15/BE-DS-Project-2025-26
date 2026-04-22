document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const reportTypeSelect = document.getElementById('report-type');
    const dateRangeSelect = document.getElementById('date-range');
    const generateReportBtn = document.getElementById('generate-report-btn');
    const exportBtn = document.getElementById('export-btn');
    const exportFormatSelect = document.getElementById('export-format');
    
    // Chart instances
    let marketActivityChart = null;
    let transactionPieChart = null;
    
    // Initialize with summary report on load
    initializeSummaryReport();
    
    // Event listeners
    generateReportBtn.addEventListener('click', function() {
        const reportType = reportTypeSelect.value;
        const dateRange = dateRangeSelect.value;
        
        // Clear existing charts
        if (marketActivityChart) marketActivityChart.destroy();
        if (transactionPieChart) transactionPieChart.destroy();
        
        // Show appropriate report section based on selection
        fetchReportData(reportType, dateRange);
    });
    
    exportBtn.addEventListener('click', function() {
        const reportType = reportTypeSelect.value;
        const dateRange = dateRangeSelect.value;
        const format = exportFormatSelect.value;
        
        exportReport(reportType, dateRange, format);
    });
    
    function initializeSummaryReport() {
        // Sample data - in production this would be fetched from the server
        const marketActivityData = {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [
                {
                    label: 'Transaction Volume',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Average Price',
                    data: [50, 55, 60, 58, 56, 65],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        };
        
        const transactionPieData = {
            labels: ['Employer Purchases', 'Employee Sales', 'Bank Transactions', 'System Operations'],
            datasets: [{
                data: [35, 25, 30, 10],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(255, 99, 132, 0.7)'
                ],
                borderWidth: 1
            }]
        };
        
        // Initialize charts
        const marketActivityCtx = document.getElementById('market-activity-chart').getContext('2d');
        marketActivityChart = new Chart(marketActivityCtx, {
            type: 'line',
            data: marketActivityData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Transaction Volume'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        title: {
                            display: true,
                            text: 'Average Price'
                        }
                    }
                }
            }
        });
        
        const transactionPieCtx = document.getElementById('transaction-pie-chart').getContext('2d');
        transactionPieChart = new Chart(transactionPieCtx, {
            type: 'doughnut',
            data: transactionPieData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
        // Update summary metrics
        document.getElementById('total-credits').textContent = '45,678';
        document.getElementById('credits-change').textContent = '+12.5%';
        document.getElementById('transaction-count').textContent = '893';
        document.getElementById('transaction-change').textContent = '+5.2%';
        document.getElementById('avg-price').textContent = '$65';
        document.getElementById('price-change').textContent = '+3.8%';
    }
    
    function fetchReportData(reportType, dateRange) {
        // In a real implementation, this would make a fetch request to the server
        // For now, we'll just simulate loading and then show some sample data
        
        document.getElementById('loading-indicator').classList.add('htmx-request');
        
        // Simulate API request with a timeout
        setTimeout(() => {
            document.getElementById('loading-indicator').classList.remove('htmx-request');
            
            if (reportType === 'summary') {
                initializeSummaryReport();
            } else if (reportType === 'transactions') {
                showTransactionReport(dateRange);
            } else if (reportType === 'price') {
                showPriceReport(dateRange);
            } else if (reportType === 'employer_activity') {
                showEmployerActivityReport(dateRange);
            }
        }, 1000);
    }
    
    function showTransactionReport(dateRange) {
        // Clear current content and inject transaction report HTML
        const reportContent = document.getElementById('report-content');
        reportContent.innerHTML = `
            <div id="transaction-report" class="report-section">
                <div class="card shadow mb-4">
                    <div class="card-header bg-light py-3">
                        <h6 class="m-0 font-weight-bold">Transaction History</h6>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Transaction ID</th>
                                        <th>Type</th>
                                        <th>Counterparty</th>
                                        <th>Credits</th>
                                        <th>Price</th>
                                        <th>Total Value</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>2023-05-10</td>
                                        <td>TX-1025478</td>
                                        <td>Purchase</td>
                                        <td>EcoTech Inc.</td>
                                        <td>500</td>
                                        <td>$62.50</td>
                                        <td>$31,250</td>
                                        <td><span class="badge bg-success">Completed</span></td>
                                    </tr>
                                    <tr>
                                        <td>2023-05-08</td>
                                        <td>TX-1025477</td>
                                        <td>Sale</td>
                                        <td>GreenLife Co.</td>
                                        <td>750</td>
                                        <td>$63.25</td>
                                        <td>$47,437.50</td>
                                        <td><span class="badge bg-success">Completed</span></td>
                                    </tr>
                                    <tr>
                                        <td>2023-05-05</td>
                                        <td>TX-1025476</td>
                                        <td>Purchase</td>
                                        <td>SustainCorp</td>
                                        <td>300</td>
                                        <td>$64.00</td>
                                        <td>$19,200</td>
                                        <td><span class="badge bg-success">Completed</span></td>
                                    </tr>
                                    <tr>
                                        <td>2023-05-03</td>
                                        <td>TX-1025475</td>
                                        <td>Sale</td>
                                        <td>EcoTech Inc.</td>
                                        <td>400</td>
                                        <td>$65.75</td>
                                        <td>$26,300</td>
                                        <td><span class="badge bg-success">Completed</span></td>
                                    </tr>
                                    <tr>
                                        <td>2023-05-01</td>
                                        <td>TX-1025474</td>
                                        <td>Purchase</td>
                                        <td>GreenLife Co.</td>
                                        <td>600</td>
                                        <td>$65.50</td>
                                        <td>$39,300</td>
                                        <td><span class="badge bg-success">Completed</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    function showPriceReport(dateRange) {
        // Clear current content and inject price report HTML
        const reportContent = document.getElementById('report-content');
        reportContent.innerHTML = `
            <div id="price-report" class="report-section">
                <div class="row">
                    <div class="col-12 mb-4">
                        <div class="card shadow">
                            <div class="card-header bg-light py-3">
                                <h6 class="m-0 font-weight-bold">Market Price Analytics</h6>
                            </div>
                            <div class="card-body">
                                <canvas id="price-history-chart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card shadow h-100">
                            <div class="card-header bg-light py-3">
                                <h6 class="m-0 font-weight-bold">Price Statistics</h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-6 mb-3">
                                        <h6 class="text-muted">Current Price</h6>
                                        <h3>$65.75</h3>
                                    </div>
                                    <div class="col-6 mb-3">
                                        <h6 class="text-muted">24h Change</h6>
                                        <h3 class="text-success">+2.5%</h3>
                                    </div>
                                    <div class="col-6 mb-3">
                                        <h6 class="text-muted">7d High</h6>
                                        <h3>$67.25</h3>
                                    </div>
                                    <div class="col-6 mb-3">
                                        <h6 class="text-muted">7d Low</h6>
                                        <h3>$62.10</h3>
                                    </div>
                                    <div class="col-6">
                                        <h6 class="text-muted">30d Average</h6>
                                        <h3>$64.30</h3>
                                    </div>
                                    <div class="col-6">
                                        <h6 class="text-muted">Volume (7d)</h6>
                                        <h3>12,450</h3>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6 mb-4">
                        <div class="card shadow h-100">
                            <div class="card-header bg-light py-3">
                                <h6 class="m-0 font-weight-bold">Market Events</h6>
                            </div>
                            <div class="card-body">
                                <div class="timeline">
                                    <div class="timeline-item pb-3">
                                        <div class="d-flex">
                                            <div class="timeline-date me-3">May 10</div>
                                            <div>
                                                <h6 class="mb-1">Price Spike</h6>
                                                <p class="text-muted mb-0">Credits increased by 4.2% following new sustainability policy announcement.</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="timeline-item pb-3">
                                        <div class="d-flex">
                                            <div class="timeline-date me-3">May 5</div>
                                            <div>
                                                <h6 class="mb-1">High Volume Day</h6>
                                                <p class="text-muted mb-0">Record trading volume of 2,500 credits in a single day.</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="timeline-item">
                                        <div class="d-flex">
                                            <div class="timeline-date me-3">Apr 28</div>
                                            <div>
                                                <h6 class="mb-1">Market Correction</h6>
                                                <p class="text-muted mb-0">Price stabilized after 2-day decline of 3.5%.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Initialize price history chart
        const priceHistoryData = {
            labels: ['Apr 1', 'Apr 8', 'Apr 15', 'Apr 22', 'Apr 29', 'May 6', 'May 13'],
            datasets: [
                {
                    label: 'Credit Price (USD)',
                    data: [58, 61, 63, 62, 64, 63, 65.75],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        };
        
        const priceHistoryCtx = document.getElementById('price-history-chart').getContext('2d');
        new Chart(priceHistoryCtx, {
            type: 'line',
            data: priceHistoryData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Price (USD)'
                        }
                    }
                }
            }
        });
    }
    
    function showEmployerActivityReport(dateRange) {
        // Clear current content and inject employer activity report HTML
        const reportContent = document.getElementById('report-content');
        reportContent.innerHTML = `
            <div id="employer-activity-report" class="report-section">
                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card shadow h-100">
                            <div class="card-header bg-light py-3">
                                <h6 class="m-0 font-weight-bold">Top Employers by Volume</h6>
                            </div>
                            <div class="card-body">
                                <canvas id="employer-volume-chart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6 mb-4">
                        <div class="card shadow h-100">
                            <div class="card-header bg-light py-3">
                                <h6 class="m-0 font-weight-bold">Employer Growth Trends</h6>
                            </div>
                            <div class="card-body">
                                <canvas id="employer-growth-chart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card shadow mb-4">
                    <div class="card-header bg-light py-3">
                        <h6 class="m-0 font-weight-bold">Employer Activity Table</h6>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Employer</th>
                                        <th>Industry</th>
                                        <th>Employees</th>
                                        <th>Credits Purchased</th>
                                        <th>Credits Used</th>
                                        <th>Current Balance</th>
                                        <th>30d Change</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>EcoTech Inc.</td>
                                        <td>Technology</td>
                                        <td>245</td>
                                        <td>5,250</td>
                                        <td>4,780</td>
                                        <td>470</td>
                                        <td class="text-success">+12.5%</td>
                                    </tr>
                                    <tr>
                                        <td>GreenLife Co.</td>
                                        <td>Retail</td>
                                        <td>189</td>
                                        <td>4,100</td>
                                        <td>3,650</td>
                                        <td>450</td>
                                        <td class="text-success">+8.3%</td>
                                    </tr>
                                    <tr>
                                        <td>SustainCorp</td>
                                        <td>Manufacturing</td>
                                        <td>312</td>
                                        <td>6,800</td>
                                        <td>6,400</td>
                                        <td>400</td>
                                        <td class="text-danger">-2.1%</td>
                                    </tr>
                                    <tr>
                                        <td>EcoEnergy Ltd.</td>
                                        <td>Energy</td>
                                        <td>156</td>
                                        <td>3,250</td>
                                        <td>2,900</td>
                                        <td>350</td>
                                        <td class="text-success">+5.2%</td>
                                    </tr>
                                    <tr>
                                        <td>CarboZero Inc.</td>
                                        <td>Logistics</td>
                                        <td>203</td>
                                        <td>4,500</td>
                                        <td>4,200</td>
                                        <td>300</td>
                                        <td class="text-success">+3.8%</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Initialize employer charts
        const employerVolumeData = {
            labels: ['EcoTech Inc.', 'GreenLife Co.', 'SustainCorp', 'EcoEnergy Ltd.', 'CarboZero Inc.'],
            datasets: [{
                label: 'Credits Purchased',
                data: [5250, 4100, 6800, 3250, 4500],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 99, 132, 0.7)'
                ],
                borderWidth: 1
            }]
        };
        
        const employerGrowthData = {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            datasets: [
                {
                    label: 'EcoTech Inc.',
                    data: [380, 390, 420, 450, 470],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'GreenLife Co.',
                    data: [410, 425, 415, 430, 450],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'SustainCorp',
                    data: [450, 430, 420, 410, 400],
                    borderColor: 'rgb(255, 206, 86)',
                    backgroundColor: 'rgba(255, 206, 86, 0.1)',
                    tension: 0.4
                }
            ]
        };
        
        const employerVolumeCtx = document.getElementById('employer-volume-chart').getContext('2d');
        new Chart(employerVolumeCtx, {
            type: 'bar',
            data: employerVolumeData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Credits Purchased'
                        }
                    }
                }
            }
        });
        
        const employerGrowthCtx = document.getElementById('employer-growth-chart').getContext('2d');
        new Chart(employerGrowthCtx, {
            type: 'line',
            data: employerGrowthData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: 'Credit Balance'
                        }
                    }
                }
            }
        });
    }
    
    function exportReport(reportType, dateRange, format) {
        // In a real implementation, this would make a fetch request to export endpoint
        // For now, we'll just show an alert
        const reportNames = {
            'summary': 'Summary Report',
            'transactions': 'Transaction History',
            'price': 'Price Analytics',
            'employer_activity': 'Employer Activity'
        };
        
        const dateRangeNames = {
            '7d': 'Last 7 Days',
            '30d': 'Last 30 Days',
            '90d': 'Last 90 Days',
            '1y': 'Last Year',
            'all': 'All Time'
        };
        
        alert(`Exporting ${reportNames[reportType]} for ${dateRangeNames[dateRange]} in ${format.toUpperCase()} format...`);
        
        // In a real implementation, this would trigger a download
        // window.location.href = `/api/reports/export?type=${reportType}&range=${dateRange}&format=${format}`;
    }
}); 