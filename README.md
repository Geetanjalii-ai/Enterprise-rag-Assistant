# Enterprise RAG Assistant

A role-aware enterprise assistant that answers employee questions from approved, current company documents, always cites its sources, says 'I could not find this' when unsure, and never exposes anything the asker is not allowed to see.

## Development Setup

### Prerequisites
- Python 3.11+
- Neon PostgreSQL database instance
- Qdrant Cloud cluster or instance
- Backblaze B2 bucket
- Groq and Jina API keys

### Phase 0 Setup

1. Copy `.env.example` to `backend/.env` (or root `.env` for development) and fill in the required credentials.
2. Navigate to `backend`:
   ```bash
   cd backend
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
3. Run Alembic migrations:
   ```bash
   alembic upgrade head
   ```
4. Run health check / diagnostics:
   ```bash
   python -m app.cli doctor
   ```
5. Seed initial departments and users:
   ```bash
   python -m app.cli seed
   ```
