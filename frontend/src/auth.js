import { apiClient } from './api/client.js';

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
      return { 
        success: false, 
        error: this.getErrorMessage(error) 
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
      return { 
        success: false, 
        error: this.getErrorMessage(error) 
      };
    }
  }

  async logout() {
    await apiClient.logout();
    this.isAuthenticated = false;
    this.notifyListeners();
  }

  getErrorMessage(error) {
    switch (error.status) {
      case 400:
        return 'Неверные данные. Проверьте email и пароль.';
      case 401:
        return 'Неверный email или пароль.';
      case 409:
        return 'Пользователь с таким email уже существует.';
      case 0:
        return 'Ошибка сети. Проверьте подключение к интернету.';
      default:
        return 'Произошла ошибка. Попробуйте еще раз.';
    }
  }
}

export const authManager = new AuthManager();