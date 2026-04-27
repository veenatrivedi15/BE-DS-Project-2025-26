document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Format currency function
    window.formatCurrency = function(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    };

    // Handle real-time calculation of total amount based on credit amount
    const creditAmountInput = document.getElementById('credit-amount');
    const totalAmountElement = document.getElementById('total-amount');
    const marketRateElement = document.getElementById('market-rate');

    if (creditAmountInput && totalAmountElement && marketRateElement) {
        const marketRate = parseFloat(marketRateElement.textContent);
        
        creditAmountInput.addEventListener('input', function() {
            const creditAmount = parseFloat(this.value) || 0;
            const totalAmount = creditAmount * marketRate;
            totalAmountElement.textContent = window.formatCurrency(totalAmount);
        });
    }

    // Add confirmation for cancel offer buttons
    const cancelButtons = document.querySelectorAll('.cancel-offer-btn');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to cancel this offer?')) {
                e.preventDefault();
            }
        });
    });

    // Form validation
    const offerForm = document.getElementById('offer-form');
    if (offerForm) {
        offerForm.addEventListener('submit', function(e) {
            const creditAmount = parseFloat(creditAmountInput.value) || 0;
            const availableCredits = parseFloat(document.getElementById('available-credits').textContent) || 0;
            const offerType = document.querySelector('input[name="offer_type"]:checked').value;

            if (creditAmount <= 0) {
                e.preventDefault();
                alert('Please enter a valid credit amount greater than 0');
                return false;
            }

            if (offerType === 'sell' && creditAmount > availableCredits) {
                e.preventDefault();
                alert(`You don't have enough credits. Available: ${availableCredits}`);
                return false;
            }

            return true;
        });
    }

    // Toggle between buy and sell forms
    const buyRadio = document.getElementById('buy-radio');
    const sellRadio = document.getElementById('sell-radio');
    const buyInfo = document.getElementById('buy-info');
    const sellInfo = document.getElementById('sell-info');

    if (buyRadio && sellRadio && buyInfo && sellInfo) {
        buyRadio.addEventListener('change', function() {
            if (this.checked) {
                buyInfo.classList.remove('d-none');
                sellInfo.classList.add('d-none');
            }
        });

        sellRadio.addEventListener('change', function() {
            if (this.checked) {
                sellInfo.classList.remove('d-none');
                buyInfo.classList.add('d-none');
            }
        });
    }
}); 
 
 