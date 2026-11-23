import json
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import app_log, logger
from app.db.models import Conversation, Document, Message, User
from app.generation.citations import extract_citations
from app.generation.prompts import get_rag_prompt_template
from app.providers.llm import get_chat_model
from app.retrieval.context_builder import ContextBuilder
from app.retrieval.hybrid_search import HybridSearchService
from app.services.audit import log_rag_query
from app.services.guardrails import check_input_guardrail, check_output_guardrail
from app.services.monitoring import record_telemetry_event


def get_user_authorized_documents(db: Session, user: User) -> List[Document]:
    """Retrieve all active documents from Neon DB matching the user's role and departmental ACL."""
    user_memberships = {m.department_id: m.role_level for m in user.memberships}
    max_user_role = max(user_memberships.values(), default=1)

    docs = db.query(Document).filter(Document.status == "active").all()
    authorized: List[Document] = []
    now = datetime.now(timezone.utc)

    for d in docs:
        if d.effective_date and d.effective_date > now:
            continue
        if d.expiration_date and d.expiration_date < now:
            continue

        if user.is_admin:
            authorized.append(d)
        elif d.visibility == "company" and d.min_role_level <= max_user_role:
            authorized.append(d)
        elif d.visibility == "department":
            user_dept_role = user_memberships.get(d.department_id)
            if user_dept_role is not None and d.min_role_level <= user_dept_role:
                authorized.append(d)

    return authorized


