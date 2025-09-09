#!/usr/bin/env bash
set -Eeuo pipefail

: "${PROTO_BUILD_DIR?must be set}"
: "${REPO_ROOT?must be set}"

log()  { printf "[INFO] %s\n" "$*"; }
ok()   { printf "[ OK ] %s\n" "$*"; }
fail() { printf "[FAIL] %s\n" "$*" >&2; exit 1; }

ensure_init() {
  local d="$1"
  [[ -d "$d" ]] || mkdir -p "$d"
  [[ -f "$d/__init__.py" ]] || : > "$d/__init__.py"
}


updated=0
shopt -s nullglob

for service_dir in "${REPO_ROOT}"/*/protobuf_stubs; do
  service_root="$(dirname "$service_dir")"

  rm -rf "${service_dir:?}/"* 2>/dev/null || true
  mkdir -p "${service_dir}"
  
  # Copy main protobuf files but exclude third_party to avoid duplication
  cp -r "${PROTO_BUILD_DIR}"/* "${service_dir}/" 2>/dev/null || true
  rm -rf "${service_dir}/third_party" 2>/dev/null || true

  validate_src="${PROTO_BUILD_DIR}/third_party/protovalidate/buf/validate"
  buf_validate_dst="${service_root}/buf/validate"
  
  if [[ -f "${validate_src}/validate_pb2.py" ]]; then
    # Create buf/validate structure for protovalidate package compatibility
    rm -rf "${buf_validate_dst:?}" 2>/dev/null || true
    mkdir -p "${buf_validate_dst}"
    cp -r "${validate_src}/validate_pb2.py" "${buf_validate_dst}/"
    ensure_init "${service_root}/buf"
    ensure_init "${buf_validate_dst}"
    
  else
    fail "validate_pb2.py not found at path: ${validate_src}"
  fi

  ensure_init "${service_dir}"
  python3 - "$service_dir" <<'PY'
import sys, pathlib
pkg = pathlib.Path(sys.argv[1])
init = pkg / "__init__.py"
pb2 = sorted([p for p in pkg.glob("*_pb2.py")])
grpc = sorted([p for p in pkg.glob("*_pb2_grpc.py")])
with init.open("w", encoding="utf-8") as f:
    from datetime import datetime
    f.write(f'"""Auto-generated protobuf stubs. {datetime.now()}"""\n\n')
    for p in pb2 + grpc:
        mod = p.stem
        f.write(f"from .{mod} import *\n")
    f.write("\n__all__ = [n for n in dir() if not n.startswith('_')]\n")
print(f"[ OK ] wrote {init}")
PY

  copied=$(find "${service_dir}" -type f -name "*.py" | wc -l | tr -d ' ')
  printf "• %-16s -> %4s file(s) | validate: yes\n" "$(basename "$service_root")" "${copied}"
  updated=$((updated + 1))
done

shopt -u nullglob
ok "updated ${updated} service(s)"