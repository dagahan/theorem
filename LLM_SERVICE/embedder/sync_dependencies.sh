#!/usr/bin/env bash
set -Eeuo pipefail

echo "🔄 Syncing dependencies..."
uv sync
echo "✅ Dependencies synced successfully"