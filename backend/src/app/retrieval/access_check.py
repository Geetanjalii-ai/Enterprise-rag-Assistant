from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import Chunk, Document, User


def verify_neon_second_lock(
    retrieved_items: List[Dict[str, Any]],
    user: User,
    db: Session,
    current_time: datetime | None = None,
) -> List[Dict[str, Any]]:
    """Enforces SEC-2 (Second-lock access check):

    Re-verifies every chunk retrieved from Qdrant against the authoritative Neon database.
    If any document was archived, expired, or the user's role changed between indexing and retrieval,
    the chunk is immediately dropped and logged as a security event.
    """
    if not retrieved_items:
        return []

    now = current_time or datetime.now(timezone.utc)

    # Pre-extract user memberships
    user_memberships = {m.department_id: m.role_level for m in user.memberships}
    max_user_role = max(user_memberships.values(), default=1)

    # Collect chunk IDs
    chunk_ids = [UUID(item["payload"]["chunk_id"]) for item in retrieved_items if "chunk_id" in item.get("payload", {})]
    if not chunk_ids:
        return []

    # Query Neon for authoritative chunk and document state
    db_chunks = (
        db.query(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Chunk.id.in_(chunk_ids))
        .all()
    )
    chunk_map = {c.id: c for c in db_chunks}

    verified_items: List[Dict[str, Any]] = []

    for item in retrieved_items:
        raw_chunk_id = item["payload"].get("chunk_id")
        if not raw_chunk_id:
            logger.warning("Dropping retrieved item missing chunk_id in payload", extra={"item": item})
            continue

        try:
            cid = UUID(raw_chunk_id)
        except ValueError:
            logger.warning(f"Dropping retrieved item with invalid UUID: {raw_chunk_id}")
            continue

        chunk = chunk_map.get(cid)
        if not chunk or not chunk.document:
            logger.warning(
                f"[SEC-2 VIOLATION] Chunk {cid} not found in Neon database. Dropping item.",
                extra={"user_id": str(user.id), "chunk_id": str(cid)},
            )
            continue

        doc = chunk.document

        # 1. Status check
        if doc.status != "active":
            logger.warning(
                f"[SEC-2 VIOLATION] Document {doc.id} status is '{doc.status}' (expected active). Dropping chunk {cid}.",
                extra={"user_id": str(user.id), "document_id": str(doc.id)},
            )
            continue

        # 2. Temporal validity check
        if doc.effective_date and doc.effective_date > now:
            logger.warning(
                f"[SEC-2 VIOLATION] Document {doc.id} not yet effective ({doc.effective_date}). Dropping chunk {cid}.",
                extra={"user_id": str(user.id), "document_id": str(doc.id)},
            )
            continue
        if doc.expiration_date and doc.expiration_date < now:
            logger.warning(
                f"[SEC-2 VIOLATION] Document {doc.id} expired ({doc.expiration_date}). Dropping chunk {cid}.",
                extra={"user_id": str(user.id), "document_id": str(doc.id)},
            )
            continue

        # 3. ACL permission check
        authorized = False
        if user.is_admin:
            authorized = True
        elif doc.visibility == "company":
            if doc.min_role_level <= max_user_role:
                authorized = True
        elif doc.visibility == "department":
            user_dept_role = user_memberships.get(doc.department_id)
            if user_dept_role is not None and doc.min_role_level <= user_dept_role:
                authorized = True

        if not authorized:
            logger.warning(
                f"[SEC-2 VIOLATION] User {user.email} unauthorized for doc {doc.id} ({doc.title}). Dropping chunk {cid}.",
                extra={
                    "user_id": str(user.id),
                    "document_id": str(doc.id),
                    "visibility": doc.visibility,
                    "min_role_level": doc.min_role_level,
                },
            )
            continue

        # Attach validated document title, department code, etc. to item
        item["document"] = {
            "id": str(doc.id),
            "title": doc.title,
            "visibility": doc.visibility,
            "min_role_level": doc.min_role_level,
            "department_id": str(doc.department_id),
            "storage_key": doc.storage_key,
        }
        verified_items.append(item)

    return verified_items
