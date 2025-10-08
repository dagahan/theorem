from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from google.protobuf.struct_pb2 import Struct, Value


def _int_if_whole(x: Any) -> Any:
    return int(x) if isinstance(x, float) and x.is_integer() else x


class ProtobufConverter:
    @staticmethod
    def _value_to_py(val: Value) -> Any:
        kind = val.WhichOneof("kind")
        if kind == "null_value":
            return None
        if kind == "number_value":
            return val.number_value
        if kind == "string_value":
            return val.string_value
        if kind == "bool_value":
            return val.bool_value
        if kind == "struct_value":
            return ProtobufConverter.struct_to_dict(val.struct_value)
        if kind == "list_value":
            return [ProtobufConverter._value_to_py(x) for x in val.list_value.values]
        return None


    @staticmethod
    def struct_to_dict(s: Struct) -> Dict[str, Any]:
        return {k: ProtobufConverter._value_to_py(v) for k, v in s.fields.items()}


    @staticmethod
    def deproto(obj: Any) -> Any:
        if isinstance(obj, Value):
            return ProtobufConverter._value_to_py(obj)
        if isinstance(obj, Struct):
            return ProtobufConverter.struct_to_dict(obj)
        if isinstance(obj, Mapping):
            return {k: ProtobufConverter.deproto(v) for k, v in obj.items()}
        if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            return [ProtobufConverter.deproto(x) for x in obj]
        return obj


    @staticmethod
    def convert_response_schema(schema_like: Any) -> Any:
        if not schema_like:
            return None

        if hasattr(schema_like, "model_dump"):
            data = schema_like.model_dump()
            data = ProtobufConverter.deproto(data)

            if not data.get("type"):
                data["type"] = "object"

            props = data.get("properties", {})
            if not isinstance(props, dict):
                data["properties"] = ProtobufConverter.deproto(props) if props is not None else {}
            
            for prop_name, prop_schema in data.get("properties", {}).items():
                if isinstance(prop_schema, dict):
                    for constraint in ["minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties"]:
                        if constraint in prop_schema:
                            prop_schema[constraint] = _int_if_whole(prop_schema[constraint])
            
            return data

        raw_type = getattr(schema_like, "type", None)
        typ = raw_type or "object"

        raw_props = getattr(schema_like, "properties", None)
        props = ProtobufConverter.deproto(raw_props) if raw_props is not None else {}
        if not isinstance(props, dict):
            props = {}

        required = list(getattr(schema_like, "required", []) or [])

        return {
            "type": typ,
            "properties": props,
            "required": required,
            "title": getattr(schema_like, "title", None) or None,
            "description": getattr(schema_like, "description", None) or None,
        }


