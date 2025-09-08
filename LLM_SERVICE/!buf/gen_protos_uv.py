#!/usr/bin/env python3
"""
Скрипт для генерации proto стабов с использованием uv и grpc_tools.
Полная замена оригинального gen_protos.sh скрипта.
"""

import os
import sys
import subprocess
import shutil
import pathlib
import re
import time
from typing import List, Optional


def log(msg: str) -> None:
    """Логирование с префиксом [INFO]"""
    print(f"[INFO] {msg}")


def ok(msg: str) -> None:
    """Успешное сообщение с префиксом [ OK ]"""
    print(f"[ OK ] {msg}")


def warn(msg: str) -> None:
    """Предупреждение с префиксом [WARN]"""
    print(f"[WARN] {msg}", file=sys.stderr)


def fail(msg: str) -> None:
    """Ошибка с префиксом [FAIL]"""
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def run_command(cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Выполнить команду и вернуть результат"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return result
    except subprocess.CalledProcessError as e:
        fail(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}")
    except FileNotFoundError:
        fail(f"Command not found: {cmd[0]}")


def check_uv_available() -> bool:
    """Проверить доступность uv"""
    try:
        run_command(["uv", "--version"])
        return True
    except:
        return False


def install_grpc_tools(project_dir: pathlib.Path) -> None:
    """Установить grpcio-tools через uv"""
    log("Installing grpcio-tools via uv")
    run_command(["uv", "add", "grpcio-tools"], cwd=str(project_dir))


def generate_proto_files_with_grpc_tools(proto_dir: pathlib.Path, output_dir: pathlib.Path) -> List[pathlib.Path]:
    """Генерировать Python файлы из proto файлов используя grpc_tools"""
    generated_files = []
    
    # Найти все proto файлы
    proto_files = list(proto_dir.glob("**/*.proto"))
    log(f"Found {len(proto_files)} proto files")
    
    # Создать выходную директорию
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Генерировать Python файлы для каждого proto файла
    for proto_file in proto_files:
        try:
            proto_name = proto_file.stem
            
            log(f"Generating Python files for {proto_name}")
            
            # Команда grpc_tools.protoc для генерации Python файлов
            cmd = [
                sys.executable, "-m", "grpc_tools.protoc",
                f"--proto_path={proto_dir}",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                str(proto_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Найти сгенерированные файлы
                for suffix in ['_pb2.py', '_pb2_grpc.py']:
                    generated_file = output_dir / (proto_name + suffix)
                    if generated_file.exists():
                        generated_files.append(generated_file)
                        log(f"Generated: {generated_file.name}")
            else:
                warn(f"Failed to generate {proto_name}: {result.stderr}")
                
        except Exception as e:
            warn(f"Error processing {proto_file}: {e}")
    
    return generated_files


def generate_validate_stubs(proto_dir: pathlib.Path, output_dir: pathlib.Path) -> None:
    """Генерировать validate стабы отдельно"""
    validate_proto = proto_dir / "third_party" / "protovalidate" / "buf" / "validate" / "validate.proto"
    
    if not validate_proto.exists():
        warn("validate.proto not found, skipping validate stubs generation")
        return
    
    log("Generating validate stubs")
    
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--python_out={output_dir}",
        str(validate_proto)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        validate_file = output_dir / "buf" / "validate" / "validate_pb2.py"
        if validate_file.exists():
            log(f"Generated validate stubs: {validate_file}")
        else:
            warn("Validate stubs generation completed but file not found")
    else:
        warn(f"Failed to generate validate stubs: {result.stderr}")


def ensure_init_file(directory: pathlib.Path) -> None:
    """Создать __init__.py файл если его нет"""
    init_file = directory / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Auto-generated protobuf package"""\n')


def patch_relative_imports(pkg_dir: pathlib.Path) -> None:
    """Исправить импорты в сгенерированных файлах для относительных путей"""
    for grpc_file in pkg_dir.glob("*_pb2_grpc.py"):
        try:
            content = grpc_file.read_text(encoding="utf-8")
            
            # Если уже относительный, пропускаем
            if re.search(r'^\s*from\s+\.\s+import\s+\w+_pb2\s+as\s+.+$', content, flags=re.MULTILINE):
                continue
            
            # Заменить абсолютные импорты на относительные
            new_content = re.sub(
                r'^\s*import\s+(\w+_pb2)\s+as\s+(.+)$',
                r'from . import \1 as \2',
                content,
                flags=re.MULTILINE
            )
            
            if new_content != content:
                grpc_file.write_text(new_content, encoding="utf-8")
                log(f"Patched {grpc_file.name}")
                
        except Exception as e:
            warn(f"Failed to patch {grpc_file}: {e}")


def write_pkg_init(pkg_dir: pathlib.Path) -> None:
    """Создать __init__.py файл для пакета"""
    pb2_files = sorted(pkg_dir.glob("*_pb2.py"))
    pb2_grpc_files = sorted(pkg_dir.glob("*_pb2_grpc.py"))
    
    init_content = f'"""Auto-generated protobuf stubs for easy import.\nGenerated on {time.strftime("%Y-%m-%d %H:%M:%S")}\n"""\n\n'
    init_content += "# Import all protobuf modules (package-relative)\n"
    
    for f in pb2_files:
        rel = f.stem
        init_content += f"from .{rel} import *\n"
    
    for f in pb2_grpc_files:
        rel = f.stem
        init_content += f"from .{rel} import *\n"
    
    init_content += "\n# Expose absolute names expected by grpc stubs (e.g. 'embedder_pb2')\n"
    init_content += "import sys as _sys\n"
    init_content += "from importlib import import_module as _im\n"
    
    for f in pb2_files:
        mod = f.stem
        init_content += f"_sys.modules.setdefault('{mod}', _im('.{mod}', package=__name__))\n"
    
    init_content += "\n__all__ = [name for name in dir() if not name.startswith('_')]\n"
    
    init_file = pkg_dir / "__init__.py"
    init_file.write_text(init_content)


def distribute_stubs(output_dir: pathlib.Path, validate_out: pathlib.Path, root_dir: pathlib.Path) -> None:
    """Распределить стабы по сервисам (как в оригинальном скрипте)"""
    log("Distributing stubs to services...")
    
    updated_services = 0
    
    for service_dir in root_dir.glob("*/protobuf_stubs"):
        service_root = service_dir.parent
        service_name = service_root.name
        
        # Очистить старую директорию
        if service_dir.exists():
            shutil.rmtree(service_dir)
        
        # Скопировать основные стабы
        shutil.copytree(output_dir, service_dir)
        
        # Удалить директорию buf если она есть
        buf_dir_in_service = service_dir / "buf"
        if buf_dir_in_service.exists():
            shutil.rmtree(buf_dir_in_service)
        
        # Скопировать validate стабы
        validate_src = validate_out / "buf" / "validate"
        if validate_src.exists():
            validate_dst = service_root / "buf" / "validate"
            validate_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(validate_src, validate_dst)
            
            # Создать __init__.py файлы
            ensure_init_file(service_root / "buf")
            ensure_init_file(validate_dst)
        
        # Исправить импорты
        patch_relative_imports(service_dir)
        
        # Создать __init__.py для пакета
        write_pkg_init(service_dir)
        
        # Подсчитать файлы
        py_files = list(service_dir.glob("*.py"))
        validate_files = list((service_root / "buf" / "validate").glob("*.py")) if (service_root / "buf" / "validate").exists() else []
        
        log(f"• {service_name:<16} -> {len(py_files):>4} stub file(s) | validate: {'yes' if validate_files else 'no'}")
        
        updated_services += 1
    
    ok(f"Updated {updated_services} service(s)")


def main():
    """Основная функция - точная копия логики gen_protos.sh"""
    print("\n=== Proto generation (uv + grpc_tools) ===")
    
    # Определить пути (как в оригинальном скрипте)
    script_dir = pathlib.Path(__file__).parent
    root_dir = script_dir.parent
    buf_dir = script_dir
    proto_dir = buf_dir / "protos"
    py_out = buf_dir / "gen"
    validate_out = buf_dir / "validate_gen"
    
    print(f"ROOT: {root_dir}")
    print(f"BUF:  {buf_dir}")
    print(f"OUT:  {py_out}")
    
    # Проверить доступность uv
    if not check_uv_available():
        fail("uv CLI not found")
    
    # Подсчитать proto файлы
    proto_files = list(proto_dir.glob("**/*.proto"))
    log(f"protos: {len(proto_files)}")
    
    # Установить grpcio-tools если нужно
    try:
        import grpc_tools.protoc
        log("grpc_tools already available")
    except ImportError:
        # Использовать embedder проект для установки зависимостей
        embedder_dir = root_dir / "embedder"
        install_grpc_tools(embedder_dir)
    
    # Очистить выходную директорию
    if py_out.exists():
        log(f"clean {py_out}")
        shutil.rmtree(py_out)
    
    # Генерировать файлы
    start_ts = time.time()
    log("grpc_tools generate")
    
    generated_files = generate_proto_files_with_grpc_tools(proto_dir, py_out)
    
    end_ts = time.time()
    dur = int(end_ts - start_ts)
    
    py_cnt = len(generated_files)
    if py_cnt == 0:
        fail("no python files generated")
    
    ok(f"generated {py_cnt} file(s) in {dur} seconds")
    
    # Генерировать validate стабы отдельно
    validate_file = validate_out / "buf" / "validate" / "validate_pb2.py"
    if not validate_file.exists():
        log("generating validate stubs")
        if validate_out.exists():
            log(f"clean {validate_out}")
            shutil.rmtree(validate_out)
        
        generate_validate_stubs(proto_dir, validate_out)
        
        validate_cnt = len(list(validate_out.glob("**/*.py"))) if validate_out.exists() else 0
        if validate_cnt == 0:
            fail("no validate python files generated")
        ok(f"generated {validate_cnt} validate file(s)")
    else:
        log("validate stubs already exist, skipping generation")
    
    # Распределить стабы по сервисам
    print()
    print("=== Distribute stubs ===")
    distribute_stubs(py_out, validate_out, root_dir)
    
    print()
    ok("Proto generation completed successfully")


if __name__ == "__main__":
    main()