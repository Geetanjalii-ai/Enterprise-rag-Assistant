from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.logging import logger


def init_qdrant_collection() -> bool:
    settings = get_settings()
    if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
        logger.error("Qdrant URL or API key not configured")
        return False

    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    collection_name = settings.QDRANT_COLLECTION

    collections = [col.name for col in client.get_collections().collections]
    if collection_name not in collections:
        logger.info(f"Creating Qdrant collection: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": qmodels.VectorParams(
                    size=settings.EMBEDDING_DIM,
                    distance=qmodels.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": qmodels.SparseVectorParams(index=qmodels.SparseIndexParams(on_disk=False))
            },
        )
    else:
        logger.info(f"Qdrant collection {collection_name} already exists")

    # Setup payload indexes according to PRD Section 7:
    # department_id, visibility, status, document_id, min_role_level, effective_ts, expiry_ts
    payload_indexes = [
        ("department_id", qmodels.PayloadSchemaType.KEYWORD),
        ("visibility", qmodels.PayloadSchemaType.KEYWORD),
        ("status", qmodels.PayloadSchemaType.KEYWORD),
        ("document_id", qmodels.PayloadSchemaType.KEYWORD),
        ("min_role_level", qmodels.PayloadSchemaType.INTEGER),
        ("effective_ts", qmodels.PayloadSchemaType.INTEGER),
        ("expiry_ts", qmodels.PayloadSchemaType.INTEGER),
    ]

    for field_name, schema_type in payload_indexes:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=schema_type,
            )
        except Exception as e:
            logger.debug(f"Payload index for {field_name} note: {e}")

    logger.info(f"Qdrant collection {collection_name} configured with payload indexes")
    return True
