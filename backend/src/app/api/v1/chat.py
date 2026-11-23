from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import Chunk, Conversation, Document, Feedback, Message, User
from app.providers.storage import get_storage_provider
from app.retrieval.access_check import verify_neon_second_lock
from app.services.chat import stream_chat_rag

router = APIRouter(tags=["chat"])


# Request / Response Schemas
class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class RenameConversationRequest(BaseModel):
    title: str


class ConversationItem(BaseModel):
    id: str
    title: str
    created_at: datetime


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    messages: List[MessageItem]


class SendMessageRequest(BaseModel):
    content: str


class FeedbackRequest(BaseModel):
    rating: str  # "up" or "down"
    comment: Optional[str] = None


class CitationDetail(BaseModel):
    chunk_id: str
    document_title: str
    department: str
    version: str
    effective_date: Optional[str] = None
    section: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    text: str


# 1. Conversations CRUD
@router.get("/conversations", response_model=List[ConversationItem])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return [
        ConversationItem(
            id=str(c.id),
            title=c.title,
            created_at=c.created_at,
        )
        for c in convs
    ]


@router.post("/conversations", response_model=ConversationItem)
def create_conversation(
    body: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = body.title.strip() if body.title else "New Conversation"
    conv = Conversation(
        user_id=current_user.id,
        title=title,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationItem(
        id=str(conv.id),
        title=conv.title,
        created_at=conv.created_at,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return ConversationDetail(
        id=str(conv.id),
        title=conv.title,
        created_at=conv.created_at,
        messages=[
            MessageItem(
                id=str(m.id),
                role=m.role,
                content=m.content,
                citations=m.citations,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationItem)
def rename_conversation(
    conversation_id: UUID,
    body: RenameConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv.title = body.title.strip() or "Untitled Conversation"  # type: ignore[assignment]
    db.commit()
    return ConversationItem(id=str(conv.id), title=conv.title, created_at=conv.created_at)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully"}


# 2. Streaming Chat Message
@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream answer via Server-Sent Events (SSE).

    Client must read with fetch and ReadableStream.
    """
    question = body.content.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty")

    return StreamingResponse(
        stream_chat_rag(
            db=db,
            user=current_user,
            conversation_id=conversation_id,
            question=question,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 3. Message Feedback
@router.post("/messages/{message_id}/feedback")
def submit_feedback(
    message_id: UUID,
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    numeric_rating = 1 if body.rating.lower() == "up" else -1
    fb = Feedback(
        message_id=message_id,
        user_id=current_user.id,
        rating=numeric_rating,
        comment=body.comment,
    )
    db.add(fb)
    db.commit()
    return {"message": "Feedback submitted successfully"}


# 4. Source Citation Inspection
@router.get("/citations/{chunk_id}", response_model=CitationDetail)
def get_citation(
    chunk_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns chunk details for the source panel, re-verifying access (SEC-2)."""
    chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
    if not chunk or not chunk.document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citation not found")

    # Authoritative ACL verification
    simulated_item = {"payload": {"chunk_id": str(chunk.id)}}
    verified = verify_neon_second_lock([simulated_item], user=current_user, db=db)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to access this source document",
        )

    doc = chunk.document
    eff_str = doc.effective_date.isoformat() if doc.effective_date else None

    return CitationDetail(
        chunk_id=str(chunk.id),
        document_title=doc.title,
        department=doc.department.name,
        version=doc.version,
        effective_date=eff_str,
        section=chunk.section,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
    )


# 5. Document Download Link
@router.get("/documents/{document_id}/download-link")
def get_document_download_link(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a short-lived download link, only after authoritative access verification (SEC-6)."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or not doc.storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Verify ACL
    user_memberships = {m.department_id: m.role_level for m in current_user.memberships}
    max_role = max(user_memberships.values(), default=1)

    authorized = False
    if current_user.is_admin:
        authorized = True
    elif doc.visibility == "company" and doc.min_role_level <= max_role:
        authorized = True
    elif doc.visibility == "department":
        user_role = user_memberships.get(doc.department_id)
        if user_role is not None and doc.min_role_level <= user_role:
            authorized = True

    if not authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    storage = get_storage_provider()
    # Signed link expires in 300 seconds (5 minutes)
    download_url = storage.get_presigned_url(str(doc.storage_key), expires_in=300)
    return {"download_url": download_url, "expires_in": 300}
