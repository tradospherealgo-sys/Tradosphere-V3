/**
 * Frontend Configuration
 * Sets the API base URL for all API requests
 */

// Development environment
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.API_BASE_URL = 'http://localhost:5001';
}
// Production environment (Render backend)
else if (window.location.hostname.includes('vercel.app') || window.location.hostname.includes('tradosphere.in')) {
    window.API_BASE_URL = 'https://tradosphere.onrender.com'; // UPDATE THIS WITH YOUR RENDER URL
}
// Render deployment
else if (window.location.hostname.includes('onrender.com') || window.location.hostname.includes('render.com')) {
    window.API_BASE_URL = 'https://tradosphere.onrender.com'; // UPDATE THIS WITH YOUR RENDER BACKEND URL
}
// Fallback
else {
    window.API_BASE_URL = 'http://localhost:5001';
}

console.log('API Base URL:', window.API_BASE_URL);
