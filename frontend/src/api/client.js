import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.response.use(
  (response) => {
    // Reject HTML responses that indicate the API URL is misconfigured
    // (e.g. SPA fallback serving index.html instead of JSON)
    if (typeof response.data === 'string' && response.data.trimStart().startsWith('<!')) {
      return Promise.reject(new Error(
        'API returned HTML instead of JSON. Ensure VITE_API_BASE_URL is set to the backend URL.'
      ));
    }
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default client;
