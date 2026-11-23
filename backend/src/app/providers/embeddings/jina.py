from typing import List

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import logger
from app.providers.embeddings.base import EmbeddingProvider


class JinaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str = "", model_name: str = ""):
        settings = get_settings()
        self.api_key = api_key or settings.JINA_API_KEY
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.url = "https://api.jina.ai/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True,
    )
    def _call_api(self, input_texts: List[str], task: str = "text-matching") -> List[List[float]]:
        if not input_texts:
            return []

        payload = {
            "model": self.model_name,
            "task": task,
            "input": input_texts,
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self.url, headers=self.headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Sort by index in case API returns out of order
            sorted_items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_items]

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                batch_embeddings = self._call_api(batch, task="retrieval.passage")
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Failed to embed document batch {i}: {e}")
                raise
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        res = self._call_api([text], task="retrieval.query")
        return res[0]
