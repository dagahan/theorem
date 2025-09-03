#!/bin/bash

set -e

echo "Starting VLLM service..."

if ! command -v python &> /dev/null; then
    echo "Error: python command not found"
    exit 1
fi

mkdir -p /root/.cache

echo "Downloading small test model..."
python -c "
import os
from huggingface_hub import snapshot_download

# Download a small test model (TinyLlama-1.1B)
model_path = '/root/.cache/tinyllama'
if not os.path.exists(model_path):
    print('Downloading TinyLlama-1.1B model...')
    snapshot_download(
        repo_id='TinyLlama/TinyLlama-1.1B-Chat-v1.0',
        local_dir=model_path,
        local_dir_use_symlinks=False
    )
    print('Model downloaded successfully!')
else:
    print('Model already exists, skipping download.')
"

echo "Starting VLLM server on port ${VLLM_PORT:-8000}..."
exec python -m vllm.entrypoints.openai.api_server \
    --model /root/.cache/tinyllama \
    --host 0.0.0.0 \
    --port ${VLLM_PORT:-8000} \
    --served-model-name tinyllama

