import pytest
from sqlalchemy.orm import Session

from app.db.models import AuditLog, User
from app.db.session import SessionLocal
from app.generation.answer_service import AnswerService
from app.generation.citations import extract_citations
from app.retrieval.context_builder import ContextBuilder, ContextSource
from app.retrieval.hybrid_search import HybridSearchService


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_acl_salary_leak_protection(db_session: Session):
    """SEC-1 & SEC-12: Verify that confidential HR salary bands are retrievable

    by HR Head, but completely blocked (zero chunks leaked) for Engineering and Finance employees.
    """
    search_service = HybridSearchService(db=db_session)
    hr_head = db_session.query(User).filter(User.email == "hr_head@company.com").first()
    engineer = db_session.query(User).filter(User.email == "employee@company.com").first()
    finance_user = db_session.query(User).filter(User.email == "finance_member@company.com").first()

    assert hr_head is not None
    assert engineer is not None
    assert finance_user is not None

    query = "What are the annual salary bands for software engineers?"

    # 1. HR Head must retrieve the document
    hr_results = search_service.search(query=query, user=hr_head, limit=5)
    assert len(hr_results) > 0
    doc_titles = [r["payload"].get("doc_title") for r in hr_results]
    assert any("Salary" in t for t in doc_titles)

    # 2. Engineering employee must NOT retrieve the salary bands document (0 leaks)
    eng_results = search_service.search(query=query, user=engineer, limit=5)
    eng_titles = [r["payload"].get("doc_title") for r in eng_results]
    assert not any("Salary" in t for t in eng_titles)

    # 3. Finance member must NOT retrieve the salary bands document (0 leaks)
    fin_results = search_service.search(query=query, user=finance_user, limit=5)
    fin_titles = [r["payload"].get("doc_title") for r in fin_results]
    assert not any("Salary" in t for t in fin_titles)


def test_answer_service_abstention_on_unauthorized_query(db_session: Session):
    """Verify that AnswerService immediately abstains with the standardized message

    when a user attempts to ask about unauthorized departmental content.
    """
    answer_service = AnswerService(db=db_session)
    engineer = db_session.query(User).filter(User.email == "employee@company.com").first()
    assert engineer is not None

    query = "What are the exact salary bands for Level 4 Lead Engineers?"
    rag_answer = answer_service.generate_answer(question=query, user=engineer, top_k=5)

    assert rag_answer.outcome in ["abstention", "no_authorized_context"]
    assert "I do not have access to that information in the company documents available to your role." in rag_answer.answer
    assert len(rag_answer.citations) == 0

    # Verify audit log was written (SEC-8)
    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.user_id == engineer.id, AuditLog.question == query)
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.outcome in ["abstention", "no_authorized_context"]


def test_context_builder_budget_and_sources():
    cb = ContextBuilder(token_budget=100)
    items = [
        {
            "payload": {
                "chunk_id": "c1",
                "document_id": "d1",
                "doc_title": "Doc 1",
                "section": "Sec 1",
                "page_start": 1,
                "page_end": 1,
                "text": "Short text for chunk 1.",
            }
        },
        {
            "payload": {
                "chunk_id": "c2",
                "document_id": "d2",
                "doc_title": "Doc 2",
                "section": "Sec 2",
                "page_start": 2,
                "page_end": 3,
                "text": "Short text for chunk 2.",
            }
        },
    ]
    context_str, sources = cb.build_context(items)
    assert len(sources) == 2
    assert "[1] Document: \"Doc 1\"" in context_str
    assert "[2] Document: \"Doc 2\"" in context_str


def test_extract_citations():
    sources = [
        ContextSource(
            index=1,
            chunk_id="c1",
            doc_id="d1",
            doc_title="On-Call Handbook",
            section="5. Good practice",
            page_start=1,
            page_end=1,
            text="...",
        ),
        ContextSource(
            index=2,
            chunk_id="c2",
            doc_id="d2",
            doc_title="Code Review Guidelines",
            section="Turnaround",
            page_start=2,
            page_end=2,
            text="...",
        ),
    ]

    answer = "Engineers must acknowledge pages within 15 minutes [1]. Reviews should be done in 24 hours [2]."
    citations = extract_citations(answer, sources)
    assert len(citations) == 2
    assert citations[0]["citation_number"] == 1
    assert citations[0]["document_title"] == "On-Call Handbook"
    assert citations[1]["citation_number"] == 2
    assert citations[1]["document_title"] == "Code Review Guidelines"
