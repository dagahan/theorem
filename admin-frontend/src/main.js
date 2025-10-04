import Dashboard from './components/Dashboard.js';
import Collections from './components/Collections.js';
import Documents from './components/Documents.js';
import Upload from './components/Upload.js';

class AdminApp {
  constructor() {
    this.currentPage = 'dashboard';
    this.currentParams = {};
    this.app = document.getElementById('app');
    this.init();
  }

  init() {
    this.setupNavigation();
    this.navigateTo('dashboard');
  }

  setupNavigation() {
    window.addEventListener('navigate', (event) => {
      const { page, ...params } = event.detail;
      this.navigateTo(page, params);
    });
  }

  navigateTo(page, params = {}) {
    this.currentPage = page;
    this.currentParams = params;
    
    let component;
    
    switch (page) {
      case 'dashboard':
        component = Dashboard();
        break;
      case 'collections':
        component = Collections();
        break;
      case 'documents':
        component = Documents(params.collection);
        break;
      case 'upload':
        component = Upload();
        break;
      default:
        component = Dashboard();
    }
    
    this.app.innerHTML = '';
    this.app.appendChild(component);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new AdminApp();
});