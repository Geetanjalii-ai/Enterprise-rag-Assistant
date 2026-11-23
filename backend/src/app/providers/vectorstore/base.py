from abc import ABC, abstractmethod
from typing import Any, Dict, List


class VectorStoreProvider(ABC):
    @abstractmethod
    def upsert_points(
        self,
        points: List[Dict[str, Any]],
    ) -> bool:
        """Upsert points containing id, vector dict (dense, sparse), and payload."""
        pass

    @abstractmethod
    def delete_by_document_id(self, document_id: str) -> bool:
        """Delete all chunk points belonging to a document."""
        pass

    @abstractmethod
    def get_indexed_point_ids(self) -> List[str]:
        """Retrieve all point IDs currently indexed in the vector store."""
        pass
