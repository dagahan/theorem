import { config } from '../config.js';

class IngestorAPIClient {
  constructor(baseURL = config.ingestorApiBaseUrl) {
    this.baseURL = baseURL;
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

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.ingestorApiTimeout);
    requestConfig.signal = controller.signal;

    try {
      const response = await fetch(url, requestConfig);
      clearTimeout(timeoutId);
      
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
      
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new APIError(0, 'Ошибка сети. Проверьте подключение к серверу инжестора.');
      } else if (error.name === 'AbortError') {
        throw new APIError(504, 'Превышено время ожидания ответа.');
      } else {
        throw new APIError(0, 'Ошибка сети. Попробуйте еще раз.');
      }
    }
  }

  async uploadRequest(endpoint, formData) {
    const url = `${this.baseURL}${endpoint}`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.ingestorApiTimeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.message || errorData.error || 'Upload failed';
        throw new APIError(response.status, message);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof APIError) {
        throw error;
      }
      
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new APIError(0, 'Ошибка сети. Проверьте подключение к серверу инжестора.');
      } else if (error.name === 'AbortError') {
        throw new APIError(504, 'Превышено время ожидания ответа.');
      } else {
        throw new APIError(0, 'Ошибка сети. Попробуйте еще раз.');
      }
    }
  }

  async healthCheck() {
    return await this.request('/health');
  }

  async getServiceStats() {
    return await this.request('/statistics/service_stats');
  }

  async listCollections() {
    return await this.request('/vector-store/list_collections');
  }

  async getDocumentInfo(docId, collectionName = null) {
    const params = new URLSearchParams();
    if (collectionName) {
      params.append('collection_name', collectionName);
    }
    const queryString = params.toString();
    const endpoint = `/vector-store/get_document_info/${docId}${queryString ? '?' + queryString : ''}`;
    return await this.request(endpoint);
  }

  async getDocumentEmbedded(docId, collectionName = null) {
    const params = new URLSearchParams();
    if (collectionName) {
      params.append('collection_name', collectionName);
    }
    const queryString = params.toString();
    const endpoint = `/vector-store/get_document_embedded/${docId}${queryString ? '?' + queryString : ''}`;
    return await this.request(endpoint);
  }

  async getDocumentText(docId, collectionName = null) {
    const params = new URLSearchParams();
    if (collectionName) {
      params.append('collection_name', collectionName);
    }
    const queryString = params.toString();
    const endpoint = `/vector-store/get_document_text/${docId}${queryString ? '?' + queryString : ''}`;
    return await this.request(endpoint);
  }

  async deleteDocuments(docIds, collectionName = null) {
    return await this.request('/ingestor/delete_documents', {
      method: 'DELETE',
      body: JSON.stringify({
        doc_ids: docIds,
        collection_name: collectionName
      }),
    });
  }

  async ingestFiles(files, collectionName, metadata = {}) {
    const formData = new FormData();
    
    files.forEach(file => {
      formData.append('files', file);
    });
    
    formData.append('collection_name', collectionName);
    
    if (metadata && Object.keys(metadata).length > 0) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    return await this.uploadRequest('/ingestor/ingest_files', formData);
  }
}

class APIError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = 'APIError';
  }
}

export const ingestorAPIClient = new IngestorAPIClient();
export { APIError };