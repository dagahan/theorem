#!/usr/bin/env bash
set -euo pipefail


# Universal protobuf stub generation script for multiple languages
# Usage: ./gen.sh --py [--go] [--java] etc.
# Each language has its own generator in generators/<lang>/


SCRIPT_DIR="$(dirname "$0")"
GENERATORS_DIR="${SCRIPT_DIR}/generators"


log() { printf "[INFO] %s\n" "$*"; }
ok() { printf "[ OK ] %s\n" "$*"; }
fail() { printf "[FAIL] %s\n" "$*" >&2; exit 1; }


show_usage() {
    echo "Usage: $0 [--py] [--go] ..."
    echo ""
    echo "Generate protobuf stubs for specified languages:"
    echo "  --py     Generate Python stubs using uv"
    echo "  --go     Generate Go stubs (not implemented yet)"
    echo ""
    echo "Examples:"
    echo "  $0 --py                    # Generate only Python stubs"
    echo "  $0 --py --go              # Generate Python and Go stubs"
}


GENERATE_PYTHON=false
GENERATE_GO=false
GENERATE_JAVA=false


if [[ $# -eq 0 ]]; then
    show_usage
    exit 1
fi


while [[ $# -gt 0 ]]; do
    case $1 in
        --py)
            GENERATE_PYTHON=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            fail "Unknown option: $1"
            ;;
    esac
done


if [[ "$GENERATE_PYTHON" == "true" ]]; then
    log "Generating Python stubs..."
    
    if ! command -v uv &> /dev/null; then
        fail "uv is not installed. Please install uv first:" \
             "curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
    
    PYTHON_GENERATOR="${GENERATORS_DIR}/python/gen_protos.py"
    if [[ ! -f "$PYTHON_GENERATOR" ]]; then
        fail "Python generator not found: $PYTHON_GENERATOR"
    fi
    
    uv run "$PYTHON_GENERATOR"
    ok "Python stub generation completed"
fi


ok "All requested stub generations completed"



