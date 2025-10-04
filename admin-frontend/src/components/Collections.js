import { createElement } from '../core/utils.js';
import { ingestorAPIClient } from '../api/client.js';
import { getUserFriendlyError, logError } from '../utils/errorHandler.js';

export default function Collections() {
  const el = createElement("div", "admin-container");
  
  el.innerHTML = `
    <div class="admin-header">
      <div class="admin-title">
        <h1>Управление коллекциями</h1>
        <p>Просмотр и управление векторными коллекциями</p>
      </div>
      <div class="admin-actions">
        <button class="btn btn-secondary" id="backBtn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          Назад
        </button>
        <button class="theme-toggle" id="themeToggle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="admin-main">
      <div class="section">
        <div class="section-header">
          <h2>Коллекции</h2>
        </div>
        <div class="section-content">
          <div class="loading" id="loadingIndicator">
            <div class="spinner"></div>
            Загрузка коллекций...
          </div>
          
          <div id="collectionsContent" style="display: none;">
            <div class="table-container">
              <table class="table" id="collectionsTable">
                <thead>
                  <tr>
                    <th>Название</th>
                    <th>Статус</th>
                    <th>Документы</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody id="collectionsTableBody">
                </tbody>
              </table>
            </div>
          </div>
          
          <div class="empty-state" id="emptyState" style="display: none;">
            <h3>Коллекции не найдены</h3>
            <p>В системе пока нет векторных коллекций</p>
            <button class="btn btn-primary" id="refreshCollectionsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23,4 23,10 17,10"/>
                <polyline points="1,20 1,14 7,14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
              Обновить
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  
  setupCollectionsInteractions(el);
  loadCollections(el);
  
  return el;
}

function setupCollectionsInteractions(container) {
  const backBtn = container.querySelector('#backBtn');
  const themeToggle = container.querySelector('#themeToggle');
  const refreshCollectionsBtn = container.querySelector('#refreshCollectionsBtn');
  
  backBtn.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'dashboard' } }));
  });
  
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('admin-theme', newTheme);
  });
  
  refreshCollectionsBtn.addEventListener('click', () => {
    loadCollections(container);
  });
}

async function loadCollections(container) {
  const loadingIndicator = container.querySelector('#loadingIndicator');
  const collectionsContent = container.querySelector('#collectionsContent');
  const emptyState = container.querySelector('#emptyState');
  const collectionsTableBody = container.querySelector('#collectionsTableBody');
  
  loadingIndicator.style.display = 'flex';
  collectionsContent.style.display = 'none';
  emptyState.style.display = 'none';
  
  try {
    const collectionsData = await ingestorAPIClient.listCollections();
    
    loadingIndicator.style.display = 'none';
    
    if (collectionsData.collections && collectionsData.collections.length > 0) {
      collectionsContent.style.display = 'block';
      renderCollectionsTable(collectionsTableBody, collectionsData.collections);
    } else {
      emptyState.style.display = 'block';
    }
    
  } catch (error) {
    logError(error, 'Collections.loadCollections');
    
    loadingIndicator.style.display = 'none';
    emptyState.style.display = 'block';
    
    const errorMessage = getUserFriendlyError(error);
    emptyState.innerHTML = `
      <h3>Ошибка загрузки</h3>
      <p>${errorMessage}</p>
      <button class="btn btn-primary" id="refreshCollectionsBtn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23,4 23,10 17,10"/>
          <polyline points="1,20 1,14 7,14"/>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
        </svg>
        Попробовать снова
      </button>
    `;
    
    const refreshBtn = emptyState.querySelector('#refreshCollectionsBtn');
    refreshBtn.addEventListener('click', () => {
      loadCollections(container);
    });
  }
}

function renderCollectionsTable(tbody, collections) {
  tbody.innerHTML = '';
  
  collections.forEach(collection => {
    const row = document.createElement('tr');
    
    const statusClass = getStatusClass(collection.status);
    const statusIcon = getStatusIcon(collection.status);
    
    row.innerHTML = `
      <td>
        <div style="font-weight: 500;">${collection.name}</div>
      </td>
      <td>
        <div class="status-indicator status-${statusClass}">
          ${statusIcon} ${collection.status}
        </div>
      </td>
      <td>
        <div>${collection.documents ? collection.documents.length : 0} документов</div>
      </td>
      <td>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-small btn-secondary" onclick="viewCollectionDetails('${collection.name}')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            Подробнее
          </button>
        </div>
      </td>
    `;
    
    tbody.appendChild(row);
  });
}

function getStatusClass(status) {
  switch (status?.toLowerCase()) {
    case 'healthy':
    case 'ok':
    case 'active':
      return 'healthy';
    case 'warning':
    case 'degraded':
      return 'warning';
    case 'error':
    case 'failed':
    case 'down':
      return 'error';
    default:
      return 'unknown';
  }
}

function getStatusIcon(status) {
  switch (status?.toLowerCase()) {
    case 'healthy':
    case 'ok':
    case 'active':
      return '✓';
    case 'warning':
    case 'degraded':
      return '⚠';
    case 'error':
    case 'failed':
    case 'down':
      return '✗';
    default:
      return '?';
  }
}

window.viewCollectionDetails = function(collectionName) {
  window.dispatchEvent(new CustomEvent('navigate', { 
    detail: { page: 'documents', collection: collectionName } 
  }));
};