import { createElement } from '../core/utils.js';
import { ingestorAPIClient } from '../api/client.js';
import { getUserFriendlyError, logError } from '../utils/errorHandler.js';
import { formatFileSize } from '../core/utils.js';

export default function Upload() {
  const el = createElement("div", "admin-container");
  
  el.innerHTML = `
    <div class="admin-header">
      <div class="admin-title">
        <h1>Загрузка файлов</h1>
        <p>Загрузка документов в векторную базу данных</p>
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
          <h2>Загрузка файлов</h2>
        </div>
        <div class="section-content">
          <form id="uploadForm">
            <div class="form-group">
              <label for="collectionName">Коллекция</label>
              <select id="collectionName" required>
                <option value="">Выберите коллекцию</option>
                <option value="default">default</option>
              </select>
            </div>
            
            <div class="form-group">
              <label for="metadata">Метаданные (JSON)</label>
              <textarea id="metadata" placeholder='{"source": "admin", "version": "1.0"}'></textarea>
            </div>
            
            <div class="form-group">
              <label>Файлы для загрузки</label>
              <div class="file-upload" id="fileUpload">
                <input type="file" id="fileInput" multiple accept=".pdf,.txt,.docx,.md,.html">
                <div>
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom: 16px; color: var(--muted);">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7,10 12,15 17,10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  <p style="margin-bottom: 8px; font-weight: 500;">Перетащите файлы сюда или нажмите для выбора</p>
                  <p style="color: var(--muted); font-size: 14px;">Поддерживаемые форматы: PDF, TXT, DOCX, MD, HTML</p>
                </div>
              </div>
            </div>
            
            <div class="file-list" id="fileList" style="display: none;">
            </div>
            
            <div class="form-group">
              <button type="submit" class="btn btn-primary btn-large" id="uploadBtn">
                <div class="loading" id="uploadLoading" style="display: none;">
                  <div class="spinner"></div>
                  Загрузка...
                </div>
                <span id="uploadText">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7,10 12,15 17,10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  Загрузить файлы
                </span>
              </button>
            </div>
          </form>
          
          <div id="uploadResults" style="display: none;">
          </div>
        </div>
      </div>
    </div>
  `;
  
  setupUploadInteractions(el);
  loadCollections(el);
  
  return el;
}

function setupUploadInteractions(container) {
  const backBtn = container.querySelector('#backBtn');
  const themeToggle = container.querySelector('#themeToggle');
  const fileUpload = container.querySelector('#fileUpload');
  const fileInput = container.querySelector('#fileInput');
  const fileList = container.querySelector('#fileList');
  const uploadForm = container.querySelector('#uploadForm');
  const uploadBtn = container.querySelector('#uploadBtn');
  const uploadLoading = container.querySelector('#uploadLoading');
  const uploadText = container.querySelector('#uploadText');
  const uploadResults = container.querySelector('#uploadResults');
  
  backBtn.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'dashboard' } }));
  });
  
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('admin-theme', newTheme);
  });
  
  fileUpload.addEventListener('click', () => {
    fileInput.click();
  });
  
  fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files, container);
  });
  
  fileUpload.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileUpload.classList.add('dragover');
  });
  
  fileUpload.addEventListener('dragleave', () => {
    fileUpload.classList.remove('dragover');
  });
  
  fileUpload.addEventListener('drop', (e) => {
    e.preventDefault();
    fileUpload.classList.remove('dragover');
    handleFiles(e.dataTransfer.files, container);
  });
  
  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const collectionSelect = container.querySelector('#collectionName');
    const newCollectionInput = container.querySelector('#newCollectionName');
    const metadataText = container.querySelector('#metadata').value;
    const files = Array.from(fileInput.files);
    
    let collectionName = collectionSelect.value;
    
    // Если выбрано создание новой коллекции
    if (!collectionName && newCollectionInput.style.display === 'block') {
      collectionName = newCollectionInput.value.trim();
      if (!collectionName) {
        alert('Пожалуйста, введите название новой коллекции');
        return;
      }
    }
    
    if (!collectionName) {
      alert('Пожалуйста, выберите коллекцию или введите название новой');
      return;
    }
    
    if (files.length === 0) {
      alert('Пожалуйста, выберите файлы для загрузки');
      return;
    }
    
    let metadata = {};
    if (metadataText.trim()) {
      try {
        metadata = JSON.parse(metadataText);
      } catch (error) {
        alert('Неверный формат JSON в метаданных');
        return;
      }
    }
    
    uploadLoading.style.display = 'flex';
    uploadText.style.display = 'none';
    uploadBtn.disabled = true;
    
    try {
      const result = await ingestorAPIClient.ingestFiles(files, collectionName, metadata);
      showUploadResults(result, uploadResults);
      
      // Обновляем список коллекций после успешной загрузки
      loadCollections(container);
    } catch (error) {
      logError(error, 'Upload.uploadFiles');
      alert(`Ошибка загрузки: ${getUserFriendlyError(error)}`);
    } finally {
      uploadLoading.style.display = 'none';
      uploadText.style.display = 'flex';
      uploadBtn.disabled = false;
    }
  });
}

