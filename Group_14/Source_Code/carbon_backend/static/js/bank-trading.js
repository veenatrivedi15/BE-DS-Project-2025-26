document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const navButtons = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('section');
    const createTransactionBtn = document.getElementById('create-transaction-btn');
    const createTransactionModal = document.getElementById('create-transaction-modal');
    const closeModal = document.querySelector('.close-modal');
    const transactionForm = document.getElementById('transaction-form');
    const searchInputs = document.querySelectorAll('.search-input');
    
    // Variables
    let priceChart, volumeChart, typesChart;
    
    // Initialize the page
    function init() {
        // Show the pending section by default
        document.getElementById('pending-section').style.display = 'block';
        
        // Set up event listeners
        setupNavigation();
        setupModal();
        setupFormCalculations();
        setupSearch();
        setupBuyButtons();
        
        // Initialize charts if analytics section is visible
        if (document.getElementById('analytics-section').style.display === 'block') {
            initCharts();
        }
    }
    
    // Setup navigation
    function setupNavigation() {
        navButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove active class from all buttons
                navButtons.forEach(btn => btn.classList.remove('active'));
                
                // Add active class to clicked button
                this.classList.add('active');
                
                // Hide all sections
                sections.forEach(section => section.style.display = 'none');
                
                // Show the corresponding section
                const sectionId = this.dataset.section + '-section';
                document.getElementById(sectionId).style.display = 'block';
                
                // Initialize charts if analytics section is shown
                if (sectionId === 'analytics-section') {
                    initCharts();
                }
            });
        });
    }
    
    // Setup modal
    function setupModal() {
        createTransactionBtn.addEventListener('click', function() {
            createTransactionModal.style.display = 'block';
        });
        
        closeModal.addEventListener('click', function() {
            createTransactionModal.style.display = 'none';
        });
        
        window.addEventListener('click', function(event) {
            if (event.target === createTransactionModal) {
                createTransactionModal.style.display = 'none';
            }
        });
        
        // Handle form submission
        if (transactionForm) {
            transactionForm.addEventListener('submit', function(e) {
                e.preventDefault();
                submitTransaction();
            });
        }
    }
    
    // Setup form calculations
    function setupFormCalculations() {
        const creditAmountInput = document.getElementById('credit-amount');
        const pricePerCreditInput = document.getElementById('price-per-credit');
        const totalPriceElement = document.getElementById('total-price');
        const transactionFeeElement = document.getElementById('transaction-fee');
        
        if (creditAmountInput && pricePerCreditInput) {
            function updateCalculations() {
                const creditAmount = parseFloat(creditAmountInput.value) || 0;
                const pricePerCredit = parseFloat(pricePerCreditInput.value) || 0;
                const totalPrice = creditAmount * pricePerCredit;
                const transactionFee = totalPrice * 0.02;
                
                totalPriceElement.textContent = '$' + totalPrice.toFixed(2);
                transactionFeeElement.textContent = '$' + transactionFee.toFixed(2);
            }
            
            creditAmountInput.addEventListener('input', updateCalculations);
            pricePerCreditInput.addEventListener('input', updateCalculations);
        }
    }
    
    // Setup search functionality
    function setupSearch() {
        searchInputs.forEach(input => {
            input.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const tableId = this.dataset.table;
                const tableRows = document.querySelectorAll(`#${tableId} tbody tr`);
                
                tableRows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
                
                // Show/hide no results message
                const noResultsMessage = document.querySelector(`#${tableId}-container .no-results-message`);
                if (noResultsMessage) {
                    let visibleRows = 0;
                    tableRows.forEach(row => {
                        if (row.style.display !== 'none') {
                            visibleRows++;
                        }
                    });
                    
                    noResultsMessage.style.display = visibleRows > 0 ? 'none' : 'block';
                }
            });
        });
    }
    
    // Setup buy buttons
    function setupBuyButtons() {
        const buyButtons = document.querySelectorAll('.buy-btn');
        
        buyButtons.forEach(button => {
            button.addEventListener('click', function() {
                const creditId = this.dataset.id;
                const sellerId = this.dataset.seller;
                const creditType = this.dataset.type;
                const amount = this.dataset.amount;
                const price = this.dataset.price;
                
                // Populate form with credit details
                if (document.getElementById('seller-select')) {
                    document.getElementById('seller-select').value = sellerId;
                }
                
                if (document.getElementById('credit-type')) {
                    document.getElementById('credit-type').value = creditType;
                }
                
                if (document.getElementById('credit-amount')) {
                    document.getElementById('credit-amount').value = amount;
                    document.getElementById('credit-amount').dispatchEvent(new Event('input'));
                }
                
                if (document.getElementById('price-per-credit')) {
                    document.getElementById('price-per-credit').value = price;
                    document.getElementById('price-per-credit').dispatchEvent(new Event('input'));
                }
                
                // Show the modal
                createTransactionModal.style.display = 'block';
            });
        });
    }
    
    // Submit transaction
    function submitTransaction() {
        const seller = document.getElementById('seller-select').value;
        const buyer = document.getElementById('buyer-select').value;
        const creditType = document.getElementById('credit-type').value;
        const amount = document.getElementById('credit-amount').value;
        const price = document.getElementById('price-per-credit').value;
        
        // Validate form
        if (!seller || !buyer || !creditType || !amount || !price) {
            alert('Please fill all fields');
            return;
        }
        
        if (seller === buyer) {
            alert('Seller and buyer cannot be the same');
            return;
        }
        
        // Show loading state
        const submitButton = transactionForm.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        
        // AJAX request to create transaction
        fetch('/api/transactions/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                seller_id: seller,
                buyer_id: buyer,
                credit_type: creditType,
                amount: amount,
                price_per_credit: price
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reset form
                transactionForm.reset();
                
                // Close modal
                createTransactionModal.style.display = 'none';
                
                // Show success message
                showNotification('Transaction created successfully', 'success');
                
                // Refresh the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                // Show error message
                showNotification(data.message || 'Failed to create transaction', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        })
        .finally(() => {
            // Reset button state
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        });
    }
    
    // Initialize charts
    function initCharts() {
        // Price trend chart
        const priceCtx = document.getElementById('priceChart').getContext('2d');
        priceChart = new Chart(priceCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                datasets: [{
                    label: 'Average Price per Credit',
                    data: [12.5, 13.2, 14.1, 13.8, 15.2, 16.5, 16.8],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: true
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
                        padding: 10,
                        titleFont: { weight: 'bold' },
                        callbacks: {
                            label: function(context) {
                                return `$${context.raw.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + value;
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
        
        // Volume chart
        const volumeCtx = document.getElementById('volumeChart').getContext('2d');
        volumeChart = new Chart(volumeCtx, {
            type: 'bar',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Transaction Volume',
                    data: [350, 420, 380, 490, 560, 610],
                    backgroundColor: 'rgba(46, 204, 113, 0.7)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
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
                }
            }
        });
        
        // Credit types chart
        const typesCtx = document.getElementById('creditTypesChart').getContext('2d');
        typesChart = new Chart(typesCtx, {
            type: 'doughnut',
            data: {
                labels: ['Carbon Reduction', 'Renewable Energy', 'Sustainable Transport'],
                datasets: [{
                    data: [45, 30, 25],
                    backgroundColor: [
                        'rgba(52, 152, 219, 0.7)',
                        'rgba(46, 204, 113, 0.7)',
                        'rgba(155, 89, 182, 0.7)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
        
        // Period buttons for price chart
        document.querySelectorAll('.btn-period').forEach(button => {
            button.addEventListener('click', function() {
                document.querySelectorAll('.btn-period').forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');
                
                const period = this.dataset.period;
                updateChartData(period);
            });
        });
    }
    
    // Update chart data based on period
    function updateChartData(period) {
        let labels, data;
        
        switch(period) {
            case 'week':
                labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                data = [16.2, 16.5, 16.3, 16.8, 17.1, 16.9, 17.2];
                break;
            case 'month':
                labels = Array.from({length: 30}, (_, i) => i + 1);
                data = Array.from({length: 30}, () => Math.random() * 3 + 15);
                break;
            case 'year':
                labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                data = [12.5, 13.2, 14.1, 13.8, 15.2, 16.5, 16.8, 16.2, 16.5, 16.9, 17.2, 17.5];
                break;
        }
        
        priceChart.data.labels = labels;
        priceChart.data.datasets[0].data = data;
        priceChart.update();
        
        // Also update volume chart with corresponding data
        if (period === 'week') {
            volumeChart.data.labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            volumeChart.data.datasets[0].data = [85, 92, 78, 102, 110, 95, 88];
        } else if (period === 'month') {
            volumeChart.data.labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
            volumeChart.data.datasets[0].data = [350, 420, 380, 490];
        } else {
            volumeChart.data.labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            volumeChart.data.datasets[0].data = [350, 420, 380, 490, 560, 610, 580, 540, 620, 680, 720, 790];
        }
        
        volumeChart.update();
    }
    
    // Show notification
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Hide notification after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    // Helper to get CSRF token from cookies
    function getCookie(name) {
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
    
    // Initialize the page
    init();
}); 