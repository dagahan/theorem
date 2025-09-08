#!/usr/bin/env python3
"""
Альтернативный скрипт для генерации proto стабов с использованием Python.
Используется когда buf.build недоступен.
"""

import os
import sys
import subprocess
import shutil
import tempfile
import pathlib
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


def find_protoc() -> Optional[str]:
    """Найти исполняемый файл protoc"""
    # Проверяем стандартные пути
    for path in ["/usr/local/bin/protoc", "/usr/bin/protoc", "protoc"]:
        if shutil.which(path):
            return path
    return None


def install_protobuf_locally() -> bool:
    """Попытаться установить protobuf локально через pip"""
    try:
        log("Attempting to install protobuf locally...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--user", 
            "protobuf", "grpcio-tools"
        ], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        warn(f"Failed to install protobuf: {e}")
        return False


def generate_proto_files(protoc_path: str, proto_dir: str, output_dir: str) -> List[str]:
    """Генерировать Python файлы из proto файлов"""
    generated_files = []
    
    # Найти все proto файлы
    proto_files = []
    for root, dirs, files in os.walk(proto_dir):
        for file in files:
            if file.endswith('.proto'):
                proto_files.append(os.path.join(root, file))
    
    log(f"Found {len(proto_files)} proto files")
    
    # Создать выходную директорию
    os.makedirs(output_dir, exist_ok=True)
    
    # Генерировать Python файлы для каждого proto файла
    for proto_file in proto_files:
        try:
            # Определить относительный путь для импорта
            rel_path = os.path.relpath(proto_file, proto_dir)
            proto_name = os.path.splitext(os.path.basename(proto_file))[0]
            
            log(f"Generating Python files for {proto_name}")
            
            # Команда protoc для генерации Python файлов
            cmd = [
                protoc_path,
                f"--proto_path={proto_dir}",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                proto_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Найти сгенерированные файлы
                for suffix in ['_pb2.py', '_pb2_grpc.py']:
                    generated_file = os.path.join(output_dir, proto_name + suffix)
                    if os.path.exists(generated_file):
                        generated_files.append(generated_file)
                        log(f"Generated: {generated_file}")
            else:
                warn(f"Failed to generate {proto_name}: {result.stderr}")
                
        except Exception as e:
            warn(f"Error processing {proto_file}: {e}")
    
    return generated_files


def create_init_files(output_dir: str) -> None:
    """Создать __init__.py файлы для правильной работы пакетов"""
    for root, dirs, files in os.walk(output_dir):
        if '__init__.py' not in files:
            init_file = os.path.join(root, '__init__.py')
            with open(init_file, 'w') as f:
                f.write('"""Auto-generated protobuf package"""\n')
        # Создать __init__.py для всех поддиректорий
        for dir_name in dirs:
            subdir = os.path.join(root, dir_name)
            init_file = os.path.join(subdir, '__init__.py')
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write('"""Auto-generated protobuf package"""\n')


def patch_imports(output_dir: str) -> None:
    """Исправить импорты в сгенерированных файлах для относительных путей"""
    import re
    
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith('_pb2_grpc.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Заменить абсолютные импорты на относительные
                    # from module_pb2 import ... -> from . import module_pb2 as ...
                    pattern = r'^(\s*)import\s+(\w+_pb2)\s+as\s+(\w+)$'
                    replacement = r'\1from . import \2 as \3'
                    
                    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        log(f"Patched imports in {file_path}")
                        
                except Exception as e:
                    warn(f"Failed to patch {file_path}: {e}")


def distribute_stubs(output_dir: str, root_dir: str) -> None:
    """Распределить стабы по сервисам (как в оригинальном скрипте)"""
    log("Distributing stubs to services...")
    
    # Найти все директории protobuf_stubs
    for service_dir in pathlib.Path(root_dir).glob("*/protobuf_stubs"):
        service_root = service_dir.parent
        
        log(f"Updating {service_root.name}")
        
        # Очистить старую директорию
        if service_dir.exists():
            shutil.rmtree(service_dir)
        
        # Скопировать новые стабы
        shutil.copytree(output_dir, service_dir)
        
        # Подсчитать файлы
        py_files = list(service_dir.glob("**/*.py"))
        log(f"Copied {len(py_files)} Python files to {service_root.name}")


def main():
    """Основная функция"""
    print("\n=== Proto generation (Python) ===")
    
    # Определить пути
    script_dir = pathlib.Path(__file__).parent
    root_dir = script_dir.parent
    buf_dir = script_dir
    proto_dir = buf_dir / "protos"
    output_dir = buf_dir / "gen"
    
    print(f"ROOT: {root_dir}")
    print(f"BUF:  {buf_dir}")
    print(f"OUT:  {output_dir}")
    
    # Проверить наличие proto файлов
    if not proto_dir.exists():
        fail(f"Proto directory not found: {proto_dir}")
    
    proto_files = list(proto_dir.glob("**/*.proto"))
    log(f"protos: {len(proto_files)}")
    
    # Найти protoc
    protoc_path = find_protoc()
    if not protoc_path:
        warn("protoc not found in system")
        if not install_protobuf_locally():
            fail("Cannot find protoc and failed to install protobuf locally")
        # Попробовать найти protoc снова после установки
        protoc_path = find_protoc()
        if not protoc_path:
            fail("Still cannot find protoc after installation attempt")
    
    log(f"Using protoc: {protoc_path}")
    
    # Очистить выходную директорию
    if output_dir.exists():
        log(f"Cleaning {output_dir}")
        shutil.rmtree(output_dir)
    
    # Генерировать файлы
    import time
    start_time = time.time()
    
    generated_files = generate_proto_files(str(protoc_path), str(proto_dir), str(output_dir))
    
    end_time = time.time()
    duration = int(end_time - start_time)
    
    if not generated_files:
        fail("No Python files generated")
    
    ok(f"Generated {len(generated_files)} file(s) in {duration} seconds")
    
    # Создать __init__.py файлы
    create_init_files(str(output_dir))
    
    # Исправить импорты
    patch_imports(str(output_dir))
    
    # Распределить стабы по сервисам
    distribute_stubs(str(output_dir), str(root_dir))
    
    ok("Proto generation completed successfully")


if __name__ == "__main__":
    main()