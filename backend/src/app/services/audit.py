from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import AuditLog


def log_rag_query(
    db: Session,
    user_id: UUID,
    question: str,
    chunk_ids: List[str],
    outcome: str,
    action: str = "rag_ask",
) -> None:
    """Enforces SEC-8: Append-only audit logging for all RAG questions and admin

    actions.
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            question=question,
            chunk_ids=chunk_ids,
            outcome=outcome,
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record audit log: {e}", extra={"user_id": str(user_id), "question": question})
