#!/bin/bash

set -e

echo "Starting frontend service..."

# Load environment variables from global .env file
if [ -f "/home/usov/myprojects/theorem/LLM_SERVICE/.env" ]; then
    echo "Loading environment variables from global .env file..."
    export $(grep -v '^#' /home/usov/myprojects/theorem/LLM_SERVICE/.env | xargs)
else
    echo "Warning: Global .env file not found at /home/usov/myprojects/theorem/LLM_SERVICE/.env"
fi

# Set default ports if not provided
FRONTEND_NGINX_PORT=${FRONTEND_NGINX_PORT:-4173}
FRONTEND_NGINX_DEV_PORT=${FRONTEND_NGINX_DEV_PORT:-5173}

# Set default API URL if not provided
VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://100.87.209.118:8080}

echo "Configuration:"
echo "  Frontend Port: ${FRONTEND_NGINX_PORT}"
echo "  API Base URL: ${VITE_API_BASE_URL}"
echo "  Node Environment: ${NODE_ENV:-production}"

# Check if we're running in development mode
if [ "${NODE_ENV}" = "development" ]; then
    echo "Running in development mode..."
    npm run dev -- --host 0.0.0.0 --port ${FRONTEND_NGINX_DEV_PORT}
else
    echo "Running in production mode..."
    # Serve built files with a simple HTTP server
    npx serve -s dist -l ${FRONTEND_NGINX_PORT}
fi


