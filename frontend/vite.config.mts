import { defineConfig, loadEnv } from "vite"

export default defineConfig(({ mode }) => {
  // Load environment variables from the global .env file
  const env = loadEnv(mode, '/home/usov/myprojects/theorem/LLM_SERVICE', '')
  
  return {
    root: ".",
    server: { 
      port: 4173, 
      open: true,
      host: '0.0.0.0'
    },
    build: { 
      outDir: "dist", 
      emptyOutDir: true 
    },
    define: {
      // Make environment variables available to the client
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL || 'http://100.87.209.118:8080'),
      'import.meta.env.VITE_API_TIMEOUT': JSON.stringify(env.VITE_API_TIMEOUT || '100000'),
      'import.meta.env.VITE_FRONTEND_HOST': JSON.stringify(env.VITE_FRONTEND_HOST || '192.168.0.102'),
      'import.meta.env.VITE_FRONTEND_PORT': JSON.stringify(env.VITE_FRONTEND_PORT || '4173'),
      'import.meta.env.VITE_FRONTEND_PROTOCOL': JSON.stringify(env.VITE_FRONTEND_PROTOCOL || 'http'),
      'import.meta.env.NODE_ENV': JSON.stringify(env.NODE_ENV || 'production'),
    }
  }
})


