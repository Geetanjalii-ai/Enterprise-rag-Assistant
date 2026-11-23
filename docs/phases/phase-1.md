# Phase 1: Ingestion Pipeline

Branch: `phase-1-ingestion`  
Tag: `v0.2.0`  
Status: Completed & Verified

## Scope Completed
1. **Document Parsers & Cleaners (`backend/src/app/ingestion/parsers` & `cleaners.py`):**
   - **PDF:** Native extraction via PyMuPDF (`fitz`), preserving structural section boundaries, headings, and page metadata.
   - **DOCX:** Parsing paragraphs and structured tables via `python-docx`.
   - **Markdown:** Header-aware document parsing with frontmatter/metadata isolation.
   - **Plain Text:** Normalization of text files.
   - **Cleaners:** Normalized Unicode, whitespace collapsing, removal of unprintable/control characters, stripping of repeating page headers/footers and isolated page numbers.

2. **Chunking Engine (`backend/src/app/ingestion/chunkers.py`):**
   - `SectionChunker`: Structural heading-based chunker (~300–500 tokens target) using `tiktoken` (cl100k_base).
   - Preserves breadcrumb metadata (`headings` list, page number, character offsets).
   - Enforces 50-token contextual overlaps across section boundaries.

3. **Metadata, Versioning & Quarantine (`backend/src/app/ingestion/`):**
   - `metadata.py`: Validates `manifest.yaml` mapping filenames to security labels, department, version, min role levels, and validity timestamps.
   - `versioning.py`: Computes SHA-256 content hashes for change detection and version tracking.
   - `quarantine.py`: Implements **FR-ING-9** quarantine validation rules:
     - Missing mandatory metadata (owner, security classification, department).
     - Conflicting or duplicate active versions for the same department and title.
     - Unparseable or corrupt documents.

4. **Multi-Model Embeddings & Providers (`backend/src/app/providers`):**
   - **LangChain Ecosystem Integration:**
     - `langchain`, `langchain-core`, `langchain-community`, `langchain-text-splitters`, `langchain-groq`, `langchain-qdrant`.
     - `embeddings/base.py` & `jina.py`: Directly subclass `langchain_core.embeddings.Embeddings` for standard LangChain compatibility (1024-dim dense vectors, dynamic task typing).
     - `llm/groq.py`: Implements `ChatGroq` wrapper for generation, query rewriting, and LCEL chains.
     - `chunkers.py`: Native conversion to/from `langchain_core.documents.Document` with metadata preserving headings and page numbers.
   - `sparse/fastembed_bm25.py`: FastEmbed BM25 sparse lexical vector generation.
   - `vectorstore/qdrant.py`: Qdrant Cloud client handling dense + sparse vector upserts, document-level deletions, and point ID scroll streaming.
   - `storage/b2.py` & `storage/local.py`: Object storage for source documents in Backblaze B2 (with local fallback).

5. **Ingestion Pipeline Coordinator (`backend/src/app/ingestion/pipeline.py`):**
   - Full orchestration of document ingestion transactions in Neon PostgreSQL.
   - Idempotency: Unchanged documents (identical SHA-256 hash) are skipped automatically.
   - Change handling: Updating a document automatically archives prior versions and flushes obsolete vectors from Qdrant.
   - Detailed ingestion job auditing in `ingestion_jobs` and `ingestion_job_items`.

6. **CLI Commands (`backend/src/app/cli.py`):**
   - `python -m app.cli ingest --folder <path>`: Batch ingestion with rich summary report table.
   - `python -m app.cli reconcile`: Verifies 1:1 synchronization between PostgreSQL chunk records and Qdrant points.
   - `python -m app.cli reindex`: Full collection rebuild from PostgreSQL document chunks.

7. **Verification & Test Suite:**
   - Ingested all 28 corporate sample documents across HR, IT, Finance, Engineering, and Sales into Neon PostgreSQL (102 chunks) and Qdrant Cloud (102 points).
   - Verified idempotency: Subsequent run resulted in 28 skipped, 0 re-embedded.
   - Verified reconciliation: 102 active Neon chunks matched 102 Qdrant points with 0 missing.
   - Linting (`ruff check src tests`) passed with 0 errors.
   - Type-checking (`mypy src tests`) passed with 0 issues across 45 source files.
   - Unit tests (`pytest tests/unit/test_ingestion.py`) passed cleanly.

## Exit Criteria Checklist
- [x] Ingestion pipeline parses PDF, DOCX, MD, and TXT files cleanly.
- [x] Chunker produces structural chunks (~300–500 tokens) with heading breadcrumbs and page metadata.
- [x] Metadata loader validates `manifest.yaml` and enforces FR-ING-9 quarantine rules.
- [x] Jina dense (1024-dim) and FastEmbed BM25 sparse vectors generated and indexed into Qdrant.
- [x] SHA-256 hashing ensures idempotency on repeat runs (28/28 skipped).
- [x] CLI commands `ingest`, `reconcile`, and `reindex` implemented and verified.
- [x] `ruff`, `mypy`, and `pytest` pass cleanly with zero warnings or errors.
