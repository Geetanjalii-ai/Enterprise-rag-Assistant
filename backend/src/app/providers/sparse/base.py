from abc import ABC, abstractmethod
from typing import List, Tuple


class SparseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[Tuple[List[int], List[float]]]:
        """Generate sparse BM25 vectors for documents. Returns list of (indices, values)."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> Tuple[List[int], List[float]]:
        """Generate sparse BM25 vector for query. Returns (indices, values)."""
        pass
