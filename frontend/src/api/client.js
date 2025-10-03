import { config } from '../config.js';

class APIClient {
  constructor(baseURL = config.apiBaseUrl) {
    this.baseURL = baseURL;
    this.accessToken = localStorage.getItem('accessToken');
    this.refreshToken = localStorage.getItem('refreshToken');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const requestConfig = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (this.accessToken) {
      requestConfig.headers.Authorization = `Bearer ${this.accessToken}`;
    }

    try {
      const response = await fetch(url, requestConfig);
      
      if (response.status === 401 && this.refreshToken) {
        const refreshed = await this.refreshTokens();
        if (refreshed) {
          requestConfig.headers.Authorization = `Bearer ${this.accessToken}`;
          return await fetch(url, requestConfig);
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new APIError(response.status, errorData.message || 'Request failed');
      }

      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      throw new APIError(0, 'Network error');
    }
  }

  async register(email, password) {
    const response = await this.request('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    
    this.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  async login(email, password) {
    const response = await this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    
    this.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  async logout() {
    try {
      await this.request('/api/v1/auth/logout', {
        method: 'POST',
      });
    } catch (error) {
      console.warn('Logout request failed:', error);
    } finally {
      this.clearTokens();
    }
  }

  async refreshTokens() {
    if (!this.refreshToken) {
      return false;
    }

    try {
      const response = await this.request('/api/v1/auth/tokens/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      
      this.setTokens(response.access_token, response.refresh_token);
      return true;
    } catch (error) {
      this.clearTokens();
      return false;
    }
  }

  async sendQuestion(text) {
    const response = await this.request('/api/v1/llm/question', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
    
    return response.text;
  }

  setTokens(accessToken, refreshToken) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  }

  isAuthenticated() {
    return !!this.accessToken;
  }
}

class APIError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = 'APIError';
  }
}

export const apiClient = new APIClient();
export { APIError };