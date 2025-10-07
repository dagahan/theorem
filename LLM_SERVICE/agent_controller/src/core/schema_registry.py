from typing import Dict, Type
from pydantic import BaseModel


class SchemaRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseModel]] = {}
    
    
    def get(self, fingerprint: str) -> Type[BaseModel] | None:
        return self._registry.get(fingerprint)
    

    def set(self, fingerprint: str, model: Type[BaseModel]) -> None:
        self._registry[fingerprint] = model
    

    def clear(self) -> None:
        self._registry.clear()
    

    def size(self) -> int:
        return len(self._registry)
    

    def has(self, fingerprint: str) -> bool:
        return fingerprint in self._registry


_registry_instance = SchemaRegistry()


def get_registry() -> SchemaRegistry:
    return _registry_instance



