from typing import Any, Dict, Type

from pydantic import BaseModel

from .schema_cache import get_cache


class SchemaUtils:
    def __init__(self) -> None:
        self._cache = get_cache()
    

    def get_personality_model(
        self,
        personality: Dict[str, Any],
        model_name: str
    ) -> Type[BaseModel] | None:
        response_schema = personality.get("response_schema")
        if not response_schema:
            return None
        
        if not isinstance(response_schema, dict):
            return None
        
        schema_data = response_schema.get("schema")
        if not schema_data:
            return None
        
        return self._cache.get_compiled_model(schema_data, model_name)
    

    def get_personality_schema_data(
        self,
        personality: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        response_schema = personality.get("response_schema")
        if not response_schema or not isinstance(response_schema, dict):
            return None
        
        schema_data = response_schema.get("schema")
        if not isinstance(schema_data, dict):
            return None
        
        return schema_data
    

    def create_schema_entry(
        self,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self._cache.create_schema_entry(schema)


_utils_instance = SchemaUtils()


def get_utils() -> SchemaUtils:
    return _utils_instance


    