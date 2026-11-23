from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.logging import logger
from app.providers.vectorstore.base import VectorStoreProvider


class QdrantVectorStore(VectorStoreProvider):
    def __init__(self, url: str = "", api_key: str = "", collection: str = ""):
        settings = get_settings()
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.collection = collection or settings.QDRANT_COLLECTION
        self.client = QdrantClient(url=self.url, api_key=self.api_key)

    def upsert_points(self, points: List[Dict[str, Any]]) -> bool:
        if not points:
            return True

        qdrant_points = []
        for p in points:
            sparse_indices, sparse_values = p["sparse"]
            vector_dict = {
                "dense": p["dense"],
                "sparse": qmodels.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                ),
            }
            qdrant_points.append(
                qmodels.PointStruct(
                    id=p["id"],
                    vector=vector_dict,
                    payload=p["payload"],
                )
            )

        try:
            self.client.upsert(collection_name=self.collection, points=qdrant_points)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points to Qdrant: {e}")
            raise

    def delete_by_document_id(self, document_id: str) -> bool:
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete points for document {document_id}: {e}")
            raise

    def get_indexed_point_ids(self) -> List[str]:
        point_ids: List[str] = []
        offset = None
        while True:
            records, next_offset = self.client.scroll(
                collection_name=self.collection,
                limit=1000,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            for r in records:
                point_ids.append(str(r.id))
            if next_offset is None:
                break
            offset = next_offset
        return point_ids
