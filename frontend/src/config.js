// Frontend Configuration
// This file will be replaced during build with environment variables

export const config = {
  // API Configuration
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://100.87.209.118:8080',
  apiTimeout: import.meta.env.VITE_API_TIMEOUT || 100000,
  
  // Frontend Configuration
  frontendHost: import.meta.env.VITE_FRONTEND_HOST || '192.168.0.102',
  frontendPort: import.meta.env.VITE_FRONTEND_PORT || '4173',
  frontendProtocol: import.meta.env.VITE_FRONTEND_PROTOCOL || 'http',
  
  // Environment
  nodeEnv: import.meta.env.NODE_ENV || 'production',
  
  // Development flags
  isDevelopment: import.meta.env.NODE_ENV === 'development',
  isProduction: import.meta.env.NODE_ENV === 'production',
};

// Helper function to get full API URL
export const getApiUrl = (endpoint = '') => {
  return `${config.apiBaseUrl}${endpoint}`;
};

// Helper function to get full frontend URL
export const getFrontendUrl = (path = '') => {
  return `${config.frontendProtocol}://${config.frontendHost}:${config.frontendPort}${path}`;
};