# Phase 2: Hybrid Retrieval & Multi-Department ACL Reranking

Branch: `phase-2-retrieval`  
Tag: `v0.3.0`  
Status: Completed & Verified

## Scope Completed

1. **Security & ACL Filter Engine (`app/retrieval/access_filter.py`):**
   - Implements **SEC-1**: Department-then-role filtering built inside Qdrant queries.
   - Evaluates user's administrative status, active department memberships, and role levels.
   - Automatically scopes searches to company-wide documents (`visibility == "company"`) and authorized departmental documents (`visibility == "department" AND min_role_level <= user_role`).
   - Enforces status (`status == "active"`) and temporal validity window (`effective_ts <= now <= expiry_ts`).

2. **Authoritative Second-Lock Verification (`app/retrieval/access_check.py`):**
   - Implements **SEC-2**: Every candidate chunk retrieved from Qdrant is cross-checked against Neon PostgreSQL before use.
   - Prevents stale vector index drift, expired document usage, or unauthorized access. Violations are automatically dropped and logged as security warnings.

3. **Hybrid Search & RRF Fusion (`app/retrieval/hybrid_search.py`):**
   - Dense query embedding using Jina Embeddings v3 (task `retrieval.query`).
   - Sparse lexical query embedding using FastEmbed BM25.
   - Server-side Reciprocal Rank Fusion (RRF) executed natively in Qdrant via `qmodels.FusionQuery(fusion=qmodels.Fusion.RRF)`.
   - Native LangChain integration via `EnterpriseACLRetriever` subclassing `langchain_core.retrievers.BaseRetriever`.

4. **Jina Reranker Integration (`app/providers/reranker/`):**
   - `JinaRerankerProvider`: Connects to Jina Reranker API (`jina-reranker-v2-base-multilingual`) to reorder hybrid candidates based on deep cross-encoder semantic relevance scores.
   - Includes automatic graceful fallback to hybrid RRF scores.

5. **Context Builder (`app/retrieval/context_builder.py`):**
   - Formats context chunks within the `LLM_CONTEXT_TOKEN_BUDGET` (3000 tokens) using `tiktoken`.
   - Adds structured breadcrumb headers (`[N] Document: "..." | Section: "..." | Page: ...`).

6. **Generation, Prompts & Citations (`app/generation/`):**
   - `prompts.py`: Role-aware enterprise system prompt enforcing strict grounding, mandatory `[N]` citations, and safe abstention (`"I do not have access to that information in the company documents available to your role."`).
   - `citations.py`: Regex extraction of `[N]` citation tokens mapped to document title, section, page numbers, and chunk IDs.
   - `answer_service.py`: End-to-end RAG answer orchestration with LangChain `ChatGroq` (`llama-3.3-70b-versatile` / `gpt-oss-20b`), retry and automatic fallback model (`llama-3.1-8b-instant`).

7. **Append-Only Audit Logging (`app/services/audit.py`):**
   - Implements **SEC-8**: Writes immutable audit log entries to Neon's `audit_log` table for all queries, user IDs, cited chunk IDs, and outcome (`answered`, `abstention`, or `no_authorized_context`).

8. **CLI Commands (`app/cli.py`):**
   - `python -m app.cli search "<query>" --as <email>`: Runs hybrid search + ACL filter + second lock and displays retrieved chunk table.
   - `python -m app.cli ask "<query>" --as <email>`: Generates complete role-aware RAG answer with citations and audit logging.

9. **Evaluation & Automated Leak Tests (`eval/` & `tests/integration/`):**
   - `eval/retrieval_test_set.json`: 30 evaluation questions spanning all departments, roles, and confidential documents.
   - `tests/integration/test_retrieval_acl.py`: Automated leak tests confirming **0 leaks** (SEC-12). Salary band queries return full data for `hr_head@company.com`, and safe abstention with 0 leaked chunks for `employee@company.com` and `finance_member@company.com`.
   - All 14 unit and integration tests passing in `pytest`.
   - `ruff check src tests` passed with 0 errors.
   - `mypy src tests` passed with 0 issues across 63 source files.

## Exit Criteria Checklist
- [x] Hybrid search in Qdrant with department-then-role filter (SEC-1).
- [x] Second-lock check against Neon drops unauthorized chunks (SEC-2).
- [x] Jina reranker re-scores hybrid candidates.
- [x] Context builder stays within 3000 token budget.
- [x] Answer service generates answers with citations using LangChain ChatGroq.
- [x] CLI commands `search` and `ask --as <email>` work cleanly.
- [x] Append-only audit logs recorded in Neon (SEC-8).
- [x] 30-question retrieval test set created (`eval/retrieval_test_set.json`).
- [x] Automated leak tests show **0 leaks** across department/role boundaries.
- [x] `ruff`, `mypy`, and `pytest` pass cleanly.
