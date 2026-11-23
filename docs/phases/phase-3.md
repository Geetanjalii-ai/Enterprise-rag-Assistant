# Phase 3: API, Login and Screens

Branch: `phase-3-api-screens`  
Tag: `v0.4.0`  
Status: Completed & Verified

## Overview
Phase 3 delivers the production-ready FastAPI backend endpoints and the complete React/Vite/TypeScript frontend user interface for **Meridian Assist**. It implements role-based access control, secure authentication with token rotation, real-time Server-Sent Events (SSE) streaming chat with citation panels, and an administrative console for document lifecycle and ingestion auditing.

---

## 1. Architecture & Security Foundations

### Backend Authentication & Authorization (`/api/v1/auth`)
- **Authoritative Neon PostgreSQL Role Resolution**: Every request evaluates user memberships, department assignments, role levels (member=1, manager=2, head=3), and system admin flag (`is_admin`) directly against Neon.
- **JWT & Rotating Refresh Cookie**:
  - `POST /auth/login`: Issues a short-lived in-memory JWT access token and sets an `httpOnly`, `SameSite=Strict` refresh cookie.
  - Refresh tokens are hashed using SHA-256 before storage in PostgreSQL and revoked/rotated upon every refresh (`POST /auth/refresh`).
  - `POST /auth/logout`: Revokes active refresh tokens.
  - `GET /me`: Returns authoritative current user identity, departments, and roles.
- **Slowapi Brute-Force Rate Limiting**:
  - Limits login attempts to 5 per 15 minutes per IP address.
  - Emits a generic error message (`"Incorrect email or password"`) preventing user enumeration.

### Chat & Streaming API (`/api/v1/conversations`, `/api/v1/messages`)
- **User Isolation**: A user only ever sees and accesses their own conversations.
- **SSE Streaming with Access Control (`POST /conversations/{id}/messages`)**:
  - Delivers chunk tokens via `event: token` and structured citations via `event: citations`.
  - Reuses Phase 2 retrieval and LangChain Groq generation pipelines unchanged without weakening ACL checks.
  - Dispatches `event: done` with message id for feedback tracking and `event: error` on failures.
- **Source Citation Excerpt Drawer (`GET /citations/{chunk_id}`)**:
  - Re-verifies tenant/department/role ACL permissions before returning document metadata, section name, page numbers, and chunk text.
- **Presigned Document Download (`GET /documents/{id}/download-link`)**:
  - Verifies read access, then generates a short-lived signed Backblaze B2 presigned download URL.

### Admin APIs (`/api/v1/admin`)
- Accessible strictly by users with `is_admin=True`.
- **Documents**: Filtered list, multipart file upload with validation (PDF, DOCX, MD, TXT allowlist; 20MB max), label modification, archive, and reingestion. Shows metadata only, never raw chunk text.
- **Ingestion Runs**: POST creates async run job; GET list & details with per-file status logs.
- **Quarantine**: Review flagged documents, correct metadata labels and release, or reject and discard.
- **Users**: List users, create user with auto-generated temporary password (returned once), modify roles and permissions.
- **Audit Log**: Paginated records (25/page) of queries, ACL denials, and administrative changes.

---

## 2. Frontend Implementation (`frontend/`)

### Design System & Theme Tokens (`src/styles/tokens.css`, `tailwind.config.js`)
- Strict token-driven design system following PRD Section 10:
  - Surface & Backgrounds: `--bg: #FAFAFA`, `--surface: #FFFFFF`, `--surface-muted: #F4F4F5`.
  - Borders & Inks: `--border: #E7E7EA`, `--border-strong: #D4D4D8`, `--ink: #0F1115`.
  - Pastels: Lavender (`#E9E4FA` / `#4B3FA0`), Sky (`#E0EEFB` / `#1E5A8C`), Mint (`#E0F3EA` / `#1F6B49`), Peach (`#FCEBDD` / `#8A4B1C`), Rose (`#FBE5E8` / `#A3283C`), Amber (`#FBF0D3` / `#85600A`).
  - Chat Greeting Glow: `radial-gradient(60% 50% at 50% 30%, #E9E4FA 0%, rgba(233,228,250,0) 70%)`.
- Typography: Inter font (`@fontsource-variable/inter`) loaded locally.

