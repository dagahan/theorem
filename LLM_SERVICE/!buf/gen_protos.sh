#!/usr/bin/env bash
set -Eeuo pipefail


SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUF_DIR="${ROOT_DIR}/!buf"
PY_OUT="${GEN_PY_OUT:-${BUF_DIR}/gen}"
VALIDATE_OUT="${BUF_DIR}/validate_gen"


log()  { printf "[INFO] %s\n" "$*"; }
ok()   { printf "[ OK ] %s\n" "$*"; }
warn() { printf "[WARN] %s\n" "$*" >&2; }
fail() { printf "[FAIL] %s\n" "$*" >&2; exit 1; }

on_error() { ec=$?; printf "[FAIL] buf workflow failed (exit %d)\n" "$ec" >&2; exit "$ec"; }
trap on_error ERR


printf "\n=== Proto generation (buf) ===\n"
printf "ROOT: %s\nBUF:  %s\nOUT:  %s\n" "${ROOT_DIR}" "${BUF_DIR}" "${PY_OUT}"

command -v buf >/dev/null 2>&1 || fail "buf CLI not found"
log "buf $(buf --version)"

cnt=$(find "${BUF_DIR}/protos" -type f -name "*.proto" | wc -l | tr -d ' ')
log "protos: ${cnt}"


[[ -d "${PY_OUT}" ]] && { log "clean ${PY_OUT}"; rm -rf "${PY_OUT}"; }


pushd "${BUF_DIR}" >/dev/null
log "buf dep update"; buf dep update

start_ts=$(date +%s)
log "buf generate"; buf generate
end_ts=$(date +%s)
popd >/dev/null


dur=$(( end_ts - start_ts ))
py_cnt=$(find "${PY_OUT}" -type f -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
[[ "${py_cnt}" -gt 0 ]] || fail "no python files generated"
ok "generated ${py_cnt} file(s) in ${dur} seconds"


if [[ ! -f "${VALIDATE_OUT}/buf/validate/validate_pb2.py" ]]; then
  log "generating validate stubs"
  [[ -d "${VALIDATE_OUT}" ]] && { log "clean ${VALIDATE_OUT}"; rm -rf "${VALIDATE_OUT}"; }
  pushd "${BUF_DIR}" >/dev/null
  buf generate --template buf.validate.gen.yaml third_party/protovalidate/buf/validate
  popd >/dev/null
  validate_cnt=$(find "${VALIDATE_OUT}" -type f -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
  [[ "${validate_cnt}" -gt 0 ]] || fail "no validate python files generated"
  ok "generated ${validate_cnt} validate file(s)"
else
  log "validate stubs already exist, skipping generation"
fi


echo
printf "=== Distribute stubs ===\n"


ensure_init() {
  local d="$1"
  [[ -d "$d" ]] || mkdir -p "$d"
  [[ -f "$d/__init__.py" ]] || : > "$d/__init__.py"
}


patch_relative_imports() {
  local pkg_dir="$1"   # .../protobuf_stubs
  python3 - <<'PY' "$pkg_dir"
import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
for p in root.glob("*_pb2_grpc.py"):
    s = p.read_text(encoding="utf-8")
    # если уже относительный, пропускаем
    if re.search(r'^\s*from\s+\.\s+import\s+\w+_pb2\s+as\s+.+$', s, flags=re.M):
        continue
    ns = re.sub(r'^\s*import\s+(\w+_pb2)\s+as\s+(.+)$',
                r'from . import \1 as \2', s, flags=re.M)
    if ns != s:
        p.write_text(ns, encoding="utf-8")
        print(f"patched {p}")
PY
}


write_pkg_init() {
  local pkg_dir="$1"
  local pb2_files pb2_grpc_files
  pb2_files=$(find "${pkg_dir}" -maxdepth 1 -name "*_pb2.py" | sort || true)
  pb2_grpc_files=$(find "${pkg_dir}" -maxdepth 1 -name "*_pb2_grpc.py" | sort || true)

  {
    printf '"""Auto-generated protobuf stubs for easy import.\nGenerated on %s\n"""\n\n' "$(date)"
    echo "# Import all protobuf modules (package-relative)"
    for f in $pb2_files; do
      rel="${f#${pkg_dir}/}"; rel="${rel%.py}"; rel="${rel//\//.}"
      echo "from .${rel} import *"
    done
    for f in $pb2_grpc_files; do
      rel="${f#${pkg_dir}/}"; rel="${rel%.py}"; rel="${rel//\//.}"
      echo "from .${rel} import *"
    done

    echo
    echo "# Expose absolute names expected by grpc stubs (e.g. 'embedder_pb2')"
    echo "import sys as _sys"
    echo "from importlib import import_module as _im"
    for f in $pb2_files; do
      base="$(basename "$f")"
      mod="${base%.py}"   # e.g. embedder_pb2
      echo "_sys.modules.setdefault('${mod}', _im('.${mod}', package=__name__))"
    done

    echo
    echo "__all__ = [name for name in dir() if not name.startswith('_')]"
  } > "${pkg_dir}/__init__.py"
}


updated=0
shopt -s nullglob


for service_dir in "${ROOT_DIR}"/*/protobuf_stubs; do
  service_root="$(dirname "$service_dir")"
  validate_src="${VALIDATE_OUT}/buf/validate"
  validate_dst="${service_root}/buf/validate" 

  mkdir -p "${service_dir}"
  rm -rf "${service_dir:?}/"* 2>/dev/null || true
  cp -r "${PY_OUT}/"* "${service_dir}/" 2>/dev/null || true

  rm -rf "${service_dir}/buf" 2>/dev/null || true

  if [[ -d "${validate_src}" ]]; then
    rm -rf "${validate_dst:?}/"* 2>/dev/null || true
    mkdir -p "${validate_dst}"
    cp -r "${validate_src}/"* "${validate_dst}/"
    ensure_init "${service_root}/buf"
    ensure_init "${validate_dst}"
  fi

  ensure_init "${service_dir}"

  patch_relative_imports "${service_dir}"

  write_pkg_init "${service_dir}"

  copied=$(find "${service_dir}" -type f -name "*.py" | wc -l | tr -d ' ')
  printf "• %-16s -> %4s stub file(s) | validate: %s\n" \
    "$(basename "$service_root")" "${copied}" \
    "$( [[ -f "${validate_dst}/validate_pb2.py" ]] && echo yes || echo no )"

  updated=$((updated + 1))
done


shopt -u nullglob
ok "updated ${updated} service(s)"


