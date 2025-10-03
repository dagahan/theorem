#!/bin/bash

set -e

echo "Starting frontend service..."

# Set default ports if not provided
FRONTEND_NGINX_PORT=${FRONTEND_NGINX_PORT:-4173}
FRONTEND_NGINX_DEV_PORT=${FRONTEND_NGINX_DEV_PORT:-5173}

# Check if we're running in development mode
if [ "${NODE_ENV}" = "development" ]; then
    echo "Running in development mode..."
    npm run dev -- --host 0.0.0.0 --port ${FRONTEND_NGINX_DEV_PORT}
else
    echo "Running in production mode..."
    # Serve built files with a simple HTTP server
    npx serve -s dist -l ${FRONTEND_NGINX_PORT}
fi


