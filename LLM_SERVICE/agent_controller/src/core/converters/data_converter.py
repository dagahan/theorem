from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import ContextDigestItem


class DataConverter:    
    
    @staticmethod
    def digests_to_payload(digests: list[ContextDigestItem]) -> list[dict[str, Any]]:
        return [
            {
                'title': digest.title,
                'summary': digest.summary,
                'source_chunk': digest.source_chunk,
            }
            for digest in digests
        ]
    

    @staticmethod
    def digests_to_json(digests: list[ContextDigestItem]) -> str:
        payload = {'digests': DataConverter.digests_to_payload(digests)}
        return json.dumps(payload, ensure_ascii=False)
    

    

    @staticmethod
    def digests_to_dict(digests: list[ContextDigestItem]) -> dict[str, Any]:
        return {
            'digests': DataConverter.digests_to_payload(digests),
            'count': len(digests)
        }
    

    @staticmethod
    def personality_to_dict(personality: Any) -> dict[str, Any]:
        if hasattr(personality, 'model_dump'):
            return personality.model_dump()  # type: ignore[no-any-return]

        elif hasattr(personality, '__dict__'):
            return personality.__dict__  # type: ignore[no-any-return]

        else:
            return {
                'name': getattr(personality, 'name', ''),
                'system_prompt': getattr(personality, 'system_prompt', ''),
                'response_schema': getattr(personality, 'response_schema', None)
            }
    

    @staticmethod
    def personalities_to_dict(personalities: Any) -> dict[str, Any]:
        if hasattr(personalities, 'personalities'):
            return {
                name: DataConverter.personality_to_dict(personality)
                for name, personality in personalities.personalities.items()
            }

        else:
            return {}
    

    @staticmethod
    def response_to_dict(response: Any) -> dict[str, Any]:
        if hasattr(response, 'model_dump'):
            return response.model_dump()  # type: ignore[no-any-return]

        elif hasattr(response, '__dict__'):
            return response.__dict__  # type: ignore[no-any-return]

        else:
            return {
                'success': getattr(response, 'success', False),
                'error': getattr(response, 'error', None),
                'data': getattr(response, 'data', None)
            }
    

    @staticmethod
    def graph_state_to_summary(state: dict[str, Any]) -> dict[str, Any]:
        return {
            'question_id': state.get('question_id', 'unknown'),
            'agent_name': state.get('agent_name', 'unknown'),
            'success': state.get('success', False),
            'error': state.get('error', ''),
            'timings_ms': state.get('timings_ms', {}),
            'context_digests_count': len(state.get('context_digests', [])),
            'has_personalities': bool(state.get('personalities')),
            'has_response': bool(state.get('response_answer')),
        }
    

    @staticmethod
    def safe_serialize(obj: Any) -> str:
        try:
            if hasattr(obj, 'model_dump'):
                return json.dumps(obj.model_dump(), ensure_ascii=False)

            elif hasattr(obj, '__dict__'):
                return json.dumps(obj.__dict__, ensure_ascii=False, default=str)

            else:
                return json.dumps(obj, ensure_ascii=False, default=str)

        except (TypeError, ValueError) as e:
            return f"<unable to serialize: {type(obj).__name__}>"
    

    @staticmethod
    def extract_error_details(error: Exception) -> dict[str, Any]:
        return {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_args': getattr(error, 'args', ()),
        }


