/**
 * API Client with Error Handling
 * Provides safe fetch wrapper with automatic error handling and user-friendly messages
 */

class APIClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
    this.maxRetries = 2;
    this.retryDelay = 1000; // ms
  }

  /**
   * Make API request with error handling
   * @param {string} endpoint - API endpoint (e.g., '/api/market/live')
   * @param {object} options - Fetch options (method, body, headers, etc.)
   * @returns {Promise<object>} Parsed response or error object
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    let lastError = null;

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            ...options.headers
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'error') {
          throw new Error(data.error?.message || data.error || 'Unknown error');
        }

        return data.data || data; // Return data or full response

      } catch (error) {
        lastError = error;
        console.error(`❌ API Error (Attempt ${attempt}/${this.maxRetries}):`, error.message);

        if (attempt < this.maxRetries) {
          console.log(`⏳ Retrying in ${this.retryDelay}ms...`);
          await new Promise(resolve => setTimeout(resolve, this.retryDelay));
        }
      }
    }

    // All retries failed
    return {
      error: true,
      message: lastError?.message || 'API request failed',
      details: lastError
    };
  }

  /**
   * GET request helper
   */
  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  /**
   * POST request helper
   */
  async post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  /**
   * Show error message to user
   */
  showError(message, title = 'Error') {
    const errorElement = document.getElementById('errorMessage');
    if (errorElement) {
      errorElement.innerHTML = `<strong>${title}:</strong> ${message}`;
      errorElement.style.display = 'block';
      console.error(`${title}: ${message}`);
    }
  }

  /**
   * Clear error message
   */
  clearError() {
    const errorElement = document.getElementById('errorMessage');
    if (errorElement) {
      errorElement.style.display = 'none';
      errorElement.innerHTML = '';
    }
  }

  /**
   * Automatically handle response and show errors
   */
  async request WithErrorHandling(endpoint, options = {}, errorDisplay = true) {
    const response = await this.request(endpoint, options);

    if (response.error) {
      if (errorDisplay) {
        this.showError(response.message);
      }
      return null;
    }

    this.clearError();
    return response;
  }
}

// Create global instance
const api = new APIClient(window.API_BASE_URL || 'http://localhost:5001');

// Helper: Display API error with UI feedback
function handleAPIError(error, context = '') {
  console.error(`❌ ${context}:`, error);

  let userMessage = 'Something went wrong. Please try again.';

  if (error.message.includes('401') || error.message.includes('Unauthorized')) {
    userMessage = 'Session expired. Please log in again.';
    window.location.href = '/login';
  } else if (error.message.includes('404')) {
    userMessage = 'Resource not found.';
  } else if (error.message.includes('500')) {
    userMessage = 'Server error. Please try again later.';
  } else if (error.message.includes('Failed to fetch')) {
    userMessage = 'Network error. Please check your connection.';
  } else if (error.message) {
    userMessage = error.message;
  }

  api.showError(userMessage, context);
  return null;
}

// Helper: Safely get data from API
async function safeAPICall(fn, context = 'API Call') {
  try {
    return await fn();
  } catch (error) {
    handleAPIError(error, context);
    return null;
  }
}
