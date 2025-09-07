import asyncio
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import grpc
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.core.config import ConfigLoader
from src.core.logging import InterceptHandler, LogSetup
from src.core.utils import EnvTools

import protobuf_stubs.rag_pb2 as rag_pb2
import protobuf_stubs.rag_pb2_grpc as rag_pb2_grpc
import protobuf_stubs.embedder_pb2 as embedder_pb2
import protobuf_stubs.embedder_pb2_grpc as embedder_pb2_grpc


class RagService(rag_pb2_grpc.RagServiceServicer):
    def __init__(self) -> None:
        self.config = ConfigLoader()
        self.qdrant_client = None
        self.embedder_stub = None
        self.collection_name = EnvTools.get_env_var("QDRANT_COLLECTION_NAME", "docs_active")
        
        # Настройки поиска
        self.default_top_k = int(EnvTools.get_env_var("DEFAULT_TOP_K", "25"))
        self.default_neighbor_window = int(EnvTools.get_env_var("DEFAULT_NEIGHBOR_WINDOW", "2"))
        self.default_include_whole_paragraph = EnvTools.get_env_var("DEFAULT_INCLUDE_WHOLE_PARAGRAPH", "true").lower() == "true"
        
        self._init_clients()

    def _init_clients(self) -> None:
        """Инициализация клиентов Qdrant и Embedder."""
        try:
            # Qdrant клиент
            qdrant_host = EnvTools.get_env_var("QDRANT_HOST", "qdrant")
            qdrant_port = int(EnvTools.get_env_var("QDRANT_PORT", "6333"))
            
            self.qdrant_client = QdrantClient(
                host=qdrant_host,
                port=qdrant_port,
                timeout=30
            )
            
            # Embedder gRPC клиент
            embedder_host = EnvTools.get_env_var("EMBEDDER_HOST", "embedder")
            embedder_port = EnvTools.get_env_var("EMBEDDER_PORT", "50051")
            
            channel = grpc.aio.insecure_channel(f"{embedder_host}:{embedder_port}")
            self.embedder_stub = embedder_pb2_grpc.EmbedderServiceStub(channel)
            
            logger.info(f"RAG service initialized. Qdrant: {qdrant_host}:{qdrant_port}, Embedder: {embedder_host}:{embedder_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise

    def Health(self, request, context):
        """Health check endpoint."""
        try:
            # Проверяем подключение к Qdrant
            collections = self.qdrant_client.get_collections()
            
            # Проверяем подключение к Embedder
            embedder_request = embedder_pb2.HealthRequest()
            embedder_response = self.embedder_stub.Health(embedder_request, timeout=5)
            
            if embedder_response.status == "healthy":
                return rag_pb2.HealthResponse(status="healthy")
            else:
                return rag_pb2.HealthResponse(status="unhealthy")
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return rag_pb2.HealthResponse(status="unhealthy")

    async def SemanticSearch(self, request, context):
        """Семантический поиск с расширением контекста."""
        try:
            # Параметры поиска
            query = request.query.strip()
            if not query:
                return rag_pb2.SemanticSearchResponse(
                    chunks=[],
                    merged_text=""
                )
            
            top_k = request.top_k if request.top_k > 0 else self.default_top_k
            neighbor_window = request.neighbor_window if request.neighbor_window > 0 else self.default_neighbor_window
            include_whole_paragraph = request.include_whole_paragraph if request.include_whole_paragraph else self.default_include_whole_paragraph
            
            # Получаем вектор запроса
            embedder_request = embedder_pb2.EmbedRequest(
                text=query,
                normalize=True
            )
            embedder_response = await self.embedder_stub.Embed(embedder_request, timeout=10)
            
            if not embedder_response.success:
                logger.error(f"Failed to embed query: {embedder_response.error}")
                return rag_pb2.SemanticSearchResponse(
                    chunks=[],
                    merged_text=""
                )
            
            query_vector = embedder_response.vector
            
            # Поиск в Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=("text", query_vector),
                limit=top_k,
                with_payload=True,
                with_vectors=False
            )
            
            if not search_results:
                return rag_pb2.SemanticSearchResponse(
                    chunks=[],
                    merged_text=""
                )
            
            # Собираем нужные чанки согласно логике
            wanted_chunks: Set[Tuple[str, int]] = set()  # (doc_id, chunk_id)
            chunks_by_doc_para: Dict[str, Dict[int, List[Dict]]] = defaultdict(lambda: defaultdict(list))
            
            # 1) Первичный набор из результатов поиска
            for hit in search_results:
                payload = hit.payload
                doc_id = payload.get("doc_id")
                paragraph_id = payload.get("paragraph_id")
                chunk_id = payload.get("chunk_id")
                
                if not all([doc_id, paragraph_id is not None, chunk_id is not None]):
                    continue
                
                wanted_chunks.add((doc_id, chunk_id))
                
                # Если нужно включить весь абзац
                if include_whole_paragraph:
                    # Получаем все чанки этого абзаца
                    para_chunks = self._get_chunks_by_paragraph(doc_id, paragraph_id)
                    for chunk in para_chunks:
                        wanted_chunks.add((doc_id, chunk["chunk_id"]))
                
                # Добавляем соседние чанки в радиусе n±window
                neighbor_chunks = self._get_neighbor_chunks(doc_id, chunk_id, neighbor_window)
                for chunk in neighbor_chunks:
                    wanted_chunks.add((doc_id, chunk["chunk_id"]))
            
            # 2) Получаем фактические чанки
            all_chunks = self._fetch_chunks_by_ids(wanted_chunks)
            
            # 3) Сортируем и склеиваем текст
            merged_text = self._merge_chunks_to_text(all_chunks)
            
            # Создаем ответ
            response_chunks = []
            for chunk in all_chunks:
                response_chunks.append(rag_pb2.Chunk(
                    id=chunk["id"],
                    doc_id=chunk["doc_id"],
                    paragraph_id=chunk["paragraph_id"],
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"]
                ))
            
            return rag_pb2.SemanticSearchResponse(
                chunks=response_chunks,
                merged_text=merged_text
            )
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return rag_pb2.SemanticSearchResponse(
                chunks=[],
                merged_text=""
            )

    def _get_chunks_by_paragraph(self, doc_id: str, paragraph_id: int) -> List[Dict]:
        """Получить все чанки абзаца."""
        try:
            results = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        ),
                        models.FieldCondition(
                            key="paragraph_id",
                            match=models.MatchValue(value=paragraph_id)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True
            )
            
            chunks = []
            for point in results[0]:
                chunks.append({
                    "chunk_id": point.payload.get("chunk_id"),
                    "doc_id": point.payload.get("doc_id"),
                    "paragraph_id": point.payload.get("paragraph_id"),
                    "text": point.payload.get("text"),
                    "id": str(point.id)
                })
            
            return chunks
        except Exception as e:
            logger.error(f"Error getting chunks by paragraph: {e}")
            return []

    def _get_neighbor_chunks(self, doc_id: str, chunk_id: int, window: int) -> List[Dict]:
        """Получить соседние чанки в радиусе window."""
        try:
            # Получаем все чанки документа
            results = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        )
                    ]
                ),
                limit=10000,
                with_payload=True
            )
            
            chunks = []
            for point in results[0]:
                point_chunk_id = point.payload.get("chunk_id")
                if point_chunk_id is not None and abs(point_chunk_id - chunk_id) <= window:
                    chunks.append({
                        "chunk_id": point_chunk_id,
                        "doc_id": point.payload.get("doc_id"),
                        "paragraph_id": point.payload.get("paragraph_id"),
                        "text": point.payload.get("text"),
                        "id": str(point.id)
                    })
            
            return chunks
        except Exception as e:
            logger.error(f"Error getting neighbor chunks: {e}")
            return []

    def _fetch_chunks_by_ids(self, wanted_chunks: Set[Tuple[str, int]]) -> List[Dict]:
        """Получить чанки по их ID."""
        try:
            all_chunks = []
            
            # Группируем по doc_id для эффективности
            chunks_by_doc = defaultdict(list)
            for doc_id, chunk_id in wanted_chunks:
                chunks_by_doc[doc_id].append(chunk_id)
            
            # Получаем чанки для каждого документа
            for doc_id, chunk_ids in chunks_by_doc.items():
                results = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value=doc_id)
                            )
                        ]
                    ),
                    limit=10000,
                    with_payload=True
                )
                
                for point in results[0]:
                    point_chunk_id = point.payload.get("chunk_id")
                    if point_chunk_id in chunk_ids:
                        all_chunks.append({
                            "chunk_id": point_chunk_id,
                            "doc_id": point.payload.get("doc_id"),
                            "paragraph_id": point.payload.get("paragraph_id"),
                            "text": point.payload.get("text"),
                            "id": str(point.id)
                        })
            
            return all_chunks
        except Exception as e:
            logger.error(f"Error fetching chunks by IDs: {e}")
            return []

    def _merge_chunks_to_text(self, chunks: List[Dict]) -> str:
        """Склеить чанки в текст с разделением абзацев."""
        if not chunks:
            return ""
        
        # Сортируем по doc_id, paragraph_id, chunk_id
        chunks.sort(key=lambda x: (x["doc_id"], x["paragraph_id"], x["chunk_id"]))
        
        merged_lines = []
        last_paragraph_id = None
        
        for chunk in chunks:
            paragraph_id = chunk["paragraph_id"]
            
            # Добавляем пустую строку между абзацами
            if last_paragraph_id is not None and paragraph_id != last_paragraph_id:
                merged_lines.append("")
            
            merged_lines.append(chunk["text"])
            last_paragraph_id = paragraph_id
        
        return "\n".join(merged_lines).strip()


