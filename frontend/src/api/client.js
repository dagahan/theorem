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

    // Добавляем таймаут для запросов
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.apiTimeout);
    requestConfig.signal = controller.signal;

    if (this.accessToken) {
      requestConfig.headers.Authorization = `Bearer ${this.accessToken}`;
    }

    try {
      const response = await fetch(url, requestConfig);
      clearTimeout(timeoutId);
      
      if (response.status === 401 && this.refreshToken) {
        const refreshed = await this.refreshTokens();
        if (refreshed) {
          requestConfig.headers.Authorization = `Bearer ${this.accessToken}`;
          return await fetch(url, requestConfig);
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.message || errorData.error || 'Request failed';
        throw new APIError(response.status, message);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof APIError) {
        throw error;
      }
      
      // Обработка различных типов сетевых ошибок
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new APIError(0, 'Ошибка сети. Проверьте подключение к интернету.');
      } else if (error.name === 'AbortError') {
        throw new APIError(504, 'Превышено время ожидания ответа.');
      } else {
        throw new APIError(0, 'Ошибка сети. Попробуйте еще раз.');
      }
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