/**
 * Employee Registration Form JavaScript
 * Handles form validation for the employee registration process
 */

document.addEventListener('DOMContentLoaded', function() {
    // Set up form validation
    setupFormValidation();
});

/**
 * Sets up form validation on submission
 */
function setupFormValidation() {
    const form = document.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', function(event) {
        if (!validateForm()) {
            event.preventDefault();
        }
    });
}

/**
 * Validates the form before submission
 * @returns {boolean} - Whether the form is valid
 */
function validateForm() {
    let isValid = true;
    const requiredFields = document.querySelectorAll('input[required]');
    
    // Check all required fields
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('border-red-500');
            
            // Add error message if it doesn't exist
            let errorElement = field.parentNode.querySelector('.error-message');
            if (!errorElement) {
                errorElement = document.createElement('p');
                errorElement.className = 'mt-1 text-sm text-red-600 error-message';
                errorElement.textContent = 'This field is required';
                field.parentNode.appendChild(errorElement);
            }
        } else {
            field.classList.remove('border-red-500');
            
            // Remove error message if it exists
            const errorElement = field.parentNode.querySelector('.error-message');
            if (errorElement) {
                errorElement.remove();
            }
        }
    });
    
    // Validate email format if provided
    const emailField = document.querySelector('input[type="email"]');
    if (emailField && emailField.value.trim() && !isValidEmail(emailField.value.trim())) {
        isValid = false;
        emailField.classList.add('border-red-500');
        
        // Add error message if it doesn't exist
        let errorElement = emailField.parentNode.querySelector('.error-message');
        if (!errorElement) {
            errorElement = document.createElement('p');
            errorElement.className = 'mt-1 text-sm text-red-600 error-message';
            errorElement.textContent = 'Please enter a valid email address';
            emailField.parentNode.appendChild(errorElement);
        } else {
            errorElement.textContent = 'Please enter a valid email address';
        }
    }
    
    return isValid;
}

/**
 * Validates an email address format
 * @param {string} email - The email to validate
 * @returns {boolean} - Whether the email is valid
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
} 