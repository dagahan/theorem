import { createElement } from '../core/utils.js';
import { ingestorAPIClient } from '../api/client.js';
import { servicesAPIClient } from '../api/servicesClient.js';
import { getUserFriendlyError, logError } from '../utils/errorHandler.js';

export default function Dashboard() {
  const el = createElement("div", "admin-container");
  
  el.innerHTML = `
    <div class="admin-header">
      <div class="admin-title">
        <h1>Theorem Admin</h1>
        <p>Управление RAG базой данных</p>
      </div>
      <div class="admin-actions">
        <button class="theme-toggle" id="themeToggle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="admin-main">
      <div class="dashboard-grid" id="dashboardGrid">
        <div class="dashboard-card">
          <h3>Ingestor</h3>
          <p>Сервис инжеста документов</p>
          <div class="status-indicator status-unknown" id="ingestorStatus">
            <div class="spinner"></div>
            Проверка...
          </div>
        </div>
        
        <div class="dashboard-card">
          <h3>Gateway</h3>
          <p>Основной шлюз API</p>
          <div class="status-indicator status-unknown" id="gatewayStatus">
            <div class="spinner"></div>
            Проверка...
          </div>
        </div>
        
        <div class="dashboard-card">
          <h3>Qdrant</h3>
          <p>Векторная база данных</p>
          <div class="status-indicator status-unknown" id="qdrantStatus">
            <div class="spinner"></div>
            Проверка...
          </div>
        </div>
        
        
        <div class="dashboard-card">
          <h3>Коллекции</h3>
          <p>Количество векторных коллекций</p>
          <div class="dashboard-stat" id="collectionsCount">-</div>
        </div>
        
        <div class="dashboard-card">
          <h3>Векторы</h3>
          <p>Общее количество векторов</p>
          <div class="dashboard-stat" id="vectorsCount">-</div>
        </div>
        
        <div class="dashboard-card">
          <h3>Размерность</h3>
          <p>Размерность векторов</p>
          <div class="dashboard-stat-small" id="vectorDimensions">-</div>
        </div>
      </div>
      
      <div class="section">
        <div class="section-header">
          <h2>Быстрые действия</h2>
        </div>
        <div class="section-content">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
            <button class="btn btn-primary" id="refreshStatsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23,4 23,10 17,10"/>
                <polyline points="1,20 1,14 7,14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
              Обновить статистику
            </button>
            <button class="btn btn-secondary" id="manageCollectionsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18l-2 13H5L3 6z"/>
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
              Управление коллекциями
            </button>
            <button class="btn btn-success" id="uploadFilesBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7,10 12,15 17,10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Загрузить файлы
            </button>
            <button class="btn btn-warning" id="manageDocumentsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10,9 9,9 8,9"/>
              </svg>
              Управление документами
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  
  setupDashboardInteractions(el);
  loadDashboardData(el);
  
  return el;
}

function setupDashboardInteractions(container) {
  const themeToggle = container.querySelector('#themeToggle');
  const refreshStatsBtn = container.querySelector('#refreshStatsBtn');
  const manageCollectionsBtn = container.querySelector('#manageCollectionsBtn');
  const uploadFilesBtn = container.querySelector('#uploadFilesBtn');
  const manageDocumentsBtn = container.querySelector('#manageDocumentsBtn');
  
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('admin-theme', newTheme);
  });
  
  refreshStatsBtn.addEventListener('click', () => {
    loadDashboardData(container);
  });
  
  manageCollectionsBtn.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'collections' } }));
  });
  
  uploadFilesBtn.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'upload' } }));
  });
  
  manageDocumentsBtn.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'documents' } }));
  });
}

async function loadDashboardData(container) {
  const ingestorStatus = container.querySelector('#ingestorStatus');
  const gatewayStatus = container.querySelector('#gatewayStatus');
  const qdrantStatus = container.querySelector('#qdrantStatus');
  const collectionsCount = container.querySelector('#collectionsCount');
  const vectorsCount = container.querySelector('#vectorsCount');
  const vectorDimensions = container.querySelector('#vectorDimensions');
  
  try {
    // Загружаем данные от всех сервисов параллельно
    const [servicesHealth, ingestorStats, ingestorCollections] = await Promise.allSettled([
      servicesAPIClient.getAllServicesHealth(),
      ingestorAPIClient.getServiceStats(),
      ingestorAPIClient.listCollections()
    ]);
    
    // Обновляем статусы сервисов
    if (servicesHealth.status === 'fulfilled') {
      const healthData = servicesHealth.value;
      
      healthData.forEach(service => {
        const statusElement = container.querySelector(`#${service.name.toLowerCase().replace(/\s+/g, '')}Status`);
        if (statusElement) {
          statusElement.className = `status-indicator status-${getStatusClass(service.status)}`;
          statusElement.innerHTML = `${getStatusIcon(service.status)} ${service.status === 'healthy' ? 'Работает' : 'Ошибка'}`;
        }
      });
    }
    
    // Обновляем данные инжестора
    if (ingestorStats.status === 'fulfilled') {
      const statsData = ingestorStats.value;
      vectorsCount.textContent = statsData.total_vectors || 0;
      vectorDimensions.textContent = statsData.hybrid_embedder_dim || 0;
    }
    
    if (ingestorCollections.status === 'fulfilled') {
      const collectionsData = ingestorCollections.value;
      collectionsCount.textContent = collectionsData.total_collections || 0;
    }
    
    // Проверяем статус инжестора отдельно
    try {
      await ingestorAPIClient.healthCheck();
      ingestorStatus.className = 'status-indicator status-healthy';
      ingestorStatus.innerHTML = '✓ Работает';
    } catch (error) {
      ingestorStatus.className = 'status-indicator status-error';
      ingestorStatus.innerHTML = '✗ Ошибка';
    }
    
  } catch (error) {
    logError(error, 'Dashboard.loadDashboardData');
    
    // Устанавливаем статус ошибки для всех сервисов
    [ingestorStatus, gatewayStatus, qdrantStatus].forEach(statusEl => {
      if (statusEl) {
        statusEl.className = 'status-indicator status-error';
        statusEl.innerHTML = '✗ Ошибка';
      }
    });
    
    collectionsCount.textContent = '-';
    vectorsCount.textContent = '-';
    vectorDimensions.textContent = '-';
  }
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