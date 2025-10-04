#!/bin/bash

set -e

echo "Starting admin frontend service..."

if [ -f "/home/usov/myprojects/theorem/LLM_SERVICE/.env" ]; then
    echo "Loading environment variables from global .env file..."
    export $(grep -v '^#' /home/usov/myprojects/theorem/LLM_SERVICE/.env | xargs)
else
    echo "Warning: Global .env file not found at /home/usov/myprojects/theorem/LLM_SERVICE/.env"
fi

ADMIN_FRONTEND_NGINX_PORT=${ADMIN_FRONTEND_NGINX_PORT:-4174}
ADMIN_FRONTEND_NGINX_DEV_PORT=${ADMIN_FRONTEND_NGINX_DEV_PORT:-5501}

# API URLs from .env
VITE_INGESTOR_API_BASE_URL=${VITE_INGESTOR_API_BASE_URL:-http://localhost:50053}
VITE_GATEWAY_API_BASE_URL=${VITE_GATEWAY_API_BASE_URL:-http://localhost:8080}
VITE_QDRANT_API_BASE_URL=${VITE_QDRANT_API_BASE_URL:-http://localhost:6333}
VITE_VLLM_MATH_API_BASE_URL=${VITE_VLLM_MATH_API_BASE_URL:-http://localhost:50054}
VITE_VLLM_TALKING_API_BASE_URL=${VITE_VLLM_TALKING_API_BASE_URL:-http://localhost:50054}

echo "Configuration:"
echo "  Admin Frontend Port: ${ADMIN_FRONTEND_NGINX_PORT}"
echo "  Ingestor API URL: ${VITE_INGESTOR_API_BASE_URL}"
echo "  Node Environment: ${NODE_ENV:-production}"

if [ "${NODE_ENV}" = "development" ]; then
    echo "Running in development mode..."
    npm run dev -- --host 0.0.0.0 --port ${ADMIN_FRONTEND_NGINX_DEV_PORT}
else
    echo "Running in production mode..."
    npx serve -s dist -l ${ADMIN_FRONTEND_NGINX_PORT}
fi