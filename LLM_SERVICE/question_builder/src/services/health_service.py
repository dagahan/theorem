from __future__ import annotations

from src.services.llm_expansion_service import LLMExpansionService
from src.core.utils import EnvTools


class HealthService:
    def __init__(self) -> None:
        self.llm_expansion_service = LLMExpansionService()
        self.model_id = EnvTools.required_load_env_var("VLLM_MODEL_NAME")


    async def health_check_service(
        self,
        service_name: str
    ) -> tuple[str, str]:
        if service_name == "all":
            llm_healthy = await self.llm_expansion_service.health_check()
            
            status = "healthy" if llm_healthy else "unhealthy"
            
            return status, self.model_id
        
        return "unknown", ""





