from __future__ import annotations
import asyncio
from typing import List
import torch
from loguru import logger
from src.core.utils import EnvTools
from sentence_transformers import CrossEncoder   # type: ignore
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from src.domain.models import Candidate


class NeuralRerankService:
    def __init__(self) -> None:
        self.model_id = EnvTools.required_load_env_var("RERANK_MODEL_NAME")
        self.batch = int(EnvTools.required_load_env_var("RERANK_BATCH"))
        self.max_len = int(EnvTools.required_load_env_var("RERANK_MAX_LEN"))
        self.device = 0 if torch.cuda.is_available() else -1
        try:
            if self.model_id.startswith("jinaai/jina-reranker-"):
                tok = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
                mdl = AutoModelForSequenceClassification.from_pretrained(self.model_id, trust_remote_code=True)

                self.pipe = pipeline(
                    "text-classification",
                    model=mdl,
                    tokenizer=tok,
                    device=self.device,
                    function_to_apply="sigmoid",
                    truncation=True
                )

                self._backend = "transformers"
                logger.info(f"NeuralRerankService: {self.model_id}")

            else:
                self.model = CrossEncoder(self.model_id, device="cuda" if self.device==0 else "cpu")
                self._backend = "cross_encoder"
                logger.info(f"NeuralRerankService: {self.model_id}")

        except Exception as ex:
            logger.warning(f"Reranker load failed: {ex}; fallback BAAI/bge-reranker-base")
            self.model_id = "BAAI/bge-reranker-base"
            self.model = CrossEncoder(self.model_id, device="cuda" if self.device==0 else "cpu")
            self._backend = "cross_encoder"


    async def rerank(
        self,
        question: str,
        candidates: List[Candidate],
        topn: int
    ) -> List[Candidate]:
        if not candidates:
            return []

        limited = candidates[:topn]
        if self._backend == "transformers":
            items = [{"text": question, "text_pair": c.text} for c in limited]
            preds = await asyncio.to_thread(
                self.pipe, items,
                batch_size=self.batch, truncation=True,
                max_length=self.max_len, padding=False, top_k=None
            )

            scores = [float(o["score"]) for o in preds]

        else:
            pairs = [(question, c.text) for c in limited]
            scores = await asyncio.to_thread(
                self.model.predict, pairs,
                batch_size=self.batch, show_progress_bar=False
            )

        out: List[Candidate] = []
        for c, s in zip(limited, scores):
            cc = Candidate(**{**c.__dict__})
            cc.score_nn = float(s)
            out.append(cc)

        out.sort(key=lambda x: x.score_nn, reverse=True)

        return out


