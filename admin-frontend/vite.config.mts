import { defineConfig, loadEnv } from "vite"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '/home/usov/myprojects/theorem/LLM_SERVICE', '')
  
  return {
    root: ".",
    server: { 
      port: parseInt(env.ADMIN_FRONTEND_NGINX_DEV_PORT) || 5501, 
      open: true,
      host: '0.0.0.0'
    },
    build: { 
      outDir: "dist", 
      emptyOutDir: true 
    },
    define: {
      // Ingestor API
      'import.meta.env.VITE_INGESTOR_API_BASE_URL': JSON.stringify(`http://${env.INGESTOR_HOST || 'localhost'}:${env.INGESTOR_HTTP_PORT || 50053}`),
      'import.meta.env.VITE_INGESTOR_API_TIMEOUT': JSON.stringify(env.VITE_INGESTOR_API_TIMEOUT || 30000),
      
      // Gateway API
      'import.meta.env.VITE_GATEWAY_API_BASE_URL': JSON.stringify(`http://${env.GATEWAY_HOST || 'localhost'}:${env.GATEWAY_PORT || 8080}`),
      
      // Qdrant API
      'import.meta.env.VITE_QDRANT_API_BASE_URL': JSON.stringify(`http://${env.QDRANT_HOST || 'localhost'}:${env.QDRANT_HTTP_PORT || 6333}`),
      
      // VLLM Services
      'import.meta.env.VITE_VLLM_MATH_API_BASE_URL': JSON.stringify(`http://${env.VLLM_MATH_HOST || 'localhost'}:${env.VLLM_MATH_PORT || 50054}`),
      'import.meta.env.VITE_VLLM_TALKING_API_BASE_URL': JSON.stringify(`http://${env.VLLM_TALKING_HOST || 'localhost'}:${env.VLLM_TALKING_HTTP_PORT || 50054}`),
      
      // Admin Frontend Configuration  
      'import.meta.env.VITE_ADMIN_FRONTEND_HOST': JSON.stringify(env.VITE_ADMIN_FRONTEND_HOST || '192.168.0.102'),
      'import.meta.env.VITE_ADMIN_FRONTEND_PORT': JSON.stringify(env.VITE_ADMIN_FRONTEND_PORT || '4174'),
      'import.meta.env.VITE_ADMIN_FRONTEND_PROTOCOL': JSON.stringify(env.VITE_ADMIN_FRONTEND_PROTOCOL || 'http'),
      
      // Environment
      'import.meta.env.NODE_ENV': JSON.stringify(env.NODE_ENV || 'production'),
    }
  }
})