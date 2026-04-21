document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initializeCharts();
    
    // Add event listeners for period buttons
    document.querySelectorAll('.period-btn').forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            document.querySelectorAll('.period-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to the clicked button
            this.classList.add('active');
            
            // Update charts for the selected period
            const period = this.getAttribute('data-period');
            updateChartsForPeriod(period);
        });
    });
    
    // Handle window resize for responsive charts
    window.addEventListener('resize', function() {
        // Destroy and reinitialize charts on window resize for better responsiveness
        if (window.creditsChart) {
            window.creditsChart.destroy();
        }
        if (window.transportChart) {
            window.transportChart.destroy();
        }
        initializeCharts();
        
        // Get current active period
        const activePeriod = document.querySelector('.period-btn.active').getAttribute('data-period');
        updateChartsForPeriod(activePeriod);
    });
    
    // Add touch event listeners for mobile
    document.addEventListener('touchstart', handleTouchStart, false);
    document.addEventListener('touchmove', handleTouchMove, false);
    
    let xDown = null;
    let yDown = null;
    
    function handleTouchStart(evt) {
        const firstTouch = evt.touches[0];
        xDown = firstTouch.clientX;
        yDown = firstTouch.clientY;
    }
    
    function handleTouchMove(evt) {
        if (!xDown || !yDown) {
            return;
        }
        
        const xUp = evt.touches[0].clientX;
        const yUp = evt.touches[0].clientY;
        
        const xDiff = xDown - xUp;
        const yDiff = yDown - yUp;
        
        // Only process if the swipe is more horizontal than vertical
        if (Math.abs(xDiff) > Math.abs(yDiff)) {
            const periodBtns = document.querySelectorAll('.period-btn');
            const activeBtnIndex = Array.from(periodBtns).findIndex(btn => btn.classList.contains('active'));
            
            if (xDiff > 0) {
                // Swipe left - go to next period
                const nextIndex = (activeBtnIndex + 1) % periodBtns.length;
                periodBtns[nextIndex].click();
            } else {
                // Swipe right - go to previous period
                const prevIndex = (activeBtnIndex - 1 + periodBtns.length) % periodBtns.length;
                periodBtns[prevIndex].click();
            }
        }
        
        // Reset values
        xDown = null;
        yDown = null;
    }
    
    // Fix for mobile pull-to-refresh issues
    document.body.addEventListener('touchmove', function(e) {
        // Prevent pull-to-refresh behavior when at the top of the page
        if (window.scrollY === 0) {
            e.preventDefault();
        }
    }, { passive: false });
    
    // Add touch event support for mobile devices
    const chartCards = document.querySelectorAll('.chart-card');
    
    chartCards.forEach(card => {
        // Add touch feedback
        card.addEventListener('touchstart', function() {
            this.style.opacity = '0.9';
        });
        
        card.addEventListener('touchend', function() {
            this.style.opacity = '1';
        });
    });
    
    // Improve touch response on period buttons
    const periodButtons = document.querySelectorAll('.period-btn');
    
    periodButtons.forEach(button => {
        button.addEventListener('touchstart', function(e) {
            // Prevent default to avoid delay on mobile
            e.preventDefault();
            this.click();
        });
    });
    
    // Check if viewport is mobile sized on page load
    checkMobileView();
});

function initializeCharts() {
    // Credits chart initialization
    const creditsCtx = document.getElementById('creditsChart').getContext('2d');
    
    // Responsive font size based on screen width
    const fontSize = window.innerWidth < 768 ? 10 : 12;
    
    window.creditsChart = new Chart(creditsCtx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Credits Issued',
                data: [150, 320, 240, 350, 280, 220, 390],
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderColor: '#2563eb',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#2563eb',
                pointBorderColor: '#fff',
                pointBorderWidth: 1,
                pointRadius: window.innerWidth < 768 ? 2 : 3,
                pointHoverRadius: window.innerWidth < 768 ? 3 : 5
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
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleFont: {
                        size: fontSize
                    },
                    bodyFont: {
                        size: fontSize
                    },
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y.toFixed(2)} credits`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: fontSize
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: fontSize
                        },
                        callback: function(value) {
                            if (window.innerWidth < 576) {
                                // For very small screens, abbreviate numbers
                                return value >= 1000 ? (value/1000).toFixed(1) + 'k' : value;
                            }
                            return value;
                        }
                    }
                }
            }
        }
    });
    
    // Transport mode chart initialization
    const transportCtx = document.getElementById('transportChart').getContext('2d');
    
    window.transportChart = new Chart(transportCtx, {
        type: 'doughnut',
        data: {
            labels: ['Bicycle', 'Bus', 'Train', 'Carpool', 'Walk'],
            datasets: [{
                data: [35, 25, 20, 15, 5],
                backgroundColor: [
                    '#2563eb', // Primary color
                    '#0ea5e9', // Secondary
                    '#8b5cf6', // Purple
                    '#10b981', // Green
                    '#f59e0b'  // Yellow
                ],
                borderWidth: window.innerWidth < 768 ? 1 : 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: window.innerWidth < 768 ? 'bottom' : 'right',
                    labels: {
                        boxWidth: window.innerWidth < 768 ? 12 : 15,
                        padding: window.innerWidth < 768 ? 10 : 15,
                        font: {
                            size: fontSize
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleFont: {
                        size: fontSize
                    },
                    bodyFont: {
                        size: fontSize
                    },
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed}%`;
                        }
                    }
                }
            }
        }
    });
}

