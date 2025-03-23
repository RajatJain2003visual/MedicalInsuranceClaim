// static/js/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Cache DOM elements to avoid repeated querySelector calls
    const loginForm = document.getElementById('login_form');
    const registerForm = document.getElementById('register_form');
    const showLoginBtn = document.getElementById('showLogin');
    const showRegisterBtn = document.getElementById('showRegister');

    // Form toggle handlers
    showLoginBtn.addEventListener('click', () => {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
    });

    showRegisterBtn.addEventListener('click', () => {
        registerForm.classList.remove('hidden');
        loginForm.classList.add('hidden');
    });

    // Registration validation
    function validateRegistration() {
        const fullName = document.getElementById('full_name').value.trim();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();

        // Use a single validation check instead of multiple if statements
        const validations = [
            { condition: !fullName || fullName.length < 2, message: 'Full name must be at least 2 characters long' },
            { condition: !username || username.length < 3, message: 'Username must be at least 3 characters long' },
            { condition: !password || password.length < 6, message: 'Password must be at least 6 characters long' }
        ];

        const failedValidation = validations.find(v => v.condition);
        if (failedValidation) {
            alert(failedValidation.message);
            return false;
        }

        return true;
    }

    // Add submit handler to registration form
    registerForm.addEventListener('submit', (e) => {
        if (!validateRegistration()) {
            e.preventDefault();
        }
    });

    // Prevent form resubmission
    if (window.history.replaceState) {
        window.history.replaceState(null, null, window.location.href);
    }
});
