#!/usr/bin/env bash
set -euo pipefail

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "[FAIL] uv is not installed. Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Run the Python script using uv
uv run "$(dirname "$0")/scripts/gen_protos.py"