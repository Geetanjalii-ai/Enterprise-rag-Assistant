import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import (
    Chunk,
    Department,
    Document,
    IngestionJob,
    IngestionJobItem,
)
from app.ingestion.chunkers import SectionChunker, TextChunk
from app.ingestion.cleaners import clean_text
from app.ingestion.loaders import load_documents_with_langchain
from app.ingestion.metadata import load_manifest
from app.ingestion.quarantine import evaluate_quarantine_rules
from app.ingestion.versioning import compute_file_hash
from app.providers.embeddings.jina import JinaEmbeddingProvider
from app.providers.sparse.fastembed_bm25 import FastEmbedBM25Provider
from app.providers.storage import get_storage_provider
from app.providers.vectorstore.qdrant import QdrantVectorStore


class IngestionPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.embedding_provider = JinaEmbeddingProvider()
        self.sparse_provider = FastEmbedBM25Provider()
        self.vector_store = QdrantVectorStore()
        self.storage = get_storage_provider()
        self.chunker = SectionChunker()

    def run_folder_ingestion(self, folder_path: Path) -> IngestionJob:
        manifest_path = folder_path / "manifest.yaml"
        manifest_map = load_manifest(manifest_path)

        job = IngestionJob(
            status="in_progress",
            started_at=datetime.now(timezone.utc),
            summary={"processed": 0, "skipped": 0, "failed": 0, "quarantined": 0},
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # Department cache
        departments = {d.code.upper(): d for d in self.db.query(Department).all()}

        # Check for duplicate active versions in manifest
        active_versions: Dict[str, str] = {}
        file_conflicts: set = set()
        for rel_key, item in manifest_map.items():
            key = item.doc_id or item.title
            if key in active_versions:
                file_conflicts.add(rel_key)
                file_conflicts.add(active_versions[key])
            else:
                active_versions[key] = rel_key

        supported_exts = [".pdf", ".docx", ".doc", ".md", ".txt"]
        all_files = [
            f
            for f in folder_path.rglob("*")
            if f.is_file() and f.suffix.lower() in supported_exts and f.name != "manifest.yaml"
        ]

        processed_count = 0
        skipped_count = 0
        quarantined_count = 0
        failed_count = 0

        for file_path in all_files:
            rel_path = file_path.relative_to(folder_path).as_posix()
            manifest_item = manifest_map.get(rel_path)
            is_duplicate = rel_path in file_conflicts

            is_quarantined, quarantine_reason = evaluate_quarantine_rules(manifest_item, duplicate_active=is_duplicate)

            # Record item in job
            job_item = IngestionJobItem(
                job_id=job.id,
                file_path=rel_path,
                result="pending",
                reason=None,
            )

            if is_quarantined or not manifest_item:
                job_item.result = "quarantined"  # type: ignore[assignment]
                job_item.reason = quarantine_reason  # type: ignore[assignment]
                self.db.add(job_item)
                self.db.commit()
                quarantined_count += 1
                logger.warn(f"Quarantined {rel_path}: {quarantine_reason}")
                continue

            try:
                # FR-ING-8: Content hash versioning
                file_hash = compute_file_hash(file_path)

                dept = departments.get(manifest_item.department.upper())
                if not dept:
                    dept = Department(
                        code=manifest_item.department.upper(),
                        name=manifest_item.department,
                    )
                    self.db.add(dept)
                    self.db.flush()
                    departments[manifest_item.department.upper()] = dept

                existing_doc = (
                    self.db.query(Document)
                    .filter(
                        Document.department_id == dept.id,
                        Document.title == manifest_item.title,
                        Document.version == manifest_item.version,
                    )
                    .first()
                )

                if existing_doc and existing_doc.content_hash == file_hash and existing_doc.status == "active":
                    # Unchanged file: skip
                    job_item.result = "skipped"  # type: ignore[assignment]
                    job_item.reason = "Content unchanged (hash match)"  # type: ignore[assignment]
                    self.db.add(job_item)
                    self.db.commit()
                    skipped_count += 1
                    continue

                # If existing doc changed, archive its old version and remove vectors from Qdrant
                if existing_doc:
                    existing_doc.status = "archived"  # type: ignore[assignment]
                    self.vector_store.delete_by_document_id(str(existing_doc.id))
                    self.db.flush()

                # Upload original file to B2 / storage
                storage_key = f"documents/{dept.code.lower()}/{file_hash[:16]}_{file_path.name}"
                with open(file_path, "rb") as f_obj:
                    self.storage.upload_file(f_obj, storage_key)

                # Load with LangChain document loader
                raw_docs = load_documents_with_langchain(file_path)
                for d in raw_docs:
                    d.page_content = clean_text(d.page_content)

                # Chunk document
                chunks: List[TextChunk] = self.chunker.chunk_langchain_documents(raw_docs)

                # Parse effective & expiration timestamps
                eff_dt = None
                exp_dt = None
                eff_ts = 0
                exp_ts = 253402300799  # Far future (year 9999)

                if manifest_item.effective_date:
                    try:
                        eff_dt = datetime.fromisoformat(manifest_item.effective_date).replace(tzinfo=timezone.utc)
                        eff_ts = int(eff_dt.timestamp())
                    except Exception:
                        pass

                if manifest_item.expiration_date:
                    try:
                        exp_dt = datetime.fromisoformat(manifest_item.expiration_date).replace(tzinfo=timezone.utc)
                        exp_ts = int(exp_dt.timestamp())
                    except Exception:
                        pass

                # Create Document in Neon
                new_doc = Document(
                    title=manifest_item.title,
                    department_id=dept.id,
                    visibility=manifest_item.visibility,
                    min_role_level=manifest_item.min_role_level,
                    doc_type=manifest_item.doc_type,
                    version=manifest_item.version,
                    effective_date=eff_dt,
                    expiration_date=exp_dt,
                    status="active",
                    storage_key=storage_key,
                    content_hash=file_hash,
                )
                self.db.add(new_doc)
                self.db.flush()

                # Generate Embeddings
                chunk_texts = [c.text for c in chunks]
                dense_vectors = self.embedding_provider.embed_documents(chunk_texts)
                sparse_vectors = self.sparse_provider.embed_documents(chunk_texts)

                # Prepare Neon Chunks and Qdrant Points
                qdrant_points = []
                for i, c in enumerate(chunks):
                    point_id = str(uuid.uuid4())
                    db_chunk = Chunk(
                        document_id=new_doc.id,
                        chunk_index=c.chunk_index,
                        text=c.text,
                        section=c.section,
                        page_start=c.page_start,
                        page_end=c.page_end,
                        token_count=c.token_count,
                        embedding_model=self.settings.EMBEDDING_MODEL,
                        embedding_dim=self.settings.EMBEDDING_DIM,
                        index_status="pending",
                        qdrant_point_id=point_id,
                    )
                    self.db.add(db_chunk)
                    self.db.flush()

                    qdrant_points.append(
                        {
                            "id": point_id,
                            "dense": dense_vectors[i],
                            "sparse": sparse_vectors[i],
                            "payload": {
                                "chunk_id": str(db_chunk.id),
                                "document_id": str(new_doc.id),
                                "department_id": str(dept.id),
                                "visibility": manifest_item.visibility,
                                "min_role_level": manifest_item.min_role_level,
                                "status": "active",
                                "effective_ts": eff_ts,
                                "expiry_ts": exp_ts,
                                "version": manifest_item.version,
                                "doc_title": manifest_item.title,
                                "section": c.section,
                                "page_start": c.page_start,
                                "page_end": c.page_end,
                                "text": c.text,
                            },
                        }
                    )

                # Upsert to Qdrant
                self.vector_store.upsert_points(qdrant_points)

                # Mark chunks as indexed
                self.db.query(Chunk).filter(Chunk.document_id == new_doc.id).update({"index_status": "indexed"})
                self.db.commit()

                job_item.result = "processed"  # type: ignore[assignment]
                self.db.add(job_item)
                self.db.commit()
                processed_count += 1
                logger.info(f"Successfully processed {rel_path} ({len(chunks)} chunks)")

            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to process {rel_path}: {e}")
                job_item.result = "failed"  # type: ignore[assignment]
                job_item.reason = str(e)  # type: ignore[assignment]
                self.db.add(job_item)
                self.db.commit()
                failed_count += 1

        job.finished_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        job.status = "completed"  # type: ignore[assignment]
        job.summary = {  # type: ignore[assignment]
            "processed": processed_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "quarantined": quarantined_count,
            "total_files": len(all_files),
        }
        self.db.commit()
        return job

    def ingest_document_file(self, doc: Document, file_path: Path) -> int:
        """
        Chunks, embeds, stores chunks in Neon DB, and upserts dense + sparse vectors to Qdrant.
        Also archives older active versions of the same title/dept to avoid stale retriever context.
        """
        import re

        def normalize_title(t: str) -> str:
            # Strip version pattern like v1.0, v2.0, _v2.0, -v2.0, (v2.0)
            cleaned = re.sub(r'[\s_\-\(\[]*v?\d+(\.\d+)?[\)\]]*$', '', t, flags=re.IGNORECASE)
            return re.sub(r'[_\-\s]+', ' ', cleaned).strip().lower()

        target_normalized = normalize_title(doc.title)

        # Archive older active versions of this document in the same department
        all_dept_docs = (
            self.db.query(Document)
            .filter(
                Document.department_id == doc.department_id,
                Document.id != doc.id,
                Document.status == "active",
            )
            .all()
        )
        for old_d in all_dept_docs:
            if old_d.title == doc.title or normalize_title(old_d.title) == target_normalized:
                old_d.status = "archived"  # type: ignore[assignment]
                try:
                    self.vector_store.delete_by_document_id(str(old_d.id))
                except Exception as e:
                    logger.warning(f"Failed to delete Qdrant vectors for auto-archived doc: {e}")
                self.db.query(Chunk).filter(Chunk.document_id == old_d.id).update({"index_status": "archived"})
                logger.info(f"Auto-archived prior version '{old_d.title}' (v{old_d.version}) in favour of new active version v{doc.version}")

        # Clear existing vectors and chunks for this document
        try:
            self.vector_store.delete_by_document_id(str(doc.id))
        except Exception:
            pass
        self.db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        self.db.flush()

        raw_docs = load_documents_with_langchain(file_path)
        for d in raw_docs:
            d.page_content = clean_text(d.page_content)

        chunks: List[TextChunk] = self.chunker.chunk_langchain_documents(raw_docs)
        if not chunks:
            logger.warn(f"Document {doc.title} produced 0 chunks after parsing")
            return 0

        eff_ts = int(doc.effective_date.timestamp()) if doc.effective_date else 0
        exp_ts = int(doc.expiration_date.timestamp()) if doc.expiration_date else 253402300799

        chunk_texts = [c.text for c in chunks]
        dense_vectors = self.embedding_provider.embed_documents(chunk_texts)
        sparse_vectors = self.sparse_provider.embed_documents(chunk_texts)

        qdrant_points = []
        for i, c in enumerate(chunks):
            point_id = str(uuid.uuid4())
            db_chunk = Chunk(
                document_id=doc.id,
                chunk_index=c.chunk_index,
                text=c.text,
                section=c.section,
                page_start=c.page_start,
                page_end=c.page_end,
                token_count=c.token_count,
                embedding_model=self.settings.EMBEDDING_MODEL,
                embedding_dim=self.settings.EMBEDDING_DIM,
                index_status="pending",
                qdrant_point_id=point_id,
            )
            self.db.add(db_chunk)
            self.db.flush()

            qdrant_points.append(
                {
                    "id": point_id,
                    "dense": dense_vectors[i],
                    "sparse": sparse_vectors[i],
                    "payload": {
                        "chunk_id": str(db_chunk.id),
                        "document_id": str(doc.id),
                        "department_id": str(doc.department_id),
                        "visibility": doc.visibility,
                        "min_role_level": doc.min_role_level,
                        "status": doc.status,
                        "effective_ts": eff_ts,
                        "expiry_ts": exp_ts,
                        "version": doc.version,
                        "doc_title": doc.title,
                        "section": c.section,
                        "page_start": c.page_start,
                        "page_end": c.page_end,
                        "text": c.text,
                    },
                }
            )

        self.vector_store.upsert_points(qdrant_points)
        self.db.query(Chunk).filter(Chunk.document_id == doc.id).update({"index_status": "indexed"})
        self.db.commit()
        logger.info(f"Successfully indexed document '{doc.title}' ({len(chunks)} chunks, vectors synced)")
        return len(chunks)

    def reingest_document(self, doc: Document) -> int:
        """Download file from storage, re-parse, and re-embed chunks into vector store."""
        if not doc.storage_key:
            raise ValueError(f"Document {doc.id} has no storage_key")

        file_bytes = self.storage.download_file(doc.storage_key)
        ext = Path(doc.storage_key).suffix or ".txt"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            return self.ingest_document_file(doc, tmp_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
