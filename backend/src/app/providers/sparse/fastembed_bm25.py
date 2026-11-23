from typing import List, Tuple

from fastembed import SparseTextEmbedding

from app.core.config import get_settings
from app.providers.sparse.base import SparseEmbeddingProvider


class FastEmbedBM25Provider(SparseEmbeddingProvider):
    _model = None

    def __init__(self, model_name: str = ""):
        settings = get_settings()
        self.model_name = model_name or settings.SPARSE_MODEL
        if FastEmbedBM25Provider._model is None:
            FastEmbedBM25Provider._model = SparseTextEmbedding(model_name=self.model_name)

    def embed_documents(self, texts: List[str]) -> List[Tuple[List[int], List[float]]]:
        if not texts:
            return []
        assert self._model is not None
        embeddings = list(self._model.embed(texts))
        return [(list(e.indices.tolist()), list(e.values.tolist())) for e in embeddings]

    def embed_query(self, text: str) -> Tuple[List[int], List[float]]:
        assert self._model is not None
        embedding = list(self._model.embed([text]))[0]
        return (list(embedding.indices.tolist()), list(embedding.values.tolist()))
