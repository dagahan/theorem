import { apiClient } from './api/client.js';
import { getUserFriendlyError, logError } from './utils/errorHandler.js';

class AuthManager {
  constructor() {
    this.isAuthenticated = apiClient.isAuthenticated();
    this.listeners = [];
  }

  addAuthListener(callback) {
    this.listeners.push(callback);
  }

  removeAuthListener(callback) {
    this.listeners = this.listeners.filter(listener => listener !== callback);
  }

  notifyListeners() {
    this.listeners.forEach(callback => callback(this.isAuthenticated));
  }

  async login(email, password) {
    try {
      await apiClient.login(email, password);
      this.isAuthenticated = true;
      this.notifyListeners();
      return { success: true };
    } catch (error) {
      logError(error, 'AuthManager.login');
      return { 
        success: false, 
        error: getUserFriendlyError(error)
      };
    }
  }

  async register(email, password) {
    try {
      await apiClient.register(email, password);
      this.isAuthenticated = true;
      this.notifyListeners();
      return { success: true };
    } catch (error) {
      logError(error, 'AuthManager.register');
      return { 
        success: false, 
        error: getUserFriendlyError(error)
      };
    }
  }

  async logout() {
    await apiClient.logout();
    this.isAuthenticated = false;
    this.notifyListeners();
  }

}

export const authManager = new AuthManager();