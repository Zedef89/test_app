document.addEventListener('DOMContentLoaded', () => {
    const emailInput = document.getElementById('emailInput');
    const passwordInput = document.getElementById('passwordInput');
    const loginButton = document.getElementById('loginButton');
    const messageArea = document.getElementById('messageArea');

    // Function to display messages
    function showMessage(message, isError = false) {
        messageArea.textContent = message;
        if (isError) {
            messageArea.classList.remove('text-green-600');
            messageArea.classList.add('text-red-600');
        } else {
            messageArea.classList.remove('text-red-600');
            messageArea.classList.add('text-green-600');
        }
    }

    loginButton.addEventListener('click', async (event) => {
        event.preventDefault(); // Prevent default form submission, though not strictly needed here

        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();

        // Basic validation
        if (!email || !password) {
            showMessage('Please enter both email and password.', true);
            return;
        }
        if (!/\S+@\S+\.\S+/.test(email)) {
            showMessage('Please enter a valid email address.', true);
            return;
        }

        const payload = {
            email: email,
            password: password
        };

        try {
            // Assuming the backend is running on the same domain or proxied.
            // For development, ensure the API_URL is correct.
            // Example: const API_URL = 'http://localhost:8000';
            // const response = await fetch(`${API_URL}/api/login`, {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const responseData = await response.json();

            if (response.ok) { // Status 200-299
                localStorage.setItem('authToken', responseData.access_token);
                localStorage.setItem('userData', JSON.stringify({
                    userId: responseData.user_id,
                    email: responseData.email,
                    role: responseData.role
                }));
                
                showMessage(`Login successful! Welcome, ${responseData.email}. Token: ${responseData.access_token.substring(0,10)}... Role: ${responseData.role}`, false);
                
                // Conceptual redirection (for this task, a message is sufficient)
                console.log('Login successful. Token stored. User data stored.');
                console.log('Would redirect to dashboard or role-specific page.');
                // Example: window.location.href = '/dashboard.html'; 
                // or based on role:
                // if (responseData.role === 'caregiver') window.location.href = '/caregiver_dashboard.html';
                // else if (responseData.role === 'family') window.location.href = '/family_dashboard.html';
                
            } else {
                // Display error message from backend (e.g., responseData.detail)
                showMessage(responseData.detail || 'Login failed. Please check your credentials.', true);
            }
        } catch (error) {
            console.error('Login error:', error);
            showMessage('An error occurred during login. Please try again later.', true);
        }
    });
});
