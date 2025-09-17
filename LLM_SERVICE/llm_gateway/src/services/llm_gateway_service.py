import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List

import grpc
import httpx
from loguru import logger

from protobuf_stubs import llm_gateway_pb2, llm_gateway_pb2_grpc, rag_pb2, rag_pb2_grpc
from src.core.utils import EnvTools
from src.grpc.grpc_utils import GrpcTools

grpc_tools = GrpcTools()


class LLMGatewayService(llm_gateway_pb2_grpc.LLMGatewayServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self.vllm_host = EnvTools.required_load_env_var("VLLM_TALKING_HOST")
        self.vllm_port = EnvTools.required_load_env_var("VLLM_TALKING_PORT")
        self.vllm_model_name = EnvTools.required_load_env_var("VLLM_MODEL_NAME")
        
        self.rag_host = EnvTools.get_service_host("rag")
        self.rag_port = EnvTools.get_service_grpc_port("rag")
        
        self.default_collection = EnvTools.required_load_env_var("DEFAULT_RAG_COLLECTION")
        
        self.vllm_base_url = f"http://{self.vllm_host}:{self.vllm_port}"
        self.rag_channel = grpc.insecure_channel(f"{self.rag_host}:{self.rag_port}")
        self.rag_client = rag_pb2_grpc.RAGServiceStub(self.rag_channel)


    @grpc_tools.log_grpc_request("Health")
    def Health(
        self,
        request: llm_gateway_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> llm_gateway_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            llm_status = self._check_vllm_health()
            rag_status = self._check_rag_health()
            embedder_status = "healthy"  # Assume healthy for now
            
            overall_status = "healthy" if llm_status == "healthy" and rag_status == "healthy" else "unhealthy"

            response = llm_gateway_pb2.HealthResponse(
                status=overall_status,
                llm_status=llm_status,
                rag_status=rag_status,
                embedder_status=embedder_status,
            )
            
            grpc_tools.validate_proto(response, context)
            return response

        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return llm_gateway_pb2.HealthResponse(
                status="unhealthy",
                llm_status="unknown",
                rag_status="unknown",
                embedder_status="unknown"
            )


    @grpc_tools.log_grpc_request("GenerateAnswer")
    def GenerateAnswer(
        self,
        request: llm_gateway_pb2.GenerateAnswerRequest,
        context: grpc.ServicerContext,
    ) -> llm_gateway_pb2.GenerateAnswerResponse:
        try:
            grpc_tools.validate_proto(request, context)
            
            start_time = time.time()
            
            max_tokens = self._determine_optimal_max_tokens(request.question, request.max_tokens)
            answer, tokens_used = self._generate_answer_direct(
                question=request.question,
                max_tokens=max_tokens
            )
            
            generation_time = time.time() - start_time
            logger.info(f"Direct LLM generation completed in {generation_time:.2f}s")
            
            response = llm_gateway_pb2.GenerateAnswerResponse(
                answer=answer,
                success=True,
                error="",
                tokens_used=tokens_used
            )
            
            return response

        except Exception as ex:
            logger.exception("GenerateAnswer failed")
            return llm_gateway_pb2.GenerateAnswerResponse(
                answer="",
                success=False,
                error=str(ex),
                tokens_used=0
            )

    @grpc_tools.log_grpc_request("GenerateAnswerWithRAG")
    def GenerateAnswerWithRAG(
        self,
        request: llm_gateway_pb2.GenerateAnswerWithRAGRequest,
        context: grpc.ServicerContext,
    ) -> llm_gateway_pb2.GenerateAnswerWithRAGResponse:
        try:
            grpc_tools.validate_proto(request, context)
            
            start_time = time.time()
            
            # Step 1: Get RAG context
            rag_start = time.time()
            rag_context = self._get_rag_context(request.question)
            rag_time = time.time() - rag_start
            
            if not rag_context:
                return llm_gateway_pb2.GenerateAnswerWithRAGResponse(
                    answer="Недостаточно данных для ответа на ваш вопрос.",
                    rag_context=[],
                    success=False,
                    error="No relevant context found",
                    tokens_used=0,
                    generation_time=0.0,
                    rag_time=rag_time
                )
            
            # Step 2: Generate answer with vLLM
            generation_start = time.time()
            max_tokens = self._determine_optimal_max_tokens(request.question, request.max_tokens)
            answer, tokens_used = self._generate_answer_with_context(
                question=request.question,
                rag_context=rag_context,
                max_tokens=max_tokens
            )
            generation_time = time.time() - generation_start
            
            total_time = time.time() - start_time
            logger.info(f"RAG+LLM generation completed in {total_time:.2f}s (RAG: {rag_time:.2f}s, LLM: {generation_time:.2f}s)")
            
            response = llm_gateway_pb2.GenerateAnswerWithRAGResponse(
                answer=answer,
                rag_context=[],  # We don't return individual context items in this simplified version
                success=True,
                error="",
                tokens_used=tokens_used,
                generation_time=generation_time,
                rag_time=rag_time
            )
            
            return response

        except Exception as ex:
            logger.exception("GenerateAnswerWithRAG failed")
            return llm_gateway_pb2.GenerateAnswerWithRAGResponse(
                answer="",
                rag_context=[],
                success=False,
                error=str(ex),
                tokens_used=0,
                generation_time=0.0,
                rag_time=0.0
            )

    def _check_vllm_health(self) -> str:
        try:
            response = httpx.get(f"{self.vllm_base_url}/health", timeout=25.0)
            return "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            return "unhealthy"

    def _check_rag_health(self) -> str:
        try:
            health_request = rag_pb2.HealthRequest()
            health_response = self.rag_client.Health(health_request, timeout=25.0)
            return str(health_response.status)
        except Exception:
            return "unhealthy"

    def _get_rag_context(self, question: str) -> str:
        try:
            search_request = rag_pb2.SearchRequest(
                query=question,
                collection_name=self.default_collection
            )
            search_response = self.rag_client.Search(search_request, timeout=60.0)
            
            if not search_response.success or not search_response.result:
                return ""
                
            return str(search_response.result)
            
        except Exception as ex:
            logger.error(f"RAG context retrieval failed: {ex}")
            return ""

    def _generate_answer_with_context(
        self, 
        question: str, 
        rag_context: str, 
        max_tokens: int = 1024, 
        temperature: float = 0.7
    ) -> tuple[str, int]:
        try:
            # Format RAG context as separate message
            formatted_context = self._format_rag_context(rag_context)
            
            messages = [
                {
                    "role": "assistant",
                    "content": formatted_context
                },
                {
                    "role": "user", 
                    "content": question
                }
            ]
            
            payload = {
                "model": self.vllm_model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
                "stop": ["RAG_CONTEXT_END"]
            }
            
            response = httpx.post(
                f"{self.vllm_base_url}/v1/chat/completions",
                json=payload,
                timeout=150.0
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            
            return answer, tokens_used
            
        except Exception as ex:
            logger.error(f"vLLM generation failed: {ex}")
            raise

    def _generate_answer_direct(
        self, 
        question: str, 
        max_tokens: int = 1024, 
        temperature: float = 0.7
    ) -> tuple[str, int]:
        try:
            messages = [
                {
                    "role": "user", 
                    "content": question
                }
            ]
            
            payload = {
                "model": self.vllm_model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            response = httpx.post(
                f"{self.vllm_base_url}/v1/chat/completions",
                json=payload,
                timeout=150.0
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            
            return answer, tokens_used
            
        except Exception as ex:
            logger.error(f"Direct vLLM generation failed: {ex}")
            raise

    def _determine_optimal_max_tokens(self, question: str, requested_tokens: int) -> int:
        if requested_tokens > 0:
            return min(requested_tokens, 4096)
        
        question_length = len(question)
        
        if question_length < 200:
            return 512
        elif question_length < 500:
            return 1024
        elif "геометр" in question.lower() or "треугольник" in question.lower() or "окружность" in question.lower():
            return 1536
        elif "производн" in question.lower() or "интеграл" in question.lower() or "предел" in question.lower():
            return 1536
        else:
            return 1024

    def _format_rag_context(self, rag_result: str) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        formatted_context = f"""RAG_CONTEXT_START
snapshot={current_date}; policy=closed-book

{rag_result}

Инструкции: используй только факты из блока выше. Если фактов мало, напиши «недостаточно данных» и задай до 2 уточнений.
RAG_CONTEXT_END"""
        
        return formatted_context

    @grpc_tools.log_grpc_request("Search")
    def Search(
        self,
        request: llm_gateway_pb2.SearchRequest,
        context: grpc.ServicerContext,
    ) -> llm_gateway_pb2.SearchResponse:
        try:
            grpc_tools.validate_proto(request, context)
            
            search_request = rag_pb2.SearchRequest(
                query=request.query,
                collection_name=request.collection_name,
                limit=request.limit,
                score_threshold=request.score_threshold
            )
            search_response = self.rag_client.Search(search_request, timeout=60.0)
            
            if not search_response.success:
                return llm_gateway_pb2.SearchResponse(
                    results=[],
                    success=False,
                    error=str(search_response.error)
                )
            
            results = []
            for result in search_response.results:
                results.append(llm_gateway_pb2.SearchResult(
                    doc_id=result.doc_id,
                    text=result.text,
                    score=result.score,
                    pages=list(result.pages),
                    paragraph_id=result.paragraph_id,
                    chunk_id=result.chunk_id
                ))
            
            return llm_gateway_pb2.SearchResponse(
                results=results,
                success=True,
                error=""
            )

        except Exception as ex:
            logger.exception("Search failed")
            return llm_gateway_pb2.SearchResponse(
                results=[],
                success=False,
                error=str(ex)
            )