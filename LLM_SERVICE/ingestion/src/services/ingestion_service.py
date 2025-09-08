from typing import Dict, List, Any
from loguru import logger
from src.services.ingestion_orchestrator import IngestionOrchestrator
from src.grpc.client.registry_grpc_clients import RegistryGrpcClients
from src.core.utils import EnvTools


class IngestionService:
    def __init__(self, grpc_clients: RegistryGrpcClients) -> None:
        self.orchestrator = IngestionOrchestrator(grpc_clients)
        self.collection_name = EnvTools.required_load_env_var("QDRANT_COLLECTION_NAME")


    async def health_check(self) -> Dict[str, str]:
        try:
            result = await self.orchestrator.vector_store_service.health_check()
            return result
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


    async def _process_document(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> None:
        await self.orchestrator.ingest_document(doc_id, text, metadata, self.collection_name)


    async def search_documents(
        self,
        query: str,
        limit: int = 25,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        return await self.orchestrator.search_documents(query, self.collection_name, limit, score_threshold)


    async def delete_document(
        self,
        doc_id: str
    ) -> Dict[str, str]:
        await self.orchestrator.delete_document(doc_id, self.collection_name)
        return {"status": "deleted", "doc_id": doc_id}


    async def list_collections(self) -> List[str]:
        cols = await self.orchestrator.vector_store_service.get_collections()
        return [c["name"] for c in cols]


    async def get_service_stats(self) -> Dict[str, Any]:
        return await self.orchestrator.get_service_stats()


