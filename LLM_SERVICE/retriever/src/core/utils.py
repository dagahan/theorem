import json
import os
import os.path
import shutil
from collections.abc import Iterable
from datetime import datetime
from inspect import getframeinfo, stack
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import bcrypt
import chardet
import colorama  # type: ignore

from dotenv import find_dotenv, load_dotenv
from loguru import logger
from pydantic import ValidationError


class MethodTools:
    @staticmethod
    def get_method_info(
        stack_level: int = 1
    ) -> tuple[str, str, int]:
        try:
            current_stack = stack()
            if not len(current_stack) > stack_level:
                return ("Unknown File", "Unknown Method", 0)
            
            frame = current_stack[stack_level][0]
            frame_info = getframeinfo(frame)
            return (
                frame_info.filename,
                frame_info.function,
                frame_info.lineno
            )
        
        except Exception as ex:
            logger.error(f"There is an error with checking your method's name: {ex}")
            return ("Unknown File", "Unknown Method", 0)


class FileSystemTools:
    @staticmethod
    def ensure_directory_exists(directory: str) -> None:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)


    @staticmethod
    def count_files_in_dir(dir: str) -> int:
        return len([name for name in os.listdir(dir) if os.path.isfile(os.path.join(dir, name))])
    

    @staticmethod
    def save_file(
        file_path: str,
        data: bytes
    ) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)
    

    @staticmethod
    def delete_directory(dir: str) -> None:
        shutil.rmtree(dir)


    @staticmethod
    def delete_file(file_path: str) -> None:
        os.remove(file_path)


class EnvTools:
    @staticmethod
    def _find_project_root(
        markers: Iterable[str] = (".env", "docker-compose.yml")
    ) -> Path:
        path = Path.cwd().resolve()
        seen = set()
        while True:
            if any((path / marker).exists() for marker in markers):
                return path

            if path in seen or path.parent == path:
                return Path.cwd().resolve()

            seen.add(path)
            path = path.parent


    @staticmethod
    def _load_variables_from_env_file(
        path: Path,
        override: bool = False
    ) -> None:
        if path.exists():
            load_dotenv(
                dotenv_path=path,
                override=override,
                interpolate=True,
                encoding="utf-8",
            )


    @staticmethod
    def bootstrap_env(
        service_name: str | None = None,
        conf_filename: str = ".conf"
    ) -> None:
        if EnvTools.load_env_var("RUNNING_INSIDE_DOCKER") == "1":
            return

        logger.warning(f"service is running localy, loaded env/conf files manualy..")

        project_root = EnvTools._find_project_root()
        
        # Load global .env file first (highest priority)
        env_path = project_root / ".env"
        if env_path.exists():
            EnvTools._load_variables_from_env_file(path=env_path, override=True)
            logger.info(f"Loaded global .env from {env_path}")

        # Load service-specific .conf file if exists (can override global settings)
        if service_name:
            conf_path = project_root / service_name / conf_filename
            if conf_path.exists():
                EnvTools._load_variables_from_env_file(path=conf_path, override=True)
                logger.info(f"Loaded service-specific .conf from {conf_path}")
            else:
                logger.info(f"No service-specific .conf found at {conf_path}, using global .env only")

        os.environ.setdefault("RUNNING_INSIDE_DOCKER", "0")


    @staticmethod
    def load_env_var(variable_name: str) -> str | None:
        try:
            dotenv_path = find_dotenv(usecwd=True)
            if dotenv_path:
                load_dotenv(dotenv_path=dotenv_path)
            else:
                load_dotenv()
            value = os.getenv(variable_name)
            if not value:
                logger.critical(f"Cannot load env var named '{variable_name}'. returning None.")

            return value
        except Exception as ex:
            logger.critical(f"Error with loading env variable '{variable_name}'. returning None.\n{ex}")
            return None


    @staticmethod
    def required_load_env_var(variable_name: str) -> str:
        value: str | None = EnvTools.load_env_var(variable_name)
        if not value:
            raise RuntimeError(f"Missing required environment variable: {variable_name}")
        return value
        
    
    @staticmethod
    def set_env_var(
        variable_name: str,
        variable_value: str
    ) -> None:
        os.environ[variable_name] = variable_value


    @staticmethod
    def is_running_inside_docker_compose() -> bool:
        try:
            return EnvTools.required_load_env_var("RUNNING_INSIDE_DOCKER") == "1"
        except KeyError as ex:
            logger.critical(
                f"Error with checking if programm running inside docker. Returns default False\n{ex}"
            )
        return False
    

    @staticmethod
    def get_service_host(service_name: str) -> str:
        if EnvTools.is_running_inside_docker_compose():
            project: str = EnvTools.required_load_env_var("COMPOSE_PROJECT_NAME")
            return f"{service_name}-{project}"
        return EnvTools.required_load_env_var(f"{service_name.upper()}_HOST")


    @staticmethod
    def get_service_http_port(service_name: str) -> str:
        return EnvTools.required_load_env_var(f"{service_name.upper()}_HTTP_PORT")


    @staticmethod
    def get_service_grpc_port(service_name: str) -> str:
        return EnvTools.required_load_env_var(f"{service_name.upper()}_GRPC_PORT")


    @staticmethod
    def is_file_exist(directory: str, file: str) -> bool:
        return os.path.exists(os.path.join(os.getcwd(), directory, file))


    @staticmethod
    def create_file_in_directory(dir: str, file: str) -> None:
        try:
            os.makedirs(dir)
            with open(dir + file, "w") as newfile:
                newfile.write("")
        except Exception as ex:
            logger.error(
                f"Error with creating {dir}{file}\n{ex}"
            )


