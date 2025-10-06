from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from src.adapters.policy_builder_adapter import PolicyBuilderAdapter
from src.pydantic_schemas.personality_builder import BuildPersonalityRequest, BuildPersonalityResponse, HealthStatus, Personality, ResponseSchema
from src.personalities.schema_store import ResponseSchemaStore


class PersonalityBuilderService:
    def __init__(self) -> None:
        self.policy_adapter = PolicyBuilderAdapter()
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Initialize schema store
        personalities_dir = Path(__file__).parent.parent / "personalities"
        self.schema_store = ResponseSchemaStore(personalities_dir)

    async def get_health_status(self) -> HealthStatus:
        try:
            policy_status = "healthy" if await self.policy_adapter.health_check() else "unhealthy"
            return HealthStatus(
                status="healthy",
                policy_builder_status=policy_status
            )

        except Exception as ex:  # noqa: BLE001
            logger.error(f"Health check failed: {ex}")
            return HealthStatus(
                status="unhealthy",
                policy_builder_status="unknown"
            )


    async def build_personalities(
        self,
        request: BuildPersonalityRequest,
        agent_name: str = ""
    ) -> BuildPersonalityResponse:
        try:
            policy_header_response = await self.policy_adapter.get_policy_header()

            if not policy_header_response.success:
                error = policy_header_response.error or 'policy header unavailable'
                return BuildPersonalityResponse(
                    personalities=[],
                    success=False,
                    error=error
                )

            policy_header = policy_header_response.policy_header
            personalities: list[Personality] = []

            for persona in request.persona_names:
                template = self.jinja_env.get_template(self._template_name(persona))

                prompt = template.render(
                    policy_header=policy_header,
                    agent_name=agent_name
                ).strip()

                # Load schema from file
                response_schema = self._load_response_schema(persona)
                personalities.append(Personality(
                    name=persona,
                    system_prompt=prompt,
                    response_schema=response_schema
                ))

            return BuildPersonalityResponse(
                personalities=personalities,
                success=True
            )

        except Exception as ex:  # noqa: BLE001
            logger.error(f"Personality building failed: {ex}")
            return BuildPersonalityResponse(
                personalities=[],
                success=False,
                error=str(ex)
            )


    @staticmethod
    def _template_name(persona: str) -> str:
        return f"{persona.lower()}_prompt.jinja"


    def _load_response_schema(self, persona: str) -> ResponseSchema | None:
        """
        Загружает схему ответа для персоналии из файла.
        Возвращает ResponseSchema объект или None, если схема не найдена.
        """
        try:
            schema_dict = self.schema_store.load_schema(persona)
            if not schema_dict:
                logger.debug(f"No schema found for persona: {persona}")
                return None
                
            # Конвертируем JSON Schema в ResponseSchema
            return ResponseSchema(
                type=schema_dict.get("type", "object"),
                properties=schema_dict.get("properties", {}),
                required=schema_dict.get("required", []),
                title=schema_dict.get("title"),
                description=schema_dict.get("description")
            )
            
        except Exception as ex:
            logger.error(f"Failed to load response schema for persona {persona}: {ex}")
            return None



