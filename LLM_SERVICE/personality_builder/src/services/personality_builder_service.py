from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from src.adapters.policy_builder_adapter import PolicyBuilderAdapter
from src.pydantic_schemas.personality_builder import BuildPersonalityRequest, BuildPersonalityResponse, HealthStatus, Personality, ResponseSchema
from src.personalities.schema_store import ResponseSchemaStore
from src.core.logging import PersonalityBuilderLogger, SchemaStoreLogger, TemplateRenderLogger


class PersonalityBuilderService:
    def __init__(self) -> None:
        self.policy_adapter = PolicyBuilderAdapter()
        template_dir = Path(__file__).parent.parent / "personalities"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

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
                PersonalityBuilderLogger.log_personality_build_results(
                    persona_names=request.persona_names,
                    agent_name=agent_name,
                    personalities=[],
                    success=False,
                    error_message=error
                )

                return BuildPersonalityResponse(
                    personalities=[],
                    success=False,
                    error=error
                )

            policy_header = policy_header_response.policy_header
            personalities: list[Personality] = []

            for persona in request.persona_names:
                try:
                    template_name = self._template_name(persona)
                    template = self.jinja_env.get_template(template_name)

                    prompt = template.render(
                        policy_header=policy_header,
                        agent_name=agent_name
                    ).strip()

                    TemplateRenderLogger.log_template_render_results(
                        persona=persona,
                        template_name=template_name,
                        rendered_prompt=prompt,
                        success=True,
                        template_vars={
                            "policy_header_length": len(policy_header),
                            "agent_name": agent_name
                        }
                    )

                except Exception as ex:
                    logger.error(f"Template rendering failed for {persona}: {ex}")
                    TemplateRenderLogger.log_template_render_results(
                        persona=persona,
                        template_name=template_name,
                        rendered_prompt="",
                        success=False,
                        error_message=str(ex)
                    )
                    raise

                response_schema = self._load_response_schema(persona)
                
                personalities.append(Personality(
                    name=persona,
                    system_prompt=prompt,
                    response_schema=response_schema
                ))

            personalities_data = [
                {
                    "name": p.name,
                    "system_prompt": p.system_prompt,
                    "response_schema": p.response_schema.dict() if p.response_schema else None
                }
                for p in personalities
            ]
            
            PersonalityBuilderLogger.log_personality_build_results(
                persona_names=request.persona_names,
                agent_name=agent_name,
                personalities=personalities_data,
                success=True,
                policy_header=policy_header
            )

            return BuildPersonalityResponse(
                personalities=personalities,
                success=True
            )

        except Exception as ex:  # noqa: BLE001
            logger.error(f"Personality building failed: {ex}")
            PersonalityBuilderLogger.log_personality_build_results(
                persona_names=request.persona_names,
                agent_name=agent_name,
                personalities=[],
                success=False,
                error_message=str(ex)
            )

            return BuildPersonalityResponse(
                personalities=[],
                success=False,
                error=str(ex)
            )


    @staticmethod
    def _template_name(persona: str) -> str:
        return f"{persona.lower()}/system_prompt.jinja"


    def _load_response_schema(
        self,
        persona: str
    ) -> ResponseSchema | None:
        try:
            schema_dict = self.schema_store.load_schema(persona)
            if not schema_dict:
                logger.debug(f"No schema found for persona: {persona}")
                schema_file_path = f"src/personalities/{persona.lower()}/response.schema.json"
                SchemaStoreLogger.log_schema_load_results(
                    persona=persona,
                    schema_data=None,
                    success=True,
                    error_message="No schema file found",
                    schema_file_path=schema_file_path
                )
                return None
                
            response_schema = ResponseSchema(
                type=schema_dict.get("type", "object"),
                properties=schema_dict.get("properties", {}),
                required=schema_dict.get("required", []),
                title=schema_dict.get("title"),
                description=schema_dict.get("description")
            )
            
            schema_file_path = f"src/personalities/{persona.lower()}/response.schema.json"
            SchemaStoreLogger.log_schema_load_results(
                persona=persona,
                schema_data=schema_dict,
                success=True,
                schema_file_path=schema_file_path
            )
            
            return response_schema
            
        except Exception as ex:
            logger.error(f"Failed to load response schema for persona {persona}: {ex}")
            schema_file_path = f"src/personalities/{persona.lower()}/response.schema.json"
            SchemaStoreLogger.log_schema_load_results(
                persona=persona,
                schema_data=None,
                success=False,
                error_message=str(ex),
                schema_file_path=schema_file_path
            )

            return None



