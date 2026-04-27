function isValidUsername(username) {
    return username.trim().length >= 3 && /^[a-zA-Z0-9_\s]+$/.test(username);
}

function isStrongPassword(password) {
    return /^(?=.*[a-z])(?=.*[A-Z])(?=.*[\W_]).{8,}$/.test(password);
}

function toggleOrgFields() {
    const role = document.querySelector('input[name="role"]:checked').value;
    const orgFields = document.getElementById('org-fields');
    const farmerFields = document.getElementById('farmer-fields');
    
    if (role === 'admin') {
        orgFields.style.display = 'block';
        farmerFields.style.display = 'none';
    } else {
        orgFields.style.display = 'none';
        farmerFields.style.display = 'block';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Bind toggle logic to radio buttons
    document.querySelectorAll('input[name="role"]').forEach(radio => {
        radio.addEventListener('change', toggleOrgFields);
    });
    
    // Initialize correct fields on load
    toggleOrgFields();

    // Password toggle functionality
    const toggleBtn = document.querySelector('.password-toggle .toggle-btn');
    if(toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const pwdInput = document.getElementById('password-input');
            if (pwdInput.type === 'password') {
                pwdInput.type = 'text';
                this.textContent = '🙈';
            } else {
                pwdInput.type = 'password';
                this.textContent = '👁️';
            }
        });
    }
});

document.getElementById('signup-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const role = document.querySelector('input[name="role"]:checked').value;
    const password = document.getElementById('password-input').value;
    const contact = document.getElementById('contact-input').value;

    if (!isStrongPassword(password)) {
        alert("Password must be at least 8 characters and include uppercase, lowercase, and special character");
        return;
    }

    if (!/^\d{10}$/.test(contact)) {
        alert("Please enter a valid 10-digit contact number");
        return;
    }

    let body = {};
    let endpoint = "";

    if (role === 'user') {
        const username = document.getElementById('username-input').value;
        if (!isValidUsername(username)) {
            alert("Invalid username (minimum 3 characters, alphanumeric)");
            return;
        }

        body = {
            username: username,
            contact_number: contact,
            password: password
        };
        endpoint = '/api/user/signup';
    } else {
        const orgname = document.getElementById('orgname-input').value;
        const email = document.getElementById('email-input').value;
        const address = document.getElementById('address-input').value;

        if (!isValidUsername(orgname)) {
            alert("Invalid Organization Name");
            return;
        }
        if (!email.trim() || !email.includes('@')) {
            alert("Please enter a valid email");
            return;
        }
        if (!address.trim()) {
            alert("Address is required for organizations");
            return;
        }

        body = {
            name: orgname,
            email: email,
            address: address,
            contact_number: contact,
            password: password
        };
        endpoint = '/api/admin/signup';
    }

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });

    const data = await response.json();

    if (!response.ok) {
        alert(data.message);
        return;
    }

    alert("Signup successful!");
    window.location.href = '/login';
});
