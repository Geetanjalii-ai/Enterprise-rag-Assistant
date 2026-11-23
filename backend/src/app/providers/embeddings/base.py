from abc import ABC, abstractmethod
from typing import List

from langchain_core.embeddings import Embeddings


class EmbeddingProvider(Embeddings, ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents/passages."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        pass