class JsonLoader:
    @staticmethod
    def read_json(path: str) -> dict[str, Any]:
        try:
            with open(os.path.abspath(path), "rb") as file:
                raw_data = file.read()
                detected_encoding = chardet.detect(raw_data)["encoding"]

            with open(os.path.abspath(path), encoding=detected_encoding) as file:
                data = json.load(file)
                if isinstance(data, dict):
                    info: dict[str, Any] = data
                else:
                    logger.error("JSON root is not an object: %s", type(data).__name__)
                    info = {}
        except FileNotFoundError as ex:
            logger.error(f"Error during reading JSON file {path}: {ex}")
            info = {}
        except (UnicodeDecodeError, json.JSONDecodeError) as ex:
            logger.error(f"Error during reading JSON file {path}: {ex}")
            info = {}
        return info


    @staticmethod
    def write_json(path: str, data: str) -> None:
        try:
            with open(os.path.abspath(path), "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error writing JSON file {path}: {e}")


class Filters:
    @staticmethod
    def filter_strings(list1: list[str], list2: list[str]) -> list[str]:
        set2 = set(list2)
        return [s for s in list1 if s not in set2]


    @staticmethod
    def personalized_line(line: str, artifact: str, name: str) -> str:
        return line.replace(artifact, name)


class StringTools:
    @staticmethod
    def hash_string(string: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(string.encode('utf-8'), salt).decode('utf-8')


class TimeTools:
    @staticmethod
    def now_time_zone() -> datetime:
        tz_name = EnvTools.load_env_var("TZ") or "UTC"
        try:
            tz = ZoneInfo(tz_name)

        except Exception:
            tz = ZoneInfo("UTC")

        return datetime.now(tz)


    @staticmethod
    def now_time_stamp() -> int:
        return int(TimeTools.now_time_zone().timestamp())


class ValidatingTools:
    @staticmethod
    def validate_models_by_schema(models: Any, schema: Any) -> Any:
        if not isinstance(models, Iterable):
            models = [models]

        valid_models = []
        for model in models:
            try:
                dto = schema.model_validate(model, from_attributes=True)
                valid_models.append(dto)
                
            except ValidationError as ex:
                model_id = getattr(model, "id", None)
                logger.warning(f"{colorama.Fore.YELLOW}Skipping invalid instance of {schema.__name__} (id={model_id}): {ex.errors()}")

        if len(valid_models) == 1:
            return valid_models[0]
        return valid_models