class Service:
    def __init__(self) -> None:
        self.config = ConfigLoader()
        self.intercept_handler = InterceptHandler()
        self.logger_setup = LogSetup()
        self.service_name = self.config.get("project", "name")
        self.server = None

    async def run_service(self) -> None:
        self.logger_setup.configure()
        
        # Настройка gRPC сервера
        server_options = [
            ('grpc.max_send_message_length', 64 * 1024 * 1024),  # 64MB
            ('grpc.max_receive_message_length', 64 * 1024 * 1024),  # 64MB
            ('grpc.keepalive_time_ms', 30000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', True),
        ]
        
        server = grpc.aio.server(options=server_options)
        rag_pb2_grpc.add_RagServiceServicer_to_server(RagService(), server)
        
        host = EnvTools.get_service_ip(self.service_name)
        port = EnvTools.get_service_port(self.service_name)
        
        listen_addr = f"{host}:{port}"
        server.add_insecure_port(listen_addr)
        
        logger.info(f"Starting RAG service on {listen_addr}")
        
        await server.start()
        self.server = server
        
        try:
            await server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            await server.stop(grace=5.0)
            logger.info("Service stopped gracefully")


if __name__ == "__main__":
    try:
        service = Service()
        asyncio.run(service.run_service())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as error:
        logger.critical(f"Service crashed: {error}")
        import sys
        sys.exit(1)