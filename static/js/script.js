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

    // PDF upload handling
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('invoice');
    const pdfFrame = document.getElementById('pdf-frame');
    const pdfPreview = document.getElementById('pdf-preview');
    const submitButton = document.getElementById('submit-button');
    const uploadForm = document.getElementById('upload-form');

    function validateFileType(file) {
        const validTypes = ['application/pdf'];
        if (!validTypes.includes(file.type)) {
            alert('Please upload a PDF file only!');
            return false;
        }
        return true;
    }

    function previewPDF(file) {
        const fileURL = URL.createObjectURL(file);
        pdfFrame.src = fileURL;
        pdfPreview.style.display = 'block';
    }

    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.backgroundColor = '#e7f3ff';
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.style.backgroundColor = 'white';
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.backgroundColor = 'white';
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            if (validateFileType(files[0])) {
                fileInput.files = files;
                previewPDF(files[0]);
            }
        }
    });

    fileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            if (validateFileType(files[0])) {
                previewPDF(files[0]);
            } else {
                e.target.value = '';
            }
        }
    });

    // Form submission handling
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            submitButton.innerHTML = 'Validation <span class="loading"></span>';
            submitButton.disabled = true;
        });
    }

    // Toggle details function for previous submissions
    window.toggleDetails = function(detailId) {
        const detailsRow = document.getElementById(detailId);
        if (detailsRow.style.display === "none") {
            detailsRow.style.display = "table-row";
        } else {
            detailsRow.style.display = "none";
        }
    }
});
