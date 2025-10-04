export const config = {
  // API URLs
  ingestorApiBaseUrl: import.meta.env.VITE_INGESTOR_API_BASE_URL || 'http://localhost:50053',
  gatewayApiBaseUrl: import.meta.env.VITE_GATEWAY_API_BASE_URL || 'http://localhost:8080',
  qdrantApiBaseUrl: import.meta.env.VITE_QDRANT_API_BASE_URL || 'http://localhost:6333',
  vllmMathApiBaseUrl: import.meta.env.VITE_VLLM_MATH_API_BASE_URL || 'http://localhost:50054',
  vllmTalkingApiBaseUrl: import.meta.env.VITE_VLLM_TALKING_API_BASE_URL || 'http://localhost:50054',
  
  // Timeouts
  ingestorApiTimeout: import.meta.env.VITE_INGESTOR_API_TIMEOUT || 30000,
  
  // Frontend Configuration
  adminFrontendHost: import.meta.env.VITE_ADMIN_FRONTEND_HOST || '192.168.0.102',
  adminFrontendPort: import.meta.env.VITE_ADMIN_FRONTEND_PORT || '4174',
  adminFrontendProtocol: import.meta.env.VITE_ADMIN_FRONTEND_PROTOCOL || 'http',
  
  // Environment
  nodeEnv: import.meta.env.NODE_ENV || 'production',
  
  isDevelopment: import.meta.env.NODE_ENV === 'development',
  isProduction: import.meta.env.NODE_ENV === 'production',
};

export const getIngestorApiUrl = (endpoint = '') => {
  return `${config.ingestorApiBaseUrl}${endpoint}`;
};

export const getAdminFrontendUrl = (path = '') => {
  return `${config.adminFrontendProtocol}://${config.adminFrontendHost}:${config.adminFrontendPort}${path}`;
};