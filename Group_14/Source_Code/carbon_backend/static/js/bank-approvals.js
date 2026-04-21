/**
 * Carbon Credits Platform - Bank Approvals JavaScript
 * This file contains the functionality for the bank approvals page.
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeApprovals();
});

/**
 * Initialize approvals page functionality
 */
function initializeApprovals() {
    setupApprovalButtons();
    setupRejectionButtons();
    setupFilterFunctionality();
}

/**
 * Set up the approval buttons functionality
 */
function setupApprovalButtons() {
    const approveButtons = document.querySelectorAll('.btn-approve');
    
    approveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const row = this.closest('tr');
            const id = row.querySelector('td:first-child').textContent.trim();
            const transactionId = id.replace('#', '');
            
            if (confirm(`Are you sure you want to approve transaction ${id}?`)) {
                // Show loading state
                button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                button.disabled = true;
                
                // In production, make an AJAX request to the server
                // For demo purposes, we'll simulate the request
                setTimeout(() => {
                    approveTransaction(transactionId, row);
                }, 1000);
            }
        });
    });
}

/**
 * Set up the rejection buttons functionality
 */
function setupRejectionButtons() {
    const rejectButtons = document.querySelectorAll('.btn-reject');
    
    rejectButtons.forEach(button => {
        button.addEventListener('click', function() {
            const row = this.closest('tr');
            const id = row.querySelector('td:first-child').textContent.trim();
            const transactionId = id.replace('#', '');
            
            if (confirm(`Are you sure you want to reject transaction ${id}?`)) {
                // Show loading state
                button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                button.disabled = true;
                
                // In production, make an AJAX request to the server
                // For demo purposes, we'll simulate the request
                setTimeout(() => {
                    rejectTransaction(transactionId, row);
                }, 1000);
            }
        });
    });
}

/**
 * Process approval for a transaction
 * @param {string} transactionId - The ID of the transaction to approve
 * @param {HTMLElement} row - The table row element
 */
function approveTransaction(transactionId, row) {
    // In production, this would be an AJAX call to the server
    // For demo purposes, we'll simply update the UI
    
    // Create success notification
    showNotification('success', `Transaction #${transactionId} approved successfully`);
    
    // Remove the row with animation
    row.style.backgroundColor = '#dcfce7';
    setTimeout(() => {
        row.style.opacity = '0';
        row.style.transition = 'opacity 0.5s ease';
        
        setTimeout(() => {
            row.remove();
            updateCounters();
            checkEmptyTable();
        }, 500);
    }, 500);
    
    // In production, redirect to approval URL:
    // window.location.href = `/bank/approve_transaction/${transactionId}`;
}

/**
 * Process rejection for a transaction
 * @param {string} transactionId - The ID of the transaction to reject
 * @param {HTMLElement} row - The table row element
 */
function rejectTransaction(transactionId, row) {
    // In production, this would be an AJAX call to the server
    // For demo purposes, we'll simply update the UI
    
    // Create error notification
    showNotification('error', `Transaction #${transactionId} rejected`);
    
    // Remove the row with animation
    row.style.backgroundColor = '#fee2e2';
    setTimeout(() => {
        row.style.opacity = '0';
        row.style.transition = 'opacity 0.5s ease';
        
        setTimeout(() => {
            row.remove();
            updateCounters();
            checkEmptyTable();
        }, 500);
    }, 500);
    
    // In production, redirect to rejection URL:
    // window.location.href = `/bank/reject_transaction/${transactionId}`;
}

/**
 * Update the counters for pending transactions
 */
function updateCounters() {
    // If there are counters on the page, update them
    const pendingCounter = document.querySelector('.pending-counter');
    if (pendingCounter) {
        const currentCount = parseInt(pendingCounter.textContent);
        pendingCounter.textContent = currentCount - 1;
    }
}

/**
 * Check if the table is empty and display a message
 */
function checkEmptyTable() {
    const table = document.querySelector('table');
    const tbody = table.querySelector('tbody');
    
    if (tbody.querySelectorAll('tr').length === 0) {
        // Create an empty row with a message
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = `
            <td colspan="7" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                No pending transactions found.
            </td>
        `;
        tbody.appendChild(emptyRow);
    }
}

/**
 * Set up filtering functionality for the table
 */
function setupFilterFunctionality() {
    // Add search functionality if needed
    const searchInput = document.querySelector('#search-transactions');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            filterTransactions(searchTerm);
        });
    }
}

/**
 * Filter transactions based on search term
 * @param {string} searchTerm - The search term to filter by
 */
function filterTransactions(searchTerm) {
    const rows = document.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        // Skip the empty message row
        if (row.cells.length === 1 && row.cells[0].colSpan === 7) {
            return;
        }
        
        const text = row.textContent.toLowerCase();
        const match = text.includes(searchTerm);
        
        // Set display based on match
        row.style.display = match ? '' : 'none';
    });
}

/**
 * Show a notification message
 * @param {string} type - The type of notification (success, error, info)
 * @param {string} message - The message to display
 */
function showNotification(type, message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
        </div>
    `;
    
    // Add styles for notification
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '10px 20px';
    notification.style.borderRadius = '4px';
    notification.style.zIndex = '1000';
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.3s ease';
    
    // Set colors based on type
    if (type === 'success') {
        notification.style.backgroundColor = '#dcfce7';
        notification.style.color = '#166534';
        notification.style.border = '1px solid #10b981';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#fee2e2';
        notification.style.color = '#b91c1c';
        notification.style.border = '1px solid #ef4444';
    } else {
        notification.style.backgroundColor = '#e0f2fe';
        notification.style.color = '#1e40af';
        notification.style.border = '1px solid #3b82f6';
    }
    
    // Add to document
    document.body.appendChild(notification);
    
    // Show notification with animation
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 10);
    
    // Hide notification after a delay
    setTimeout(() => {
        notification.style.opacity = '0';
        
        // Remove from DOM after fadeout
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
} 