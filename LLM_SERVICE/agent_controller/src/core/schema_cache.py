import hashlib
import json
from functools import lru_cache
from typing import Any, Dict, Type

from pydantic import BaseModel

from .json_schema_to_pydantic import JsonPydanticSchemaCompiler
from .schema_registry import get_registry


class SchemaCache:
    def __init__(self) -> None:
        self._registry = get_registry()
        self._compiler = JsonPydanticSchemaCompiler()
    

    def create_fingerprint(
        self,
        schema: Dict[str, Any]
    ) -> str:
        normalized = json.dumps(
            schema, 
            sort_keys=True, 
            ensure_ascii=False, 
            separators=(",", ":")
        )

        return hashlib.sha256(normalized.encode()).hexdigest()
    

    @lru_cache(maxsize=256)
    def _compile_schema_cached(
        self,
        schema_json: str,
        model_name: str
    ) -> Type[BaseModel]:
        schema = json.loads(schema_json)
        return self._compiler.compile(
            schema,
            default_name=model_name
        )
    

    def get_compiled_model(
        self,
        schema: Dict[str, Any],
        model_name: str
    ) -> Type[BaseModel]:
        fingerprint = self.create_fingerprint(schema)
        
        cached_model = self._registry.get(fingerprint)
        if cached_model is not None:
            return cached_model
        
        schema_json = json.dumps(
            schema,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":")
        )

        model = self._compile_schema_cached(schema_json, model_name)
        
        self._registry.set(fingerprint, model)

        return model
    

    def create_schema_entry(
        self,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "fingerprint": self.create_fingerprint(schema),
            "schema": schema
        }


_cache_instance = SchemaCache()


def get_cache() -> SchemaCache:
    return _cache_instance


    