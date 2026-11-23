from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank a list of retrieved candidate documents given a query."""
        pass
