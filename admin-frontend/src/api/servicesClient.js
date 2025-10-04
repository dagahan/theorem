import { config } from '../config.js';

class ServicesAPIClient {
  constructor() {
    this.timeout = 10000;
  }

  async request(url, options = {}) {
    const requestConfig = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
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
        throw new APIError(0, 'Ошибка сети. Проверьте подключение к сервису.');
      } else if (error.name === 'AbortError') {
        throw new APIError(504, 'Превышено время ожидания ответа.');
      } else {
        throw new APIError(0, 'Ошибка сети. Попробуйте еще раз.');
      }
    }
  }

  // Gateway API
  async getGatewayHealth() {
    // Gateway может не иметь /health эндпоинта, проверяем доступность
    try {
      const response = await fetch(`${config.gatewayApiBaseUrl}/health`, { 
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });
      if (response.ok) {
        return await response.json();
      } else {
        return { status: 'unknown', message: 'Gateway доступен, но health endpoint не найден' };
      }
    } catch (error) {
      throw new APIError(0, 'Gateway недоступен');
    }
  }

  async getGatewayStats() {
    return await this.request(`${config.gatewayApiBaseUrl}/stats`);
  }

  // Qdrant API
  async getQdrantHealth() {
    // Qdrant не имеет /health, но /collections работает
    try {
      const collections = await this.request(`${config.qdrantApiBaseUrl}/collections`);
      return { status: 'healthy', collections: collections.result?.collections?.length || 0 };
    } catch (error) {
      throw new APIError(0, 'Qdrant недоступен');
    }
  }

  async getQdrantCollections() {
    return await this.request(`${config.qdrantApiBaseUrl}/collections`);
  }

  async getQdrantCollectionInfo(collectionName) {
    return await this.request(`${config.qdrantApiBaseUrl}/collections/${collectionName}`);
  }

  async getQdrantCollectionStats(collectionName) {
    return await this.request(`${config.qdrantApiBaseUrl}/collections/${collectionName}/points/count`);
  }

  // VLLM Math API
  async getVllmMathHealth() {
    return await this.request(`${config.vllmMathApiBaseUrl}/health`);
  }

  async getVllmMathStats() {
    return await this.request(`${config.vllmMathApiBaseUrl}/stats`);
  }

  // VLLM Talking API
  async getVllmTalkingHealth() {
    return await this.request(`${config.vllmTalkingApiBaseUrl}/health`);
  }

  async getVllmTalkingStats() {
    return await this.request(`${config.vllmTalkingApiBaseUrl}/stats`);
  }

  // Combined health check for all services
  async getAllServicesHealth() {
    const results = await Promise.allSettled([
      // Gateway health check
      (async () => {
        try {
          const health = await this.getGatewayHealth();
          return {
            name: 'Gateway',
            status: 'healthy',
            url: config.gatewayApiBaseUrl,
            data: health
          };
        } catch (error) {
          return {
            name: 'Gateway',
            status: 'error',
            url: config.gatewayApiBaseUrl,
            error: error.message
          };
        }
      })(),
      
      // Qdrant health check
      (async () => {
        try {
          const health = await this.getQdrantHealth();
          return {
            name: 'Qdrant',
            status: 'healthy',
            url: config.qdrantApiBaseUrl,
            data: health
          };
        } catch (error) {
          return {
            name: 'Qdrant',
            status: 'error',
            url: config.qdrantApiBaseUrl,
            error: error.message
          };
        }
      })()
    ]);

    return results.map(result => result.value || result.reason);
  }

  // Get comprehensive system stats
  async getSystemStats() {
    try {
      const [gatewayStats, qdrantCollections, vllmMathStats, vllmTalkingStats] = await Promise.allSettled([
        this.getGatewayStats(),
        this.getQdrantCollections(),
        this.getVllmMathStats(),
        this.getVllmTalkingStats()
      ]);

      return {
        gateway: gatewayStats.status === 'fulfilled' ? gatewayStats.value : null,
        qdrant: qdrantCollections.status === 'fulfilled' ? qdrantCollections.value : null,
        vllmMath: vllmMathStats.status === 'fulfilled' ? vllmMathStats.value : null,
        vllmTalking: vllmTalkingStats.status === 'fulfilled' ? vllmTalkingStats.value : null,
      };
    } catch (error) {
      throw new APIError(0, `Ошибка получения статистики системы: ${error.message}`);
    }
  }
}

class APIError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = 'APIError';
  }
}

export const servicesAPIClient = new ServicesAPIClient();
export { APIError };