/**
 * Frontend Configuration
 * Sets the API base URL for all API requests based on where the page is served.
 *
 * Override order:
 *   1. A pre-set window.API_BASE_URL (e.g. injected at build time) wins.
 *   2. localhost / 127.0.0.1            -> local dev backend.
 *   3. any other host (prod domain)     -> production Render backend.
 *
 * If you move the backend to a custom domain, change PROD_API_BASE_URL below.
 */
(function () {
    var PROD_API_BASE_URL = 'https://tradosphere-v3.onrender.com';
    var DEV_API_BASE_URL = 'http://localhost:5001';

    // Respect an explicit override if one was already set.
    if (window.API_BASE_URL) {
        console.log('API Base URL (override):', window.API_BASE_URL);
        return;
    }

    var host = window.location.hostname;
    var isLocal = (host === 'localhost' || host === '127.0.0.1' || host === '');

    // Production by default: only localhost uses the dev backend, so custom
    // domains (vercel.app, tradosphere.in, onrender.com, or anything else)
    // correctly hit the production API instead of falling back to localhost.
    window.API_BASE_URL = isLocal ? DEV_API_BASE_URL : PROD_API_BASE_URL;

    console.log('API Base URL:', window.API_BASE_URL);
})();
