from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, create_model
from pydantic import AnyUrl, EmailStr
from pydantic.config import ConfigDict


def _create_fingerprint(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        return str(id(value))


@dataclass(frozen=True)
class _ResolvedType:
    python_type: Any
    default_value: Any
    field_arguments: Dict[str, Any]


class JsonPydanticSchemaCompiler:
    """Compiles JSON Schema to Pydantic v2 classes."""

    _PRIMITIVE_TYPES: Dict[str, Any] = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }

    _FORMAT_TYPE_MAP: Dict[str, Any] = {
        "date-time": datetime,
        "date": date,
        "uuid": UUID,
        "email": EmailStr,
        "uri": AnyUrl,
        "url": AnyUrl,
    }

    def __init__(self, *, model_name_prefix: str = "Dynamic", allow_title_names: bool = True) -> None:
        self.model_name_prefix = model_name_prefix
        self.allow_title_names = allow_title_names
        self._name_usage_counts: Dict[str, int] = {}
        self._root_schema: Dict[str, Any] | None = None


    def compile(
        self,
        schema: Dict[str, Any],
        *,
        default_name: str = "DynamicResponse"
    ) -> Type[BaseModel]:
        """Returns Pydantic model class corresponding to the given JSON Schema."""

        self._root_schema = schema
        title = self._create_model_name(schema.get("title") or default_name)
        is_object_like = schema.get("type") == "object" or "properties" in schema or "additionalProperties" in schema
        node = schema if is_object_like else {
            "type": "object",
            "title": title,
            "properties": {"value": schema},
            "required": ["value"],
        }

        model = self._build_object_model(
            node,
            title, path=("root",)
        )
        
        return model


    def _create_model_name(
        self,
        raw_name: str
    ) -> str:
        base_name = raw_name if self.allow_title_names else self.model_name_prefix
        base_name = base_name or self.model_name_prefix
        base_name = re.sub(r"[^0-9a-zA-Z_]", "_", base_name)

        if not base_name[0].isalpha():
            base_name = f"{self.model_name_prefix}_{base_name}"

        usage_count = self._name_usage_counts.get(base_name, 0)
        self._name_usage_counts[base_name] = usage_count + 1

        return base_name if usage_count == 0 else f"{base_name}_{usage_count}"


    def _resolve_reference(
        self,
        reference: str
    ) -> Dict[str, Any] | None:
        if not self._root_schema or not reference.startswith("#/"):
            return None

        current_node: Any = self._root_schema

        for part in reference[2:].split("/"):
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]

            else:
                return None

        return current_node if isinstance(current_node, dict) else None


    def _get_type_signature(
        self, 
        type_hint: Any
    ) -> str:
        try:
            return repr(type_hint)
        except Exception:
            return str(type_hint)


    def _resolve_string_type(
        self,
        node: Dict[str, Any]
    ) -> Any:
        format_type = node.get("format")

        if format_type in self._FORMAT_TYPE_MAP:
            return self._FORMAT_TYPE_MAP[format_type]

        if isinstance(node.get("enum"), list) and node["enum"]:
            try:
                    return Literal[tuple(node["enum"])]

            except TypeError:
                return str

        min_length = node.get("minLength")
        max_length = node.get("maxLength")
        pattern = node.get("pattern")

        constraints: Dict[str, Any] = {}

        if isinstance(min_length, int):
            constraints["min_length"] = min_length

        if isinstance(max_length, int):
            constraints["max_length"] = max_length

        if isinstance(pattern, str):
            constraints["pattern"] = pattern

        return Annotated[str, StringConstraints(**constraints)] if constraints else str


    def _get_number_field_arguments(
        self,
        node: Dict[str, Any]
    ) -> Dict[str, Any]:
        field_arguments: Dict[str, Any] = {}
        for constraint_key in ("ge", "gt", "le", "lt"):
            if isinstance(node.get(constraint_key), (int, float)):
                field_arguments[constraint_key] = node[constraint_key]

        if isinstance(node.get("multipleOf"), (int, float)):
            field_arguments["multiple_of"] = node["multipleOf"]

        return field_arguments


    def _get_array_field_arguments(
        self,
        node: Dict[str, Any]
    ) -> Dict[str, Any]:
        field_arguments: Dict[str, Any] = {}
        if isinstance(node.get("minItems"), int):
            field_arguments["min_length"] = node["minItems"]
        if isinstance(node.get("maxItems"), int):
            field_arguments["max_length"] = node["maxItems"]
        return field_arguments


    def _resolve_union_type(
        self,
        nodes: List[Dict[str, Any]],
        name: str, path: Tuple[str, ...]
    ) -> Any:
        union_types: List[Any] = []

        for sub_node in nodes:
            resolved = self._resolve_type(sub_node, name=name, path=path + ("union",))
            union_types.append(resolved.python_type)

        non_null_types = [t for t in union_types if t is not type(None)]

        if len(union_types) == 2 and len(non_null_types) == 1 and any(t is type(None) for t in union_types):
                return Optional[non_null_types[0]]

        unique_types: List[Any] = []

        for type_hint in union_types:
            if all(self._get_type_signature(type_hint) != self._get_type_signature(existing) for existing in unique_types):
                unique_types.append(type_hint)

            return unique_types[0] if len(unique_types) == 1 else Union[tuple(unique_types)]


    def _resolve_type(
        self,
        node: Dict[str, Any],
        *,
        name: str,
        path: Tuple[str, ...]
    ) -> _ResolvedType:
        if isinstance(node.get("$ref"), str):
            reference = self._resolve_reference(node["$ref"])
            if reference is not None:
                return self._resolve_type(reference, name=name, path=path + ("$ref",))

            return _ResolvedType(Any, None, {})

        if node.get("nullable") is True:
            base_resolved = self._resolve_type({k: v for k, v in node.items() if k != "nullable"}, name=name, path=path)
            return _ResolvedType(Optional[base_resolved.python_type], base_resolved.default_value, base_resolved.field_arguments)

        if isinstance(node.get("oneOf"), list):
            union_type = self._resolve_union_type(node["oneOf"], name, path)
            return _ResolvedType(union_type, node.get("default"), {})

        if isinstance(node.get("anyOf"), list):
            union_type = self._resolve_union_type(node["anyOf"], name, path)
            return _ResolvedType(union_type, node.get("default"), {})

        if isinstance(node.get("allOf"), list):
            all_of_parts = node["allOf"]

            if all(isinstance(x, dict) and (x.get("type") == "object" or "properties" in x) for x in all_of_parts):
                merged_schema: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}

                part_titles: List[str] = []

                for part in all_of_parts:
                    part_titles.append(part.get("title", "") or "")
                    if isinstance(part.get("properties"), dict):
                        merged_schema["properties"].update(part["properties"])

                    if isinstance(part.get("required"), list):
                        merged_schema["required"] = list(set(merged_schema["required"]) | set(part["required"]))

                merged_schema["title"] = "AllOf_" + "_".join(filter(None, part_titles)) or name

                model = self._build_object_model(merged_schema, self._create_model_name(merged_schema["title"]), path=path + ("allOf",))

                return _ResolvedType(model, node.get("default"), {})

            union_type = self._resolve_union_type(all_of_parts, name, path)

            return _ResolvedType(union_type, node.get("default"), {})

        type_declaration = node.get("type")

        if isinstance(type_declaration, list):
            non_null_types = [x for x in type_declaration if x != "null"]

            if len(non_null_types) == 1:
                base_resolved = self._resolve_type({**node, "type": non_null_types[0]}, name=name, path=path)
                return _ResolvedType(Optional[base_resolved.python_type], node.get("default"), base_resolved.field_arguments)

            python_types = []

            for type_name in non_null_types:
                sub_resolved = self._resolve_type({**node, "type": type_name}, name=name, path=path + ("union",))
                python_types.append(sub_resolved.python_type)

            union_type = Union[tuple(python_types)] if python_types else Any

            return _ResolvedType(union_type, node.get("default"), {})

        if type_declaration in self._PRIMITIVE_TYPES:
            if type_declaration == "string":
                return _ResolvedType(self._resolve_string_type(node), node.get("default"), {"description": node.get("description")})

            if type_declaration in ("number", "integer"):
                base_type = float if type_declaration == "number" else int
                return _ResolvedType(base_type, node.get("default"), {**self._get_number_field_arguments(node), "description": node.get("description")})

            if type_declaration == "boolean":
                return _ResolvedType(bool, node.get("default"), {"description": node.get("description")})

            if type_declaration == "null":
                return _ResolvedType(type(None), None, {"description": node.get("description")})

        if type_declaration == "array" or ("items" in node and type_declaration is None):
            items_schema = node.get("items", {})
            item_resolved = self._resolve_type(items_schema, name=f"{name}Item", path=path + ("items",))
            return _ResolvedType(List[item_resolved.python_type], node.get("default"), {**self._get_array_field_arguments(node), "description": node.get("description")})  # type: ignore

        if type_declaration == "object" or "properties" in node or "additionalProperties" in node:
            properties = node.get("properties", {})
            additional_properties = node.get("additionalProperties", None)

            if not properties and isinstance(additional_properties, dict):
                value_type_resolved = self._resolve_type(additional_properties, name=f"{name}Value", path=path + ("additionalProperties",))
                return _ResolvedType(Dict[str, value_type_resolved.python_type], node.get("default"), {"description": node.get("description")})  # type: ignore

            model = self._build_object_model(node, self._create_model_name(node.get("title") or name), path=path)
            return _ResolvedType(model, node.get("default"), {})

        if isinstance(node.get("enum"), list):
            try:
                return _ResolvedType(Literal[tuple(node["enum"])], node.get("default"), {"description": node.get("description")})
            except TypeError:
                return _ResolvedType(Any, node.get("default"), {"description": node.get("description")})

        return _ResolvedType(Any, node.get("default"), {"description": node.get("description")})


    def _build_object_model(
        self,
        node: Dict[str, Any],
        name: str,
        *,
        path: Tuple[str, ...]
    ) -> Type[BaseModel]:
        properties: Dict[str, Any] = node.get("properties", {}) or {}
        required_fields: List[str] = list(node.get("required", []) or [])

        model_fields: Dict[str, Tuple[Any, Any]] = {}

        for property_name, property_schema in properties.items():
            property_title = property_schema.get("title") or f"{name}_{property_name}"
            resolved = self._resolve_type(property_schema, name=self._create_model_name(property_title), path=path + ("properties", property_name))
            is_required = property_name in required_fields
            default_value = resolved.default_value if resolved.default_value is not None else (None if not is_required else ...)
            field_definition = Field(default=default_value, description=property_schema.get("description"), **resolved.field_arguments)
            model_fields[property_name] = (resolved.python_type, field_definition)

        extra_behavior = "forbid" if node.get("additionalProperties") is False else "allow"
        base_class = type(f"{name}Base", (BaseModel,), {"model_config": ConfigDict(extra=extra_behavior)})
        model: Type[BaseModel] = create_model(name, __base__=base_class, **model_fields)

        return model



