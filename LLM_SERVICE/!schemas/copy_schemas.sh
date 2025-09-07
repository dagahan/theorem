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


for service_dir in "${ROOT_DIR}"/*/pydantic_schemas; do
  if [[ -d "$(dirname "$service_dir")" ]]; then
    service_name=$(basename "$(dirname "$service_dir")")
    log "Copying to ${service_name}..."
    
    mkdir -p "${service_dir}"
    
    # Clean destination directory before copying
    log "  Cleaning ${service_dir}/"
    rm -rf "${service_dir:?}/"* 2>/dev/null || true
    
    log "  Copying from ${SCHEMAS_DIR}/ to ${service_dir}/"
    find "${SCHEMAS_DIR}" -name "*.py" -not -name "__init__.py" -exec cp {} "${service_dir}/" \;
    
    log "  Creating dynamic __init__.py for ${service_name} schemas..."
    
    schema_files=$(find "${service_dir}" -name "*.py" -not -name "__init__.py" | sort)
    
    cat > "${service_dir}/__init__.py" << EOF
"""
Auto-generated Pydantic schemas for easy import.
All schemas are imported dynamically from individual files.
Generated on $(date)
"""

# Import all schema modules
EOF
    
    for file in $schema_files; do
        basename_file=$(basename "$file" .py)
        echo "from .${basename_file} import *" >> "${service_dir}/__init__.py"
    done
    

    cat >> "${service_dir}/__init__.py" << EOF


# Auto-generated __all__ list
__all__ = []
EOF
    
    for file in $schema_files; do
        basename_file=$(basename "$file" .py)
        log "    Analyzing ${basename_file}..."
        
        classes=$(grep -E "^class [A-Za-z][A-Za-z0-9]*.*BaseModel" "$file" | sed 's/class \([A-Za-z][A-Za-z0-9]*\).*/\1/' | tr '\n' ' ')
        
        if [[ -n "$classes" ]]; then
            echo "# Classes from ${basename_file}" >> "${service_dir}/__init__.py"
            for class_name in $classes; do
                echo "__all__.append('${class_name}')" >> "${service_dir}/__init__.py"
            done
        fi
    done
    
    log "  Copying schemas __init__.py to $(dirname "$service_dir")/schemas.py"
    cp "${SCHEMAS_DIR}/__init__.py" "$(dirname "$service_dir")/schemas.py"
    
    ((copied_count++))
  fi
done


if [[ $copied_count -eq 0 ]]; then
  warn "No services with pydantic/ directories found"
else
  ok "Schemas copied to ${copied_count} service(s)"
fi


ok "Done."


