#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Python stub generation from .proto files using uv and pyproject.toml:
- Uses uv to manage dependencies and virtual environment
- Compiles all .proto files to *_pb2.py and *_pb2_grpc.py
- Compiles validate.proto to third_party/.../validate_pb2.py
- Patches relative imports in *_pb2_grpc.py (from . import X_pb2)
- Calls shell script distribute_stubs.sh for distribution to microservices

Usage: bash !buf/gen.sh
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
import shutil
from pathlib import Path


# ---------- PATHS ----------
SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_GEN_DIR = SCRIPT_DIR
BUF_DIR = PYTHON_GEN_DIR.parent.parent
ROOT = BUF_DIR.parent

PROTOS_DIR = BUF_DIR / "contracts" / "llm_service"
BUILD_DIR = PYTHON_GEN_DIR / ".build"  # temporary folder with compilation results
VENV_DIR = PYTHON_GEN_DIR / ".venv"

DISTRIBUTOR = PYTHON_GEN_DIR / "distribute_stubs.sh"


# ---------- LOGGING UTILITIES ----------
def log(msg: str) -> None:
    """Log info message."""
    print(f"[INFO] {msg}")


def ok(msg: str) -> None:
    """Log success message."""
    print(f"[ OK ] {msg}")


def fail(msg: str, code: int = 1) -> None:
    """Log error message and exit."""
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(code)


# ---------- STEP 1: uv environment setup ----------
def ensure_uv_environment() -> Path:
    """Create uv environment if needed. Returns path to python from uv environment."""
    python_bin = VENV_DIR / "bin" / "python"
    
    if not python_bin.exists():
        log(f"Creating uv environment: {VENV_DIR}")
        # Use uv to create virtual environment
        subprocess.run([
            "uv", "venv", 
            "--python", "3.12",
            str(VENV_DIR)
        ], check=True)
    
    # Install dependencies using uv
    log("Installing dependencies with uv: grpcio-tools, protobuf, protovalidate")
    subprocess.run([
        "uv", "pip", "install", 
        "--python", str(python_bin),
        "-e", str(PYTHON_GEN_DIR)
    ], check=True)
    
    return python_bin


def reexec_inside_uv_env():
    """If script is not run from uv environment, restart it with uv python."""
    if os.environ.get("INSIDE_UV_ENV") == "1":
        return  # already inside
    
    py = ensure_uv_environment()
    env = os.environ.copy()
    env["INSIDE_UV_ENV"] = "1"
    cmd = [str(py), str(Path(__file__).resolve())]
    log("Restarting script inside uv environment...")
    subprocess.run(cmd, check=True, env=env)
    sys.exit(0)


# ---------- STEP 2: collect all .proto files ----------
def collect_proto_files() -> list[Path]:
    """Collect all .proto files from the protos directory."""
    if not PROTOS_DIR.exists():
        fail(f"Protos directory not found: {PROTOS_DIR}")
    
    files = sorted(PROTOS_DIR.rglob("*.proto"))
    if not files:
        fail(f"No .proto files found in {PROTOS_DIR}")
    
    log(f"Found {len(files)} .proto files")
    return files


# ---------- STEP 3: protoc generation via grpc_tools ----------
def protoc_include_dir() -> str:
    """Get path with built-in google/*.proto from grpc_tools."""
    try:
        from grpc_tools import protoc  # noqa: F401
        import pkgutil
        import importlib
        
        spec = importlib.util.find_spec("grpc_tools")
        if spec and spec.submodule_search_locations:
            base = Path(list(spec.submodule_search_locations)[0])
            include = base / "_proto"
            return str(include)
    except Exception as e:
        fail(f"Could not find include directory from grpc_tools: {e}")
    
    fail("grpc_tools not installed or package structure changed")


