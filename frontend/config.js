/**
 * Frontend Configuration
 * Sets the API base URL for all API requests
 */

// Development environment
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.API_BASE_URL = 'http://localhost:5001';
}
// Production environment
else if (window.location.hostname.includes('vercel.app') || window.location.hostname.includes('tradosphere.in')) {
    window.API_BASE_URL = 'https://api.tradosphere.in';
}
// Railway deployment
else if (window.location.hostname.includes('railway.app')) {
    window.API_BASE_URL = window.location.origin.replace('http://', 'https://');
}
// Fallback
else {
    window.API_BASE_URL = 'http://localhost:5001';
}

console.log('API Base URL:', window.API_BASE_URL);
