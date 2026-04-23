function isStrongPassword(password) {
    return /^(?=.*[a-z])(?=.*[A-Z])(?=.*[\W_]).{8,}$/.test(password);
}

function isValidUsername(username) {
    return username.trim().length >= 3;
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const role = document.querySelector('input[name="role"]:checked').value;

    if (!isValidUsername(username) || !isStrongPassword(password)) {
        alert("Invalid credentials format");
        return;
    }

    const endpoint =
        role === 'admin'
            ? '/api/admin/login'
            : '/api/user/login';

    const loginData = { username, password };

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData)
    });

    const data = await response.json();

    if (!response.ok) {
        alert(data.message);
        return;
    }

    alert("Login successful!");

    // Store user session data
    localStorage.setItem('isLoggedIn', 'true');
    localStorage.setItem('username', username);
    localStorage.setItem('role', role);

    // update nav immediately (in case the homepage caches)
    try { checkLoginState(); } catch {}

    // redirect to dashboard for convenience
    window.location.href = '/dashboard';
});

// Password toggle functionality
document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.querySelector('.password-toggle .toggle-btn');
    if(toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const pwdInput = document.getElementById('login-password');
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