### Key Screens & Components
1. **Login Page (`/login`)**:
   - Split layout with left dark ambient panel (`#0C0C0E` with dual radial glows) and right sign-in form.
   - Show/hide password toggle, "Keep me signed in" checkbox, and IT helpdesk popover.
2. **Chat Page (`/chat`, `/chat/:conversationId`)**:
   - Left sidebar with conversation groups (Today, Previous 7 days, Older) with rename/delete controls.
   - User profile card with department/role badge and popup menu (Admin Console link + Sign out).
   - Empty state with greeting orb and 3 suggestion cards.
   - Streaming markdown message list with blinking caret and source citation chips.
   - Right-side `SourceDrawer` displaying excerpt text and "Open original document" link.
3. **Admin Console (`/admin/...`)**:
   - Documents table with search/department/status filters and Upload Drawer.
   - Ingestion Runs page with 4 StatCards and live polling.
   - Quarantine page with reason badges, label correction drawer, and reject dialog.
   - Users & Permissions page with Add User temporary password display.
   - Audit Log page with outcome filters and event inspector drawer.

---

## 3. Test & Verification Results

### Backend Verification:
- **Ruff**: `All checks passed!` (0 lint errors)
- **Mypy**: `Success: no issues found in 62 source files` (Strict type safety)
- **Pytest**: `21 passed in 58.03s`
  - Auth login, token rotation, and cookie security: PASSED
  - Chat conversation lifecycle and streaming SSE: PASSED
  - Admin ACL isolation and admin action endpoints: PASSED
  - Leak tests & salary protection assertions: PASSED

### Frontend Verification:
- **TypeScript Compiler (`tsc`)**: 0 errors
- **Vite Build**: `✓ built cleanly` (production bundle built cleanly)
- **Vitest Unit Tests**: `5 passed (2 test files)`
  - `streamChatMessage` SSE event parser (token, citations, done, error): PASSED
  - `LoginForm` rendering, authentication submission, and error handling: PASSED

---

## 4. Observability, Telemetry Analytics & AI Safety Guardrails

### Observability & Admin Monitoring Console (`/admin/monitoring`)
- **LangSmith Distributed Tracing**: Automated distributed tracing across all LLM queries, tool invocations, and retrieval chains via LangSmith API key and project `tracy-development`.
- **Model & Embeddings Observability**: Real-time telemetry cards for primary LLM (`qwen/qwen3.8-27b`), embeddings (`jina-embeddings-v3`), sparse index (`Qdrant/bm25`), and vector store (`Qdrant Cloud`).
- **Telemetry Performance Analytics & Charts**:
  - **Latency Trend (ms)**: Interactive time-series bar chart analyzing inference latency and TTFT.
  - **Context Window Usage**: Token volume tracking (context prompt tokens vs output completion tokens).
  - **Cost Burn Analytics ($ USD)**: Real-time cost estimation per query and aggregate spend.
  - **Per-User Usage Breakdown**: Table detailing User Email, Department, Role, Total Queries, Avg Latency, Context Tokens, and Total Cost ($).
  - **Range Selector**: Toggleable views for `Last 24h`, `Last 7 Days`, and `Last 30 Days`.
- **Step-Aware Log Streaming**:
  - Replaced ambiguous generic names with semantic, step-specific logger names:
    - `system.startup`, `vector_store.qdrant`, `embeddings.jina`, `llm.engine`, `guardrails.config`, `rag.agent`
    - `chat.ingress`, `chat.query`, `guardrails.input`, `retrieval.acl_catalog`, `retrieval.embeddings`, `retrieval.hybrid_search`, `llm.stream_generator`, `llm.completion`, `guardrails.output`, `telemetry.metrics`
  - Structured format: `TIMESTAMP | LEVEL | STEP_NAME | MESSAGE`
  - **Date & Time Range Filters**: Presets (`All Time`, `Past 1 Hour`, `Past 24 Hours`) and custom `From` / `To` datetime inputs.

### Dual-Layer AI Safety Guardrails
- **Input Guardrail**: Combines heuristic regex checks with `meta-llama/llama-prompt-guard-2-86m` to intercept prompt injections, jailbreak patterns, system prompt extraction, and role overrides.
- **Output Guardrail**: Evaluates LLM responses before client streaming to detect and suppress credential leaks (JWTs, API keys, passwords, database URLs).
- **Incident Logging**: Violations are blocked, recorded in the audit log with `outcome="guardrail_blocked"`, and displayed on the monitoring dashboard.