def run_protoc(proto_paths: list[str], out_dir: Path, protos: list[Path]) -> None:
    """Run protoc (via python module) to generate python and grpc stubs."""
    from grpc_tools import protoc

    out_dir.mkdir(parents=True, exist_ok=True)
    include_args = ["-I" + p for p in proto_paths]

    # Generate everything at once - simpler, imports will match
    args = (["protoc"] +
            include_args +
            [f"--python_out={out_dir}", f"--grpc_python_out={out_dir}"] +
            [str(p) for p in protos])

    log("Running protoc (grpc_tools.protoc)...")
    # pylint: disable=protected-access
    code = protoc.main(args)
    if code != 0:
        fail(f"protoc exited with code {code}")
    ok("Python stub generation completed")


# ---------- STEP 4: patch imports in generated files ----------
def patch_relative_imports(pkg_root: Path) -> int:
    """
    Change `import X_pb2 as ...` to `from . import X_pb2 as ...` in *_pb2_grpc.py,
    so they can be imported as a package (protobuf_stubs).
    """
    count = 0
    for p in pkg_root.glob("*_pb2_grpc.py"):
        content = p.read_text(encoding="utf-8")
        if re.search(r'^\s*from\s+\.\s+import\s+\w+_pb2\s+as\s+', content, flags=re.M):
            continue
        
        new_content = re.sub(
            r'^\s*import\s+(\w+_pb2)\s+as\s+',
            r'from . import \1 as ',
            content, 
            flags=re.M
        )
        
        if new_content != content:
            p.write_text(new_content, encoding="utf-8")
            count += 1
    
    return count


def patch_third_party_imports(pkg_root: Path) -> int:
    """
    Patch third_party imports in *_pb2.py files to use buf.validate import path.
    """
    count = 0
    for p in pkg_root.glob("*_pb2.py"):
        content = p.read_text(encoding="utf-8")
        
        # Replace third_party imports with buf.validate path
        # Pattern matches: from third_party.protovalidate.buf.validate import validate_pb2 as ...
        new_content = re.sub(
            r'from third_party\.protovalidate\.buf\.validate import validate_pb2 as .+',
            'from buf.validate import validate_pb2 as third__party_dot_protovalidate_dot_buf_dot_validate_dot_validate__pb2',
            content
        )
        
        if new_content != content:
            p.write_text(new_content, encoding="utf-8")
            count += 1
    
    return count


# ---------- STEP 5: cleanup/prepare build directory ----------
def clean_build():
    """Clean and prepare build directory."""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


# ---------- STEP 6: call distributor ----------
def distribute():
    """Call distributor script to distribute stubs to microservices."""
    if not DISTRIBUTOR.exists():
        fail(f"Distributor not found: {DISTRIBUTOR}")
    
    env = os.environ.copy()
    env["PROTO_BUILD_DIR"] = str(BUILD_DIR)
    env["REPO_ROOT"] = str(ROOT)
    
    log("Distributing stubs to microservices (shell)...")
    subprocess.run(["bash", str(DISTRIBUTOR)], check=True, env=env)
    ok("Distribution completed")


# ---------- MAIN ----------
def main():
    """Main function."""
    reexec_inside_uv_env()  # ensure running inside uv environment

    clean_build()

    # 1) collect .proto files
    protos = collect_proto_files()

    # 2) setup include paths
    google_inc = protoc_include_dir()
    proto_paths = [
        str(PROTOS_DIR),                    # our protos
        str(PROTOS_DIR / "third_party"),    # third_party/*
        google_inc,                         # google/protobuf/*
    ]

    # 3) generate everything: *_pb2.py and *_pb2_grpc.py (if services exist)
    run_protoc(proto_paths, BUILD_DIR, protos)

    # 4) patch relative imports in *_pb2_grpc.py
    patched = patch_relative_imports(BUILD_DIR)
    log(f"GRPC import patching: {patched} files modified")
    
    # 5) patch third_party imports in *_pb2.py
    third_party_patched = patch_third_party_imports(BUILD_DIR)
    log(f"Third-party import patching: {third_party_patched} files modified")

    # 6) verify that at least one *_pb2.py was generated for each *.proto
    generated_py = list(BUILD_DIR.glob("*_pb2.py"))
    if not generated_py:
        fail("No *_pb2.py files found - generation failed")

    # 7) distribute to services
    distribute()

    ok("Done.")


if __name__ == "__main__":
    main()


    