function updateChartsForPeriod(period) {
    // Sample data for different periods
    const creditsData = {
        weekly: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            data: [150, 320, 240, 350, 280, 220, 390]
        },
        monthly: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            data: [1200, 1450, 1320, 1580]
        },
        yearly: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            data: [4200, 3800, 5100, 4700, 5300, 5800, 6200, 5900, 6500, 6800, 7200, 7500]
        }
    };
    
    const transportData = {
        weekly: [35, 25, 20, 15, 5],
        monthly: [30, 28, 22, 12, 8],
        yearly: [28, 30, 25, 10, 7]
    };
    
    // Update credits chart
    window.creditsChart.data.labels = creditsData[period].labels;
    window.creditsChart.data.datasets[0].data = creditsData[period].data;
    window.creditsChart.update();
    
    // Update transport chart
    window.transportChart.data.datasets[0].data = transportData[period];
    window.transportChart.update();
    
    // Update stats
    updateStats(period);
}

function updateStats(period) {
    // Sample data for each period
    const stats = {
        weekly: {
            employers: 16,
            transactions: 25,
            credits: 2725.85,
            carbon: 312.36,
            trends: {
                employers: 12.5,
                transactions: 23.8,
                credits: 18.2,
                carbon: 15.7
            }
        },
        monthly: {
            employers: 42,
            transactions: 86,
            credits: 9843.24,
            carbon: 1128.45,
            trends: {
                employers: 8.3,
                transactions: 15.6,
                credits: 12.8,
                carbon: 10.5
            }
        },
        yearly: {
            employers: 125,
            transactions: 348,
            credits: 42567.92,
            carbon: 4875.32,
            trends: {
                employers: 32.8,
                transactions: 45.2,
                credits: 28.7,
                carbon: 22.3
            }
        }
    };
    
    // Get stat elements
    const statValues = document.querySelectorAll('.stat-value');
    const statTrends = document.querySelectorAll('.stat-trend');
    
    // Update employer stats
    animateValue(statValues[0], parseInt(statValues[0].innerText.replace(/,/g, '')), stats[period].employers, 1000);
    updateTrend(statTrends[0], stats[period].trends.employers);
    
    // Update transaction stats
    animateValue(statValues[1], parseInt(statValues[1].innerText.replace(/,/g, '')), stats[period].transactions, 1000);
    updateTrend(statTrends[1], stats[period].trends.transactions);
    
    // Update credits stats
    animateValue(statValues[2], parseFloat(statValues[2].innerText.replace(/,/g, '')), stats[period].credits, 1000, 2);
    updateTrend(statTrends[2], stats[period].trends.credits);
    
    // Update carbon stats
    animateValue(statValues[3], parseFloat(statValues[3].innerText.replace(/,/g, '')), stats[period].carbon, 1000, 2);
    updateTrend(statTrends[3], stats[period].trends.carbon);
}

function animateValue(element, start, end, duration, decimals = 0) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const currentValue = progress * (end - start) + start;
        
        // Format with commas and decimal places if needed
        if (decimals > 0) {
            element.innerText = formatNumber(currentValue.toFixed(decimals));
        } else {
            element.innerText = formatNumber(Math.floor(currentValue));
        }
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function updateTrend(element, trendValue) {
    const isPositive = trendValue >= 0;
    element.innerHTML = `<i class="fas fa-arrow-${isPositive ? 'up' : 'down'}"></i> ${Math.abs(trendValue).toFixed(1)}%`;
    
    // Update classes for positive/negative trends
    element.classList.remove('positive', 'negative');
    element.classList.add(isPositive ? 'positive' : 'negative');
}

function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function checkMobileView() {
    const isMobile = window.innerWidth < 768;
    
    if (isMobile) {
        // Adjust any mobile-specific settings
        if (window.transportChart) {
            window.transportChart.options.plugins.legend.position = 'bottom';
            window.transportChart.update();
        }
    }
} 