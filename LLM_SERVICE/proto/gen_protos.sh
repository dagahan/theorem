#!/usr/bin/env bash
set -Eeuo pipefail


SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROTO_DIR="${ROOT_DIR}/proto"


log()   { echo -e "🔹 $*"; }
ok()    { echo -e "✅ $*"; }
warn()  { echo -e "⚠️  $*" >&2; }
fail()  { echo -e "❌ $*" >&2; exit 1; }


on_error() {
  local ec=$?
  echo -e "\n❌ buf generate failed (exit $ec). See logs above."
  exit $ec
}

trap on_error ERR


PY_OUT="${GEN_PY_OUT:-${PROTO_DIR/stubs}"


echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛠  Proto generation (buf) "
echo "📁 ROOT:   ${ROOT_DIR}"
echo "📁 PROTO:  ${PROTO_DIR}"
echo "📦 PY OUT: ${PY_OUT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


if command -v buf >/dev/null 2>&1; then
  log "buf: $(buf --version)"
else
  fail "buf CLI not found. Install and retry."
fi

if command -v protoc >/dev/null 2>&1; then
  log "protoc: $(protoc --version)"
else
  warn "protoc not found in PATH (ok if you rely on remote plugins)."
fi


command -v protoc-gen-grpc_python >/dev/null 2>&1 && log "grpc_python plugin: present" || true


log "Scanning .proto files:"
find "${PROTO_DIR}" -type f -name "*.proto" -print | sed 's/^/   • /'


pushd "${PROTO_DIR}" >/dev/null

START_TS=$(date +%s)

log "Running: buf lint"
buf lint

log "Running: buf generate"
buf generate

END_TS=$(date +%s)
DUR=$(( END_TS - START_TS ))


popd >/dev/null


PY_CNT=$(find "${PY_OUT}" -type f 2>/dev/null | wc -l | tr -d ' ')


ok "Generation finished in ${DUR}s"
echo "📊 Artifacts:"
echo "   • Python files:   ${PY_CNT}   (${PY_OUT})"
ok "Done."

