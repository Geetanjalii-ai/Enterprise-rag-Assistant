from typing import Any, Dict, List, Optional

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import User
from app.providers.embeddings.jina import JinaEmbeddingProvider
from app.providers.reranker.jina import JinaRerankerProvider
from app.providers.sparse.fastembed_bm25 import FastEmbedBM25Provider
from app.retrieval.access_check import verify_neon_second_lock
from app.retrieval.access_filter import build_qdrant_access_filter


class HybridSearchService:
    def __init__(
        self,
        db: Session,
        embedder: Optional[JinaEmbeddingProvider] = None,
        sparser: Optional[FastEmbedBM25Provider] = None,
        reranker: Optional[JinaRerankerProvider] = None,
    ):
        settings = get_settings()
        self.db = db
        self.embedder = embedder or JinaEmbeddingProvider()
        self.sparser = sparser or FastEmbedBM25Provider()
        self.reranker = reranker or JinaRerankerProvider()
        self.collection_name = settings.QDRANT_COLLECTION
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

    def search(
        self,
        query: str,
        user: User,
        limit: int = 5,
        prefetch_limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Perform role-aware hybrid dense+sparse search with RRF fusion,

        second-lock PostgreSQL verification, and optional reranking.
        """
        if not query.strip():
            return []

        # 1. Build authoritative access filter (SEC-1)
        access_filter = build_qdrant_access_filter(user)

        # 2. Compute dense and sparse query embeddings
        dense_query = self.embedder.embed_query(query)
        sparse_indices, sparse_values = self.sparser.embed_query(query)

        # 3. Server-side hybrid search with RRF fusion in Qdrant
        prefetch = [
            qmodels.Prefetch(
                query=dense_query,
                using="dense",
                filter=access_filter,
                limit=prefetch_limit,
            ),
            qmodels.Prefetch(
                query=qmodels.SparseVector(indices=sparse_indices, values=sparse_values),
                using="sparse",
                filter=access_filter,
                limit=prefetch_limit,
            ),
        ]

        try:
            points_res = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
                limit=prefetch_limit,
                with_payload=True,
            )
            raw_candidates = [
                {
                    "point_id": p.id,
                    "score": p.score,
                    "payload": p.payload or {},
                }
                for p in points_res.points
            ]
        except Exception as e:
            logger.error(f"Qdrant query_points failed: {e}")
            return []

        if not raw_candidates:
            return []

        # 4. Enforce SEC-2: Second-lock access verification against Neon
        verified_candidates = verify_neon_second_lock(raw_candidates, user=user, db=self.db)
        if not verified_candidates:
            return []

        # 5. Rerank top candidates using Jina Reranker
        final_results = self.reranker.rerank(query, verified_candidates, top_k=limit)
        return final_results


class EnterpriseACLRetriever(BaseRetriever):
    """LangChain BaseRetriever conforming component for Enterprise RAG.

    Enforces department-and-role ACLs at both Qdrant and PostgreSQL layers.
    """

    user: Any = Field(description="The authenticated user object")
    db: Any = Field(description="SQLAlchemy DB session")
    search_service: Any = Field(default=None, description="Internal search service")
    top_k: int = Field(default=5, description="Number of documents to return")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, user: User, db: Session, top_k: int = 5, **kwargs):
        service = HybridSearchService(db=db)
        super().__init__(user=user, db=db, search_service=service, top_k=top_k, **kwargs)

    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[LCDocument]:
        results = self.search_service.search(query=query, user=self.user, limit=self.top_k)
        documents: List[LCDocument] = []
        for r in results:
            payload = r.get("payload", {})
            metadata = {
                "chunk_id": payload.get("chunk_id"),
                "document_id": payload.get("document_id"),
                "doc_title": payload.get("doc_title"),
                "department_id": payload.get("department_id"),
                "visibility": payload.get("visibility"),
                "min_role_level": payload.get("min_role_level"),
                "section": payload.get("section"),
                "page_start": payload.get("page_start"),
                "page_end": payload.get("page_end"),
                "score": r.get("score"),
                "rerank_score": r.get("rerank_score"),
            }
            documents.append(LCDocument(page_content=payload.get("text", ""), metadata=metadata))
        return documents
