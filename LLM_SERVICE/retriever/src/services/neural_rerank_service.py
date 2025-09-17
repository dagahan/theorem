# src/services/neural_rerank_service.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, List
import torch
from loguru import logger
from src.core.utils import EnvTools

from sentence_transformers import CrossEncoder    # type: ignore
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline


class NeuralRerankService:
    def __init__(self) -> None:
        self.model_id = EnvTools.required_load_env_var("RERANK_MODEL_NAME")
        self.neural_rerank_batch_size = int(EnvTools.required_load_env_var("RERANK_BATCH"))
        self.max_length = int(EnvTools.required_load_env_var("RERANK_MAX_LEN"))
        self.device = 0 if torch.cuda.is_available() else -1


        try:
            if self.model_id.startswith("jinaai/jina-reranker-"):
                # Загрузка через HF Transformers с кастомным кодом
                tok = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
                mdl = AutoModelForSequenceClassification.from_pretrained(
                    self.model_id, trust_remote_code=True
                )

                self.pipe = pipeline(
                    "text-classification",
                    model=mdl,
                    tokenizer=tok,
                    device=self.device,
                    function_to_apply="sigmoid",
                    truncation=True
                )

                self._backend = "transformers"
                logger.info(f"NeuralRerankService initialized with Jina model {self.model_id} on {'cuda' if self.device==0 else 'cpu'}")

            else:
                # Классический кросс-энкодер без кастомного кода
                self.model = CrossEncoder(self.model_id, device="cuda" if self.device==0 else "cpu")
                self._backend = "cross_encoder"
                logger.info(f"NeuralRerankService initialized with model {self.model_id} on {'cuda' if self.device==0 else 'cpu'}")

        except Exception as ex:
            logger.warning(f"Reranker load failed ({self.model_id}): {ex}; fallback to BAAI/bge-reranker-base")
            self.model_id = "BAAI/bge-reranker-base"
            self.model = CrossEncoder(self.model_id, device="cuda" if self.device==0 else "cpu")
            self._backend = "cross_encoder"
            logger.info(f"NeuralRerankService initialized with fallback model {self.model_id} on {'cuda' if self.device==0 else 'cpu'}")


    async def neural_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        topn: int
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        limited = candidates[:topn]

        if self._backend == "transformers":
            # Пары для пайплайна; токен-трейнкет контролируем max_length
            items = [{"text": query, "text_pair": c["document_data"]["text"]} for c in limited]
            preds = await asyncio.to_thread(
                self.pipe,
                items,
                batch_size=self.neural_rerank_batch_size,
                truncation=True,
                max_length=self.max_length,
                padding=False,
                top_k=None,
            )
            scores = [float(o["score"]) for o in preds]
        else:
            # CrossEncoder сам батчит; обрежем по токенам внутри модели, а не по символам
            pairs = [(query, c["document_data"]["text"]) for c in limited]
            scores = await asyncio.to_thread(
                self.model.predict,
                pairs,
                batch_size=self.neural_rerank_batch_size,
                show_progress_bar=False,
                # max_length работает у части моделей; если нет — оставь как есть
            )

        results = []
        for cand, score in zip(limited, scores):
            r = dict(cand)
            r["neural_score"] = float(score)
            results.append(r)

        results.sort(key=lambda x: x["neural_score"], reverse=True)
        for i, r in enumerate(results, 1):
            r["rank_position"] = min(r.get("rank_position", i), i)
        return results


