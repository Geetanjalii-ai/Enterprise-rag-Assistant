from typing import Any, Dict, List

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import logger
from app.providers.reranker.base import BaseReranker


class JinaRerankerProvider(BaseReranker):
    def __init__(self, api_key: str = "", model_name: str = ""):
        settings = get_settings()
        self.api_key = api_key or settings.JINA_API_KEY
        configured_model = getattr(settings, "RERANKER_MODEL", "") or ""
        self.model_name = (model_name or configured_model or "jina-reranker-v2-base-multilingual").strip()
        self.url = "https://api.jina.ai/v1/rerank"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=False,
    )
    def _call_api(self, query: str, texts: List[str], top_n: int) -> List[Dict[str, Any]]:
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": texts,
            "top_n": top_n,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(self.url, headers=self.headers, json=payload)
            if resp.status_code != 200:
                logger.warning(f"Jina reranker API error {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        if not documents:
            return []
        if len(documents) <= 1:
            return documents[:top_k]

        texts = [doc.get("payload", {}).get("text", "") for doc in documents]

        # If Jina API key is available, call Jina Reranker
        if self.api_key:
            try:
                top_n = min(top_k, len(texts))
                results = self._call_api(query, texts, top_n=top_n)
                if results:
                    reranked: List[Dict[str, Any]] = []
                    for r in results:
                        orig_idx = r["index"]
                        doc = documents[orig_idx].copy()
                        doc["rerank_score"] = r.get("relevance_score", 0.0)
                        reranked.append(doc)
                    return reranked
            except Exception as e:
                logger.warning(f"Jina reranker call failed, falling back to hybrid ranking: {e}")

        # Fallback: Sort by existing hybrid/RRF score
        sorted_docs = sorted(
            documents,
            key=lambda x: x.get("score", x.get("rrf_score", 0.0)),
            reverse=True,
        )
        return sorted_docs[:top_k]
