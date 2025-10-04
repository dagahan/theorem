import { createElement } from '../core/utils.js';
import { ingestorAPIClient } from '../api/client.js';
import { getUserFriendlyError, logError } from '../utils/errorHandler.js';
import { formatFileSize } from '../core/utils.js';

export default function Documents(collectionName = null) {
  const el = createElement("div", "admin-container");
  
  el.innerHTML = `
    <div class="admin-header">
      <div class="admin-title">
        <h1>Управление документами</h1>
        <p>${collectionName ? `Коллекция: ${collectionName}` : 'Просмотр и управление документами'}</p>
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
          <h2>Документы</h2>
        </div>
        <div class="section-content">
          <div class="loading" id="loadingIndicator">
            <div class="spinner"></div>
            Загрузка документов...
          </div>
          
          <div id="documentsContent" style="display: none;">
            <div class="table-container">
              <table class="table" id="documentsTable">
                <thead>
                  <tr>
                    <th>
                      <input type="checkbox" id="selectAllCheckbox">
                    </th>
                    <th>ID документа</th>
                    <th>Чанки</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody id="documentsTableBody">
                </tbody>
              </table>
            </div>
            
            <div style="margin-top: 16px; display: flex; gap: 12px; align-items: center;">
              <button class="btn btn-error" id="deleteSelectedBtn" disabled>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3,6 5,6 21,6"/>
                  <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"/>
                </svg>
                Удалить выбранные
              </button>
              <span id="selectedCount" style="color: var(--muted); font-size: 14px;">0 выбрано</span>
            </div>
          </div>
          
          <div class="empty-state" id="emptyState" style="display: none;">
            <h3>Документы не найдены</h3>
            <p>В коллекции пока нет документов</p>
            <button class="btn btn-primary" id="refreshDocumentsBtn">
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
  
  setupDocumentsInteractions(el, collectionName);
  loadDocuments(el, collectionName);
  
  return el;
}

function setupDocumentsInteractions(container, collectionName) {
  const backBtn = container.querySelector('#backBtn');
  const themeToggle = container.querySelector('#themeToggle');
  const refreshDocumentsBtn = container.querySelector('#refreshDocumentsBtn');
  const selectAllCheckbox = container.querySelector('#selectAllCheckbox');
  const deleteSelectedBtn = container.querySelector('#deleteSelectedBtn');
  const selectedCount = container.querySelector('#selectedCount');
  
  backBtn.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'collections' } }));
  });
  
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('admin-theme', newTheme);
  });
  
  refreshDocumentsBtn.addEventListener('click', () => {
    loadDocuments(container, collectionName);
  });
  
  selectAllCheckbox.addEventListener('change', () => {
    const checkboxes = container.querySelectorAll('input[type="checkbox"]:not(#selectAllCheckbox)');
    checkboxes.forEach(checkbox => {
      checkbox.checked = selectAllCheckbox.checked;
    });
    updateSelectedCount(container);
  });
  
  deleteSelectedBtn.addEventListener('click', () => {
    const selectedIds = getSelectedDocumentIds(container);
    if (selectedIds.length > 0) {
      showDeleteConfirmation(selectedIds, collectionName, container);
    }
  });
  
  container.addEventListener('change', (e) => {
    if (e.target.type === 'checkbox' && e.target !== selectAllCheckbox) {
      updateSelectedCount(container);
    }
  });
}

function updateSelectedCount(container) {
  const selectedIds = getSelectedDocumentIds(container);
  const selectedCount = container.querySelector('#selectedCount');
  const deleteSelectedBtn = container.querySelector('#deleteSelectedBtn');
  
  selectedCount.textContent = `${selectedIds.length} выбрано`;
  deleteSelectedBtn.disabled = selectedIds.length === 0;
}

function getSelectedDocumentIds(container) {
  const checkboxes = container.querySelectorAll('input[type="checkbox"]:not(#selectAllCheckbox):checked');
  return Array.from(checkboxes).map(checkbox => checkbox.dataset.docId);
}

async function loadDocuments(container, collectionName) {
  const loadingIndicator = container.querySelector('#loadingIndicator');
  const documentsContent = container.querySelector('#documentsContent');
  const emptyState = container.querySelector('#emptyState');
  const documentsTableBody = container.querySelector('#documentsTableBody');
  
  loadingIndicator.style.display = 'flex';
  documentsContent.style.display = 'none';
  emptyState.style.display = 'none';
  
  try {
    const collectionsData = await ingestorAPIClient.listCollections();
    
    loadingIndicator.style.display = 'none';
    
    let documents = [];
    if (collectionName) {
      const collection = collectionsData.collections.find(c => c.name === collectionName);
      documents = collection ? collection.documents : [];
    } else {
      documents = collectionsData.collections.flatMap(c => c.documents || []);
    }
    
    if (documents.length > 0) {
      documentsContent.style.display = 'block';
      await renderDocumentsTable(documentsTableBody, documents, collectionName);
    } else {
      emptyState.style.display = 'block';
    }
    
  } catch (error) {
    logError(error, 'Documents.loadDocuments');
    
    loadingIndicator.style.display = 'none';
    emptyState.style.display = 'block';
    
    const errorMessage = getUserFriendlyError(error);
    emptyState.innerHTML = `
      <h3>Ошибка загрузки</h3>
      <p>${errorMessage}</p>
      <button class="btn btn-primary" id="refreshDocumentsBtn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23,4 23,10 17,10"/>
          <polyline points="1,20 1,14 7,14"/>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
        </svg>
        Попробовать снова
      </button>
    `;
    
    const refreshBtn = emptyState.querySelector('#refreshDocumentsBtn');
    refreshBtn.addEventListener('click', () => {
      loadDocuments(container, collectionName);
    });
  }
}

async function renderDocumentsTable(tbody, documents, collectionName) {
  tbody.innerHTML = '';
  
  for (const docId of documents) {
    const row = document.createElement('tr');
    
    try {
      const docInfo = await ingestorAPIClient.getDocumentInfo(docId, collectionName);
      
      row.innerHTML = `
        <td>
          <input type="checkbox" data-doc-id="${docId}">
        </td>
        <td>
          <div style="font-weight: 500; font-family: monospace;">${docId}</div>
        </td>
        <td>
          <div>${docInfo.chunks_count || 0} чанков</div>
        </td>
        <td>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-small btn-secondary" onclick="viewDocumentDetails('${docId}', '${collectionName || ''}')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              Подробнее
            </button>
            <button class="btn btn-small btn-error" onclick="deleteDocument('${docId}', '${collectionName || ''}')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3,6 5,6 21,6"/>
                <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"/>
              </svg>
              Удалить
            </button>
          </div>
        </td>
      `;
    } catch (error) {
      row.innerHTML = `
        <td>
          <input type="checkbox" data-doc-id="${docId}">
        </td>
        <td>
          <div style="font-weight: 500; font-family: monospace;">${docId}</div>
        </td>
        <td>
          <div style="color: var(--error);">Ошибка загрузки</div>
        </td>
        <td>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-small btn-error" onclick="deleteDocument('${docId}', '${collectionName || ''}')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3,6 5,6 21,6"/>
                <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"/>
              </svg>
              Удалить
            </button>
          </div>
        </td>
      `;
    }
    
    tbody.appendChild(row);
  }
}

function showDeleteConfirmation(docIds, collectionName, container) {
  const modal = createDeleteConfirmationModal(docIds, collectionName, container);
  document.body.appendChild(modal);
}

function createDeleteConfirmationModal(docIds, collectionName, container) {
  const modal = document.createElement('div');
  modal.className = 'modal active';
  
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>Подтверждение удаления</h3>
        <button class="modal-close" id="closeModal">×</button>
      </div>
      <div class="modal-body">
        <p>Вы уверены, что хотите удалить следующие документы?</p>
        <ul style="margin: 16px 0; padding-left: 20px;">
          ${docIds.map(id => `<li style="font-family: monospace;">${id}</li>`).join('')}
        </ul>
        <p style="color: var(--error); font-weight: 500;">Это действие нельзя отменить!</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="cancelDelete">Отмена</button>
        <button class="btn btn-error" id="confirmDelete">
          <div class="loading" id="deleteLoading" style="display: none;">
            <div class="spinner"></div>
            Удаление...
          </div>
          <span id="deleteText">Удалить</span>
        </button>
      </div>
    </div>
  `;
  
  const closeModal = modal.querySelector('#closeModal');
  const cancelDelete = modal.querySelector('#cancelDelete');
  const confirmDelete = modal.querySelector('#confirmDelete');
  const deleteLoading = modal.querySelector('#deleteLoading');
  const deleteText = modal.querySelector('#deleteText');
  
  const closeModalHandler = () => {
    document.body.removeChild(modal);
  };
  
  closeModal.addEventListener('click', closeModalHandler);
  cancelDelete.addEventListener('click', closeModalHandler);
  
  confirmDelete.addEventListener('click', async () => {
    deleteLoading.style.display = 'flex';
    deleteText.style.display = 'none';
    confirmDelete.disabled = true;
    
    try {
      await ingestorAPIClient.deleteDocuments(docIds, collectionName);
      closeModalHandler();
      loadDocuments(container, collectionName);
    } catch (error) {
      logError(error, 'Documents.deleteDocuments');
      alert(`Ошибка удаления: ${getUserFriendlyError(error)}`);
    } finally {
      deleteLoading.style.display = 'none';
      deleteText.style.display = 'inline';
      confirmDelete.disabled = false;
    }
  });
  
  return modal;
}

window.viewDocumentDetails = function(docId, collectionName) {
  window.dispatchEvent(new CustomEvent('navigate', { 
    detail: { page: 'document-details', docId, collectionName } 
  }));
};

window.deleteDocument = function(docId, collectionName) {
  showDeleteConfirmation([docId], collectionName, document.querySelector('.admin-container'));
};