async def stream_chat_rag(
    db: Session,
    user: User,
    conversation_id: UUID,
    question: str,
) -> AsyncGenerator[str, None]:
    """Execute end-to-end RAG with employee identity context and stream tokens via Server-Sent Events (SSE).

    Yields formatted SSE chunks:
    - event: token, data: {"token": "..."}
    - event: citations, data: {"citations": [...]}
    - event: done, data: {"message_id": "...", "outcome": "..."}
    - event: error, data: {"detail": "..."}
    """
    settings = get_settings()
    search_service = HybridSearchService(db=db)
    context_builder = ContextBuilder()
    prompt_template = get_rag_prompt_template()

    # Determine user identity context
    user_name = user.full_name or "Employee"
    user_email = user.email or ""
    user_dept = user.memberships[0].department.name if user.memberships else "General"
    max_role_level = max([m.role_level for m in user.memberships], default=1)
    user_role = (
        "Department Head"
        if max_role_level >= 3
        else ("Manager" if max_role_level == 2 else "Member")
    )
    is_admin_str = "Yes (System Administrator)" if user.is_admin else "No"

    # Verify conversation ownership
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if not conv:
        yield f"event: error\ndata: {json.dumps({'detail': 'Conversation not found'})}\n\n"
        return

    start_time = time.perf_counter()

    # Step-aware pipeline logging matching enterprise step format
    app_log("INFO", "chat.ingress", f"=== Question received from {user_email} ===")
    app_log("INFO", "chat.query", f"User question: {question}")

    # 1. Input Guardrail Evaluation (Prompt Injection & Jailbreak Prevention)
    guard_eval = check_input_guardrail(query=question, user_email=user_email)
    if not guard_eval.is_safe:
        block_msg = (
            f"Security Notice: Your inquiry was flagged and blocked by enterprise safety guardrails "
            f"({guard_eval.reason}). Please submit an authorized corporate question."
        )
        for token in block_msg.split(" "):
            yield f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"

        asst_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=block_msg,
            citations=[],
        )
        db.add(asst_msg)
        db.commit()

        log_rag_query(
            db=db,
            user_id=UUID(str(user.id)),
            question=question,
            chunk_ids=[],
            outcome="guardrail_blocked",
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        record_telemetry_event(
            user_id=str(user.id),
            user_email=user_email,
            department=user_dept,
            role=user_role,
            latency_ms=latency_ms,
            context_tokens=int(len(question.split()) * 1.3),
            completion_tokens=len(block_msg.split()),
            cost_usd=0.00001,
            outcome="guardrail_blocked",
        )
        app_log("INFO", "telemetry.metrics", f"Guardrail blocked event recorded ({latency_ms}ms)")

        yield f"event: citations\ndata: {json.dumps({'citations': []})}\n\n"
        yield f"event: done\ndata: {json.dumps({'message_id': str(asst_msg.id), 'outcome': 'guardrail_blocked'})}\n\n"
        return

    # 2. Save user question message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=question,
        citations=None,
    )
    db.add(user_msg)
    db.commit()

    is_identity_query = any(
        kw in question.lower()
        for kw in ["who am i", "my role", "my department", "what is my name", "what do i do", "who are you"]
    )

    is_policy_catalog_query = any(
        kw in question.lower()
        for kw in [
            "what policies",
            "which policies",
            "what documents",
            "which documents",
            "policies can i",
            "documents can i",
            "policies i can",
            "documents i can",
            "policies are available",
            "documents are available",
            "policies available",
            "documents available",
            "what can i view",
            "what can i access",
            "list policies",
            "show policies",
            "all policies",
            "available policies",
            "list documents",
            "show documents",
            "all documents",
            "available documents",
        ]
    )

    sources = []
    chunk_ids: List[str] = []

    if is_policy_catalog_query:
        auth_docs = get_user_authorized_documents(db, user)
        company_docs = sorted(set(d.title for d in auth_docs if d.visibility == "company"))
        dept_docs = sorted(set(f"{d.title} ({d.department.name})" for d in auth_docs if d.visibility == "department"))

        catalog_lines = [
            f"Official corporate policies and documentation authorized for {user_name} ({user_dept} Department - {user_role}):",
            "",
            "Company-wide Policies and Operational Guidelines:",
        ]
        for cd in company_docs:
            catalog_lines.append(f"- {cd}")

        if dept_docs:
            catalog_lines.append("")
            catalog_lines.append(f"{user_dept} Department Specific Policies and Procedures:")
            for dd in dept_docs:
                catalog_lines.append(f"- {dd}")

        if user.is_admin:
            catalog_lines.append("")
            catalog_lines.append("System Administrator Access: As a system administrator, you have full administrative oversight across all department files.")

        context_str = "\n".join(catalog_lines)
        app_log("INFO", "retrieval.acl_catalog", f"Loaded authoritative policy directory for {user_role}: {len(auth_docs)} documents")
    else:
        # Retrieve role-aware context (SEC-1 + SEC-2) with limit=8
        app_log("INFO", "retrieval.embeddings", f"Generating dense & sparse embeddings via '{settings.EMBEDDING_MODEL}'")
        retrieved_items = search_service.search(query=question, user=user, limit=8)
        app_log("INFO", "retrieval.hybrid_search", f"Retrieved {len(retrieved_items)} role-verified context chunks from Qdrant Cloud")

        # 3. Handle cases where no authorized documents exist
        if not retrieved_items and not is_identity_query:
            # Check if question is inquiring about unauthorized access
            lowered = question.lower()
            if any(term in lowered for term in ["salary", "compensation", "payroll", "executive"]):
                abstain_text = (
                    f"As a {user_role} in the {user_dept} department, company salary and executive compensation records "
                    f"are confidential and restricted to authorized personnel. I cannot display them."
                )
            else:
                abstain_text = (
                    f"I do not have access to that information in the company documents available to your role "
                    f"({user_dept} - {user_role})."
                )

            for token in abstain_text.split(" "):
                yield f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"

            # Save assistant message
            asst_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=abstain_text,
                citations=[],
            )
            db.add(asst_msg)
            db.commit()

            log_rag_query(
                db=db,
                user_id=UUID(str(user.id)),
                question=question,
                chunk_ids=[],
                outcome="no_authorized_context",
            )

            yield f"event: citations\ndata: {json.dumps({'citations': []})}\n\n"
            yield f"event: done\ndata: {json.dumps({'message_id': str(asst_msg.id), 'outcome': 'no_authorized_context'})}\n\n"
            return

        # 4. Build context
        if retrieved_items:
            context_str, sources = context_builder.build_context(retrieved_items)
            chunk_ids = [s.chunk_id for s in sources]
        else:
            context_str = "No specific company document excerpts required for this identity or greeting inquiry."
            sources = []
            chunk_ids = []

    # 5. Format prompt and stream from LLM
    full_answer_parts: List[str] = []
    model_to_use = settings.GROQ_MODEL
    app_log("INFO", "llm.stream_generator", f"Initializing LLM generation via '{model_to_use}' (LangSmith tracing enabled)")

    prompt_inputs = {
        "context": context_str,
        "question": question,
        "user_name": user_name,
        "user_email": user_email,
        "user_department": user_dept,
        "user_role": user_role,
        "is_admin": is_admin_str,
    }

    try:
        chat_model = get_chat_model(temperature=0.0, model_name=model_to_use)
        chain = prompt_template | chat_model

        async for chunk in chain.astream(prompt_inputs):
            content_piece = str(chunk.content)
            if content_piece:
                full_answer_parts.append(content_piece)
                yield f"event: token\ndata: {json.dumps({'token': content_piece})}\n\n"

    except Exception as e:
        logger.warning(f"Primary model streaming failed: {e}. Attempting fallback {settings.GROQ_FALLBACK_MODEL}")
        try:
            model_to_use = settings.GROQ_FALLBACK_MODEL
            fallback_model = get_chat_model(temperature=0.0, model_name=model_to_use)
            chain = prompt_template | fallback_model
            async for chunk in chain.astream(prompt_inputs):
                content_piece = str(chunk.content)
                if content_piece:
                    full_answer_parts.append(content_piece)
                    yield f"event: token\ndata: {json.dumps({'token': content_piece})}\n\n"
        except Exception as fe:
            logger.error(f"Fallback streaming model failed: {fe}")
            yield f"event: error\ndata: {json.dumps({'detail': 'Failed to generate answer'})}\n\n"
            return

    # 6. Extract structured citations
    final_text = "".join(full_answer_parts)
    citations = extract_citations(final_text, sources) if sources else []

    # Run Output Guardrail check
    check_output_guardrail(final_text)

    # Calculate telemetry metrics
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    prompt_tokens = int(len(context_str.split()) * 1.3 + len(question.split()) * 1.3 + 80)
    completion_tokens = int(len(final_text.split()) * 1.3)
    cost_usd = round((prompt_tokens * 0.0002 / 1000) + (completion_tokens * 0.0006 / 1000) + 0.00002, 6)

    app_log("INFO", "llm.completion", f"Final answer generated ({latency_ms}ms, {completion_tokens} tokens): {final_text[:50].strip()}...")
    app_log("INFO", "telemetry.metrics", f"Recorded telemetry: latency={latency_ms}ms, context={prompt_tokens} tokens, cost=${cost_usd:.6f}")

    record_telemetry_event(
        user_id=str(user.id),
        user_email=user_email,
        department=user_dept,
        role=user_role,
        latency_ms=latency_ms,
        context_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        outcome="answered",
    )

    # 7. Save assistant message with citations to Neon DB
    citations_data = [
        {
            "chunk_id": str(c.get("chunk_id", "")),
            "document_title": c.get("document_title", ""),
            "section": c.get("section"),
            "page_start": c.get("page_start"),
            "page_end": c.get("page_end"),
        }
        for c in citations
    ]
    asst_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=final_text,
        citations=citations_data,
    )
    db.add(asst_msg)
    db.commit()
    db.refresh(asst_msg)

    # 8. Log query in audit trail
    log_rag_query(
        db=db,
        user_id=UUID(str(user.id)),
        question=question,
        chunk_ids=chunk_ids,
        outcome="answered",
    )

    # 9. Yield citations event
    citations_payload = [
        {
            "chunk_id": str(c.get("chunk_id", "")),
            "document_title": c.get("document_title", ""),
            "section": c.get("section"),
            "page": c.get("page_start") or 1,
        }
        for c in citations
    ]
    yield f"event: citations\ndata: {json.dumps({'citations': citations_payload})}\n\n"

    # 10. Yield done event
    yield f"event: done\ndata: {json.dumps({'message_id': str(asst_msg.id), 'outcome': 'answered'})}\n\n"
