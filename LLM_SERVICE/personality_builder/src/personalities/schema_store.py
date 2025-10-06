from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003
from typing import Any, Dict, List, Literal, Tuple, Type, Union, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeVar
    T = TypeVar('T')

import yaml
from jsonschema.validators import Draft202012Validator
from pydantic import BaseModel, create_model
from loguru import logger

class ResponseSchemaStore:
    """
    Stores and provides (name -> JSON Schema), validates and
    compiles to Pydantic models (supported subset).
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._cache_schema: dict[Tuple[str, str|None], Dict[str, Any]] = {}
        self._cache_model: dict[Tuple[str, str|None], Type[BaseModel]] = {}
        self._file_mtime_cache: dict[Path, float] = {}

    def load_schema(self, persona: str, version: str|None = None) -> Dict[str, Any] | None:
        # Look for JSON or YAML
        p = self.base_dir / persona.lower() / "response.schema.json"
        if not p.exists():
            p = self.base_dir / persona.lower() / "response.schema.yaml"
        if not p.exists():
            logger.debug(f"No schema file found for persona: {persona}")
            return None

        key = (persona, version)
        
        # Check file modification for hot-reload
        current_mtime = p.stat().st_mtime
        if key in self._cache_schema and p in self._file_mtime_cache:
            if self._file_mtime_cache[p] >= current_mtime:
                return self._cache_schema[key]
        
        # File changed or not in cache - reload
        try:
            raw = p.read_text(encoding="utf-8")
            schema_data = json.loads(raw) if p.suffix == ".json" else yaml.safe_load(raw)
            schema: Dict[str, Any] = schema_data

            # Validate the schema itself
            Draft202012Validator.check_schema(schema)
            
            # Update caches
            self._cache_schema[key] = schema
            self._file_mtime_cache[p] = current_mtime
            
            logger.debug(f"Loaded schema for persona: {persona}")
            return schema
            
        except Exception as ex:
            logger.error(f"Failed to load schema for persona {persona}: {ex}")
            return None

    def compile_to_pydantic(self, persona: str, version: str|None = None) -> Type[BaseModel] | None:
        key = (persona, version)
        if key in self._cache_model:
            return self._cache_model[key]

        schema = self.load_schema(persona, version)
        if schema is None:
            return None

        model = self._jsonschema_to_pydantic_model(persona, schema)
        self._cache_model[key] = model
        return model

    # ====== Simple converter for JSON Schema subset -> Pydantic ======
    def _jsonschema_to_pydantic_model(self, name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
        # Support: object/properties/required, enum, array(items), primitives (string/number/integer/boolean)
        if schema.get("type") != "object":
            # Wrap everything as object with single "value" field
            model: Type[BaseModel] = create_model(
                f"{name}Model",
                value=(self._map_type(schema), ...)
            )
            return model

        fields = {}
        required = set(schema.get("required", []))
        props: Dict[str, Any] = schema.get("properties", {})

        for field_name, field_schema in props.items():
            py_type = self._map_type(field_schema)
            default = ... if field_name in required else None
            fields[field_name] = (py_type, default)

        return cast("Type[BaseModel]", create_model(f"{name}Model", **fields))

    def _map_type(self, s: Dict[str, Any]) -> Any:
        t = s.get("type")

        # enum
        if "enum" in s:
            values = tuple(s["enum"])
            return Literal[values]

        if t == "string":
            return str
        if t == "number":
            return float
        if t == "integer":
            return int
        if t == "boolean":
            return bool
        if t == "array":
            items = s.get("items", {"type": "string"})
            return List[Any]
        if t == "object":
            # рекурсивный объект
            return self._jsonschema_to_pydantic_model("Nested", s)

        # по умолчанию — строка
        return str


        