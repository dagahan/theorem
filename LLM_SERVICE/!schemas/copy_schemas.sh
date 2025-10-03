#!/usr/bin/env bash


# This script copies centralized Pydantic schemas from schemas/models/ to all 
# microservices that have a pydantic/ directory.
# 
# The script automatically finds all services with pydantic/ directories
# and copies the schema files there for easy import in service code.


set -Euo pipefail


SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCHEMAS_DIR="${ROOT_DIR}/!schemas"


log()   { echo -e "🔹 $*"; }
ok()    { echo -e "✅ $*"; }
warn()  { echo -e "⚠️  $*" >&2; }
fail()  { echo -e "❌ $*" >&2; exit 1; }


echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Schema distribution"
echo "📁 ROOT:     ${ROOT_DIR}"
echo "📁 SCHEMAS:  ${SCHEMAS_DIR}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


if [[ ! -d "${SCHEMAS_DIR}" ]]; then
  fail "Schemas directory not found: ${SCHEMAS_DIR}"
fi


log "Scanning schema files:"
find "${SCHEMAS_DIR}" -type f -name "*.py" -not -name "__init__.py" -print | sed 's/^/   • /'


log "Copying schemas to services..."
copied_count=0


mapfile -t SERVICE_SCHEMA_DIRS < <(find "${ROOT_DIR}" -maxdepth 3 -type d -name "pydantic_schemas" | sort)

for service_dir in "${SERVICE_SCHEMA_DIRS[@]}"; do
  if [[ -d "$(dirname "$service_dir")" ]]; then
    parent_dir="$(dirname "$service_dir")"
    service_name=$(basename "$parent_dir")
    log "Copying to ${service_name}..."
    
    mkdir -p "${service_dir}"
    
    # Clean destination directory before copying
    log "  Cleaning ${service_dir}/"
    rm -rf "${service_dir:?}/"* 2>/dev/null || true
    
    # Copy base_model.py to root of pydantic_schemas
    log "  Copying base_model.py to ${service_dir}/"
    cp "${SCHEMAS_DIR}/base_model.py" "${service_dir}/"
    
    # Copy category directories
    log "  Copying category directories from ${SCHEMAS_DIR}/ to ${service_dir}/"
    for category_dir in "${SCHEMAS_DIR}"/*/; do
      if [[ -d "$category_dir" ]]; then
        category_name=$(basename "$category_dir")
        log "    Copying category: ${category_name}"
        cp -r "$category_dir" "${service_dir}/"
      fi
    done
    
    log "  Creating dynamic __init__.py for ${service_name} schemas..."
    
    cat > "${service_dir}/__init__.py" << EOF
from .base_model import *
from .common import *
from .collection_management import *
from .document_management import *
from .service_stats import *
from .ingest import *
from .postgres import *

__all__ = [
    # Base Model
    "UUIDpk",
    "created_at", 
    "updated_at",
    "Base",
    # Common
    "HealthResponse",
    "ErrorResponse", 
    "SuccessResponse",
    # Collection Management
    "ReindexRequest",
    "ReindexResponse",
    "SwitchAliasRequest",
    "SwitchAliasResponse",
    "CollectionInfo",
    "ListCollectionsResponse",
    # Document Management
    "DeleteDocumentRequest",
    "DeleteDocumentItem",
    "DeleteDocumentResponse",
    "DocumentInfo",
    "GetDocumentResponse",
    # Service Stats
    "ServiceStats",
    # File Ingestion
    "IngestFilesItem",
    "IngestFilesResponse",
    # PostgreSQL Models
    "Document",
]
EOF
    
    # Remove schemas.py if it exists
    if [[ -f "${parent_dir}/schemas.py" ]]; then
      log "  Removing old schemas.py from ${parent_dir}/"
      rm "${parent_dir}/schemas.py"
    fi
    
    ((copied_count++))
  fi
done


if [[ $copied_count -eq 0 ]]; then
  warn "No services with pydantic/ directories found"
else
  ok "Schemas copied to ${copied_count} service(s)"
fi


ok "Done."

