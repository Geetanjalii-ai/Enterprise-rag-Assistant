from dataclasses import dataclass
from typing import Any, Dict, List

from langchain_core.output_parsers import StrOutputParser
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import User
from app.generation.citations import extract_citations
from app.generation.prompts import get_rag_prompt_template
from app.providers.llm import get_chat_model
from app.retrieval.context_builder import ContextBuilder, ContextSource
from app.retrieval.hybrid_search import HybridSearchService
from app.services.audit import log_rag_query


@dataclass
class RAGAnswer:
    answer: str
    citations: List[Dict[str, Any]]
    sources: List[ContextSource]
    outcome: str
    model_used: str


class AnswerService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.search_service = HybridSearchService(db=db)
        self.context_builder = ContextBuilder()
        self.prompt_template = get_rag_prompt_template()

    def generate_answer(
        self,
        question: str,
        user: User,
        top_k: int = 5,
    ) -> RAGAnswer:
        """Execute end-to-end role-aware RAG pipeline:

        1. Role-aware hybrid search with Qdrant + Neon second lock.
        2. Format context and citations within token budget.
        3. LLM answer generation with LangChain ChatGroq (primary + fallback).
        4. Citation extraction and audit logging.
        """
        # 1. Retrieve candidates
        retrieved_items = self.search_service.search(query=question, user=user, limit=top_k)

        # 2. If no authorized documents found, abstain immediately without calling LLM
        if not retrieved_items:
            abstain_msg = "I do not have access to that information in the company documents available to your role."
            log_rag_query(
                db=self.db,
                user_id=user.id,  # type: ignore[arg-type]
                question=question,
                chunk_ids=[],
                outcome="no_authorized_context",
            )
            return RAGAnswer(
                answer=abstain_msg,
                citations=[],
                sources=[],
                outcome="no_authorized_context",
                model_used="none",
            )

        # 3. Build numbered context
        context_str, sources = self.context_builder.build_context(retrieved_items)
        chunk_ids = [s.chunk_id for s in sources]

        # 4. Invoke LLM with primary model, fallback if rate-limited or unavailable
        response_text = ""
        model_used = self.settings.GROQ_MODEL

        user_name = getattr(user, "full_name", "") or getattr(user, "email", "Employee")
        user_email = getattr(user, "email", "employee@company.com")
        memberships = getattr(user, "memberships", []) or []
        user_dept = memberships[0].department.name if memberships and getattr(memberships[0], "department", None) else "General"
        max_role_level = max([getattr(m, "role_level", 1) for m in memberships], default=1)
        user_role = (
            "Department Head"
            if max_role_level >= 3
            else ("Manager" if max_role_level == 2 else "Member")
        )
        is_admin_str = "Yes (System Administrator)" if getattr(user, "is_admin", False) else "No"

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
            primary_llm = get_chat_model(temperature=0.0, model_name=self.settings.GROQ_MODEL)
            lcel_chain = self.prompt_template | primary_llm | StrOutputParser()
            response_text = lcel_chain.invoke(prompt_inputs)
        except Exception as e:
            logger.warning(
                f"Primary model {self.settings.GROQ_MODEL} failed, invoking fallback {self.settings.GROQ_FALLBACK_MODEL}: {e}"
            )
            try:
                fallback_llm = get_chat_model(temperature=0.0, model_name=self.settings.GROQ_FALLBACK_MODEL)
                fallback_chain = self.prompt_template | fallback_llm | StrOutputParser()
                response_text = fallback_chain.invoke(prompt_inputs)
                model_used = self.settings.GROQ_FALLBACK_MODEL
            except Exception as fe:
                logger.error(f"Fallback model also failed: {fe}")
                raise RuntimeError(f"Both primary and fallback LLM failed: {fe}") from fe

        # 5. Extract citations and determine outcome
        is_abstain = any(
            phrase in response_text.lower()
            for phrase in ["not have access", "cannot display", "confidential and restricted", "no access", "restricted to authorized"]
        )
        if is_abstain:
            outcome = "abstention"
            citations = []
            standard_msg = "I do not have access to that information in the company documents available to your role."
            if standard_msg not in response_text:
                response_text = f"{standard_msg}\n\n{response_text}"
        else:
            citations = extract_citations(response_text, sources)
            outcome = "answered" if citations else "not_found"

        # 6. SEC-8: Append-only audit logging
        log_rag_query(
            db=self.db,
            user_id=user.id,  # type: ignore[arg-type]
            question=question,
            chunk_ids=chunk_ids,
            outcome=outcome,
        )

        return RAGAnswer(
            answer=response_text.strip(),
            citations=citations,
            sources=sources,
            outcome=outcome,
            model_used=model_used,
        )
