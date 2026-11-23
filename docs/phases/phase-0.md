# Phase 0: Foundations

Branch: `phase-0-foundations`  
Tag: `v0.1.0`  
Status: Completed & Verified

## Scope Completed
1. **Repository Layout & Config Files:**
   - `.gitignore` (safeguards secrets, virtual environments, build artifacts)
   - `.pre-commit-config.yaml` (Ruff and trailing-whitespace hooks)
   - Root `README.md` and `docs/phases/phase-0.md`
   - `backend/.env.example`
2. **Backend Architecture & Dependencies:**
   - Modular layout under `backend/src/app`
   - Virtual environment (`backend/.venv`) configured with all dependencies
   - Pydantic Settings loaded from environment (`app.core.config.Settings`)
   - Structured JSON/Console logging configured (`app.core.logging.setup_logging`)
   - Password hashing with Argon2 (`app.core.security`)
3. **Database & Migrations:**
   - Neon PostgreSQL connection pool via SQLAlchemy 2 (`app.db.session`)
   - Complete schema mapped across all 12 tables in `app.db.models`:
     - `users`, `departments`, `memberships`, `refresh_tokens`, `documents`, `chunks`, `ingestion_jobs`, `ingestion_job_items`, `conversations`, `messages`, `feedback`, `audit_log`
   - Alembic migration `001_initial` generated and successfully applied to Neon (`alembic upgrade head`)
4. **Qdrant Vector Store Setup:**
   - Qdrant Cloud collection `enterprise_docs` created with:
     - Dense vector configuration: `1024` dimensions (Cosine distance)
     - Sparse vector configuration: FastEmbed BM25
     - Payload keyword and integer indexes on: `department_id`, `visibility`, `status`, `document_id`, `min_role_level`, `effective_ts`, `expiry_ts`
5. **CLI & Diagnostics Tool (`app.cli`):**
   - `python -m app.cli doctor`: Confirms connectivity to Neon, Qdrant, Backblaze B2, Jina API, and Groq API.
   - `python -m app.cli init-qdrant`: Idempotent collection and payload index setup.
   - `python -m app.cli seed`: Seeds 5 standard departments (`HR`, `Finance`, `IT`, `Engineering`, `Sales`) and default test users across roles (`admin@company.com`, `hr_head@company.com`, `hr_member@company.com`, `finance_mgr@company.com`, `finance_member@company.com`, `it_member@company.com`, `employee@company.com`).
6. **Code Quality & Test Suite:**
   - `ruff format .` and `ruff check .` passed with 0 errors.
   - `mypy src tests` passed with 0 issues in 16 source files.
   - `pytest` passed (3 unit tests for settings, password hashing, and metadata).

## Exit Criteria Checklist
- [x] `python -m app.cli doctor` reports Neon, Qdrant, B2, Jina, and Groq as reachable.
- [x] `alembic upgrade head` applies cleanly.
- [x] `python -m app.cli seed` creates departments and sample users.
- [x] No secrets appear in tracked files (`.env` is excluded by `.gitignore`).
- [x] Linting (`ruff`), type-checking (`mypy`), and unit tests (`pytest`) pass cleanly.
