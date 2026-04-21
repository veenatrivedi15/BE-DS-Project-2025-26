document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add confirmation for approve/reject buttons
    const approveButtons = document.querySelectorAll('button.btn-success');
    const rejectButtons = document.querySelectorAll('button.btn-danger');

    approveButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to approve this offer? This will transfer credits and cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    rejectButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to reject this offer?')) {
                e.preventDefault();
            }
        });
    });

    // Add utility function to format currency
    window.formatCurrency = function(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    };

    // Update total value when credit amount or price changes (for future implementation)
    function updateTotalValue() {
        const creditAmount = parseFloat(document.getElementById('credit-amount')?.value || 0);
        const pricePerCredit = parseFloat(document.getElementById('price-per-credit')?.value || 0);
        
        if (!isNaN(creditAmount) && !isNaN(pricePerCredit)) {
            const totalValue = creditAmount * pricePerCredit;
            const totalValueElement = document.getElementById('total-value');
            if (totalValueElement) {
                totalValueElement.textContent = window.formatCurrency(totalValue);
            }
        }
    }

    // Set up event listeners for future form implementation
    const creditAmountInput = document.getElementById('credit-amount');
    const pricePerCreditInput = document.getElementById('price-per-credit');

    if (creditAmountInput) {
        creditAmountInput.addEventListener('input', updateTotalValue);
    }
    
    if (pricePerCreditInput) {
        pricePerCreditInput.addEventListener('input', updateTotalValue);
    }

    // Refresh page every 5 minutes to get updates
    setTimeout(function() {
        window.location.reload();
    }, 5 * 60 * 1000);
}); 
 
 