function handleFiles(files, container) {
  const fileList = container.querySelector('#fileList');
  
  if (files.length === 0) {
    fileList.style.display = 'none';
    return;
  }
  
  fileList.style.display = 'block';
  fileList.innerHTML = '';
  
  Array.from(files).forEach(file => {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    
    fileItem.innerHTML = `
      <div class="file-info">
        <div class="file-name">${file.name}</div>
        <div class="file-size">${formatFileSize(file.size)}</div>
      </div>
      <button class="file-remove" onclick="removeFile(this)">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    `;
    
    fileList.appendChild(fileItem);
  });
}

function showUploadResults(result, container) {
  container.style.display = 'block';
  
  const successCount = result.successful_files || 0;
  const failedCount = result.failed_files || 0;
  const totalCount = result.total_files || 0;
  
  let resultsHTML = `
    <div class="section">
      <div class="section-header">
        <h2>Результаты загрузки</h2>
      </div>
      <div class="section-content">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <div class="dashboard-card">
            <h3>Всего файлов</h3>
            <div class="dashboard-stat">${totalCount}</div>
          </div>
          <div class="dashboard-card">
            <h3>Успешно</h3>
            <div class="dashboard-stat" style="color: var(--success);">${successCount}</div>
          </div>
          <div class="dashboard-card">
            <h3>Ошибки</h3>
            <div class="dashboard-stat" style="color: var(--error);">${failedCount}</div>
          </div>
        </div>
  `;
  
  if (result.items && result.items.length > 0) {
    resultsHTML += `
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>Файл</th>
              <th>ID документа</th>
              <th>Статус</th>
              <th>Ошибка</th>
            </tr>
          </thead>
          <tbody>
    `;
    
    result.items.forEach(item => {
      const statusClass = item.status === 'success' ? 'success' : 'error';
      const statusIcon = item.status === 'success' ? '✓' : '✗';
      
      resultsHTML += `
        <tr>
          <td>${item.filename}</td>
          <td style="font-family: monospace;">${item.doc_id}</td>
          <td>
            <div class="status-indicator status-${statusClass}">
              ${statusIcon} ${item.status}
            </div>
          </td>
          <td>${item.error || '-'}</td>
        </tr>
      `;
    });
    
    resultsHTML += `
          </tbody>
        </table>
      </div>
    `;
  }
  
  resultsHTML += `
      </div>
    </div>
  `;
  
  container.innerHTML = resultsHTML;
}

async function loadCollections(container) {
  const collectionSelect = container.querySelector('#collectionName');
  
  try {
    const collectionsData = await ingestorAPIClient.listCollections();
    
    collectionSelect.innerHTML = '<option value="">Выберите коллекцию</option>';
    
    if (collectionsData.collections && collectionsData.collections.length > 0) {
      collectionsData.collections.forEach(collection => {
        const option = document.createElement('option');
        option.value = collection.name;
        option.textContent = `${collection.name} (${collection.documents ? collection.documents.length : 0} документов)`;
        collectionSelect.appendChild(option);
      });
    }
    
    // Добавляем опцию для создания новой коллекции
    const newCollectionOption = document.createElement('option');
    newCollectionOption.value = '';
    newCollectionOption.textContent = 'Создать новую коллекцию';
    newCollectionOption.disabled = true;
    collectionSelect.appendChild(newCollectionOption);
    
    // Добавляем поле для ввода названия новой коллекции
    const newCollectionInput = document.createElement('input');
    newCollectionInput.type = 'text';
    newCollectionInput.placeholder = 'Введите название новой коллекции';
    newCollectionInput.style.display = 'none';
    newCollectionInput.style.marginTop = '8px';
    newCollectionInput.id = 'newCollectionName';
    
    collectionSelect.parentElement.appendChild(newCollectionInput);
    
    // Обработчик изменения выбора коллекции
    collectionSelect.addEventListener('change', (e) => {
      if (e.target.value === '') {
        newCollectionInput.style.display = 'block';
        newCollectionInput.required = true;
      } else {
        newCollectionInput.style.display = 'none';
        newCollectionInput.required = false;
      }
    });
    
  } catch (error) {
    logError(error, 'Upload.loadCollections');
    
    collectionSelect.innerHTML = '<option value="">Выберите коллекцию</option>';
    
    const defaultOption = document.createElement('option');
    defaultOption.value = 'default';
    defaultOption.textContent = 'default (будет создана)';
    collectionSelect.appendChild(defaultOption);
  }
}

window.removeFile = function(button) {
  const fileItem = button.closest('.file-item');
  const fileList = fileItem.parentElement;
  
  fileItem.remove();
  
  if (fileList.children.length === 0) {
    fileList.style.display = 'none';
  }
};