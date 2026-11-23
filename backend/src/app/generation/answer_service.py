from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import UUID

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
                user_id=UUID(str(user.id)),
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

        try:
            primary_llm = get_chat_model(temperature=0.0, model_name=self.settings.GROQ_MODEL)
            lcel_chain = self.prompt_template | primary_llm | StrOutputParser()
            response_text = lcel_chain.invoke({"context": context_str, "question": question})
        except Exception as e:
            logger.warning(
                f"Primary model {self.settings.GROQ_MODEL} failed, invoking fallback {self.settings.GROQ_FALLBACK_MODEL}: {e}"
            )
            try:
                fallback_llm = get_chat_model(temperature=0.0, model_name=self.settings.GROQ_FALLBACK_MODEL)
                fallback_chain = self.prompt_template | fallback_llm | StrOutputParser()
                response_text = fallback_chain.invoke({"context": context_str, "question": question})
                model_used = self.settings.GROQ_FALLBACK_MODEL
            except Exception as fe:
                logger.error(f"Fallback model also failed: {fe}")
                raise RuntimeError(f"Both primary and fallback LLM failed: {fe}") from fe

        # 5. Extract citations
        citations = extract_citations(response_text, sources)
        outcome = "answered" if citations or "I do not have access" not in response_text else "abstention"

        # 6. SEC-8: Append-only audit logging
        log_rag_query(
            db=self.db,
            user_id=UUID(str(user.id)),
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
