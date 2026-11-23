import sys
from pathlib import Path

# Ensure 'src' is in sys.path so cli.py runs seamlessly whether invoked directly or as a module
src_dir = str(Path(__file__).resolve().parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import boto3
import httpx
import typer
from qdrant_client import QdrantClient
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Chunk, Department, Document, Membership, User
from app.db.session import SessionLocal, engine
from app.generation.answer_service import AnswerService
from app.ingestion.pipeline import IngestionPipeline
from app.providers.embeddings.jina import JinaEmbeddingProvider
from app.providers.sparse.fastembed_bm25 import FastEmbedBM25Provider
from app.providers.vectorstore.qdrant import QdrantVectorStore
from app.retrieval.hybrid_search import HybridSearchService
from app.services.qdrant_init import init_qdrant_collection

app = typer.Typer(help="Enterprise RAG CLI management tool")
console = Console()


@app.command()
def doctor():
    """Test connectivity to Neon, Qdrant, Backblaze B2, Jina and Groq."""
    settings = get_settings()
    results = []

    # 1. Neon Database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        results.append(("Neon Postgres", "Connected", "green"))
    except Exception as e:
        results.append(("Neon Postgres", f"Failed: {e}", "red"))

    # 2. Qdrant
    try:
        if settings.QDRANT_URL and settings.QDRANT_API_KEY:
            qc = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, timeout=5)
            qc.get_collections()
            results.append(("Qdrant Vector DB", "Connected", "green"))
        else:
            results.append(("Qdrant Vector DB", "Missing URL or API Key", "yellow"))
    except Exception as e:
        results.append(("Qdrant Vector DB", f"Failed: {e}", "red"))

    # 3. Backblaze B2 (or Local Storage)
    if settings.STORAGE_BACKEND == "b2":
        try:
            if settings.B2_KEY_ID and settings.B2_APPLICATION_KEY:
                # Clean up region name if endpoint string was passed as region (e.g. 's3.us-east-005' -> 'us-east-005')
                region = settings.B2_REGION or ""
                if region.startswith("s3."):
                    region = region.replace("s3.", "", 1)
                elif "s3." in region:
                    region = region.split("s3.")[-1]
                region = region.strip()

                s3_client = boto3.client(
                    "s3",
                    endpoint_url=settings.B2_ENDPOINT_URL,
                    aws_access_key_id=settings.B2_KEY_ID,
                    aws_secret_access_key=settings.B2_APPLICATION_KEY,
                    region_name=region or None,
                )
                s3_client.head_bucket(Bucket=settings.B2_BUCKET_NAME)
                results.append((f"Backblaze B2 ({settings.B2_BUCKET_NAME})", "Reachable", "green"))
            else:
                results.append(("Backblaze B2", "Missing B2 credentials", "yellow"))
        except Exception as e:
            results.append(("Backblaze B2", f"Failed: {e}", "red"))
    else:
        results.append(("Storage (Local)", f"Enabled: {settings.LOCAL_STORAGE_DIR}", "green"))

    # 4. Jina Embeddings API
    try:
        if settings.JINA_API_KEY:
            res = httpx.get(
                "https://api.jina.ai/v1/models",
                headers={"Authorization": f"Bearer {settings.JINA_API_KEY}"},
                timeout=5,
            )
            if res.status_code in [200, 404, 405]:  # API key check
                # Even if /models is not 200, make a minimal test embedding call
                test_embed = httpx.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={"Authorization": f"Bearer {settings.JINA_API_KEY}"},
                    json={"model": settings.EMBEDDING_MODEL, "input": ["health check"]},
                    timeout=10,
                )
                if test_embed.status_code == 200:
                    results.append((f"Jina API ({settings.EMBEDDING_MODEL})", "Connected & Embeddings OK", "green"))
                else:
                    results.append(("Jina API", f"Status {test_embed.status_code}: {test_embed.text[:100]}", "yellow"))
            else:
                results.append(("Jina API", f"Unauthorized or unreachable ({res.status_code})", "red"))
        else:
            results.append(("Jina API", "Missing JINA_API_KEY", "yellow"))
    except Exception as e:
        results.append(("Jina API", f"Failed: {e}", "red"))

    # 5. Groq LLM API (LangChain ChatGroq)
    try:
        if settings.GROQ_API_KEY:
            from app.providers.llm import get_chat_model

            chat_model = get_chat_model()
            _ = chat_model.invoke("ping")
            results.append((f"LangChain ChatGroq ({settings.GROQ_MODEL})", "Connected & Operational", "green"))
        else:
            results.append(("LangChain ChatGroq", "Missing GROQ_API_KEY", "yellow"))
    except Exception as e:
        results.append(("LangChain ChatGroq", f"Failed: {e}", "red"))

    table = Table(title="Enterprise RAG System Connectivity (Doctor)")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")

    all_ok = True
    for service, status, color in results:
        table.add_row(service, f"[{color}]{status}[/{color}]")
        if color == "red":
            all_ok = False

    console.print(table)
    if not all_ok:
        raise typer.Exit(code=1)


@app.command()
def init_qdrant():
    """Create the Qdrant collection and payload indexes."""
    success = init_qdrant_collection()
    if success:
        console.print("[green]Qdrant collection and payload indexes initialized successfully.[/green]")
    else:
        console.print("[red]Failed to initialize Qdrant collection.[/red]")
        raise typer.Exit(code=1)


@app.command()
def seed():
    """Seed initial departments, admin, and test users with roles."""
    db = SessionLocal()
    try:
        # 1. Departments
        dept_data = [
            ("HR", "Human Resources"),
            ("Finance", "Finance and Accounting"),
            ("IT", "Information Technology"),
            ("Engineering", "Engineering"),
            ("Sales", "Sales and Marketing"),
        ]
        dept_map = {}
        for code, name in dept_data:
            dept = db.query(Department).filter(Department.code == code).first()
            if not dept:
                dept = Department(code=code, name=name)
                db.add(dept)
                db.flush()
                console.print(f"Created department: [cyan]{code}[/cyan]")
            dept_map[code] = dept

        # 2. Users and Roles
        # Roles: 1: member, 2: manager, 3: head
        users_to_seed = [
            ("admin@company.com", "System Admin", "Admin@12345", True, [("IT", 3)]),
            ("hr_head@company.com", "HR Head", "Password@123", False, [("HR", 3)]),
            ("hr_member@company.com", "HR Member", "Password@123", False, [("HR", 1)]),
            ("finance_mgr@company.com", "Finance Manager", "Password@123", False, [("Finance", 2)]),
            ("finance_member@company.com", "Finance Member", "Password@123", False, [("Finance", 1)]),
            ("it_member@company.com", "IT Member", "Password@123", False, [("IT", 1)]),
            ("employee@company.com", "Standard Employee", "Password@123", False, [("Engineering", 1)]),
        ]

        for email, full_name, password, is_admin, memberships in users_to_seed:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    is_admin=is_admin,
                    is_active=True,
                )
                db.add(user)
                db.flush()
                console.print(f"Created user: [bold]{email}[/bold] (is_admin={is_admin})")

            # Add memberships
            for dept_code, role_level in memberships:
                dept = dept_map.get(dept_code)
                if dept:
                    mem = (
                        db.query(Membership)
                        .filter(Membership.user_id == user.id, Membership.department_id == dept.id)
                        .first()
                    )
                    if not mem:
                        mem = Membership(user_id=user.id, department_id=dept.id, role_level=role_level)
                        db.add(mem)
                        console.print(f"  -> Assigned to {dept_code} (Role Level: {role_level})")

        db.commit()
        console.print("[green]Database seeding completed successfully![/green]")
    except Exception as e:
        db.rollback()
        console.print(f"[red]Error during database seeding: {e}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command()
def ingest(folder: str = typer.Option("../data/sample_docs", help="Path to documents folder with manifest.yaml")):
    """Run document ingestion pipeline over folder."""
    db = SessionLocal()
    try:
        target_path = Path(folder).resolve()
        if not target_path.exists():
            console.print(f"[red]Folder not found: {target_path}[/red]")
            raise typer.Exit(code=1)

        console.print(f"[cyan]Starting ingestion for folder: {target_path}[/cyan]")
        pipeline = IngestionPipeline(db)
        job = pipeline.run_folder_ingestion(target_path)

        table = Table(title="Ingestion Job Report")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="bold")

        for k, v in (job.summary or {}).items():
            table.add_row(k.capitalize(), str(v))

        console.print(table)
        console.print(f"[green]Ingestion job {job.id} completed with status: {job.status}[/green]")
    finally:
        db.close()


@app.command()
def reindex():
    """Rebuild Qdrant collection from Neon chunks (re-embedding all text)."""
    db = SessionLocal()
    try:
        console.print("[cyan]Re-indexing all active chunks from Neon to Qdrant...[/cyan]")
        # 1. Reset collection
        init_qdrant_collection()

        vector_store = QdrantVectorStore()
        embedder = JinaEmbeddingProvider()
        sparser = FastEmbedBM25Provider()

        chunks = (
            db.query(Chunk).join(Document, Chunk.document_id == Document.id).filter(Document.status == "active").all()
        )

        if not chunks:
            console.print("[yellow]No active chunks found in database to re-index.[/yellow]")
            return

        console.print(f"Found [bold]{len(chunks)}[/bold] active chunks. Computing embeddings...")

        chunk_texts = [c.text for c in chunks]
        # pyrefly: ignore[bad-argument-type]
        dense_vectors = embedder.embed_documents(chunk_texts)
        # pyrefly: ignore[bad-argument-type]
        sparse_vectors = sparser.embed_documents(chunk_texts)

        qdrant_points = []
        for i, c in enumerate(chunks):
            doc = c.document
            eff_ts = int(doc.effective_date.timestamp()) if doc.effective_date else 0
            exp_ts = int(doc.expiration_date.timestamp()) if doc.expiration_date else 253402300799

            qdrant_points.append(
                {
                    "id": c.qdrant_point_id,
                    "dense": dense_vectors[i],
                    "sparse": sparse_vectors[i],
                    "payload": {
                        "chunk_id": str(c.id),
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

        vector_store.upsert_points(qdrant_points)
        console.print("[green]Re-index completed successfully![/green]")
    finally:
        db.close()


@app.command()
def reconcile():
    """Compare chunks stored in Neon vs points indexed in Qdrant."""
    db = SessionLocal()
    try:
        console.print("[cyan]Checking synchronization between Neon and Qdrant...[/cyan]")
        vector_store = QdrantVectorStore()
        qdrant_point_ids = set(vector_store.get_indexed_point_ids())

        neon_chunks = (
            db.query(Chunk).join(Document, Chunk.document_id == Document.id).filter(Document.status == "active").all()
        )
        neon_chunk_point_ids = {c.qdrant_point_id for c in neon_chunks if c.qdrant_point_id}

        in_neon_not_qdrant = neon_chunk_point_ids - qdrant_point_ids
        in_qdrant_not_neon = qdrant_point_ids - neon_chunk_point_ids

        table = Table(title="Store Reconciliation Report")
        table.add_column("Store", style="cyan")
        table.add_column("Count", style="bold")
        table.add_column("Status")

        table.add_row("Neon Active Chunks", str(len(neon_chunk_point_ids)), "Source of Truth")
        table.add_row("Qdrant Indexed Points", str(len(qdrant_point_ids)), "Search Index")
        table.add_row(
            "Neon Chunks Missing in Qdrant",
            str(len(in_neon_not_qdrant)),
            "[green]None[/green]" if not in_neon_not_qdrant else "[red]Drift detected[/red]",
        )
        table.add_row(
            "Qdrant Points Missing in Neon",
            str(len(in_qdrant_not_neon)),
            "[green]None[/green]" if not in_qdrant_not_neon else "[red]Orphan points[/red]",
        )

        console.print(table)
        if in_neon_not_qdrant or in_qdrant_not_neon:
            console.print("[yellow]Drift detected. Run 'python -m app.cli reindex' to synchronize.[/yellow]")
        else:
            console.print("[green]Stores are perfectly synchronized![/green]")
    finally:
        db.close()


@app.command()
def search(
    query: str,
    as_user: str = typer.Option("employee@company.com", "--as", help="Email of the user to search as"),
    limit: int = typer.Option(5, "--limit", "-k", help="Maximum chunks to retrieve"),
):
    """Run role-aware hybrid retrieval with department ACL filters and second-lock validation."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == as_user).first()
        if not user:
            console.print(f"[red]User '{as_user}' not found in database. Run 'python -m app.cli seed' first.[/red]")
            raise typer.Exit(code=1)

        memberships_desc = ", ".join([f"{m.department.code}:L{m.role_level}" for m in user.memberships]) or "None"
        console.print(f"[cyan]Searching as:[/cyan] [bold]{user.email}[/bold] (Admin: {user.is_admin}, Roles: [{memberships_desc}])")
        console.print(f"[cyan]Query:[/cyan] \"{query}\"")

        service = HybridSearchService(db=db)
        results = service.search(query=query, user=user, limit=limit)

        if not results:
            console.print("[yellow]No authorized documents found matching your query.[/yellow]")
            return

        table = Table(title=f"Retrieved Chunks for {user.email}")
        table.add_column("#", style="dim", width=4)
        table.add_column("Document", style="cyan", max_width=30)
        table.add_column("Section", style="green", max_width=25)
        table.add_column("Page", style="magenta", width=8)
        table.add_column("Score", style="yellow", width=8)
        table.add_column("Preview", style="white", max_width=50)

        for i, item in enumerate(results, 1):
            payload = item.get("payload", {})
            score = item.get("rerank_score", item.get("score", 0.0))
            text = payload.get("text", "").replace("\n", " ")[:100] + "..."
            p_start = payload.get("page_start", "")
            p_end = payload.get("page_end", "")
            page_str = f"{p_start}" if p_start == p_end or not p_end else f"{p_start}-{p_end}"

            table.add_row(
                str(i),
                payload.get("doc_title", "Untitled"),
                payload.get("section", "-") or "-",
                page_str or "-",
                f"{score:.4f}" if isinstance(score, float) else str(score),
                text,
            )

        console.print(table)
    finally:
        db.close()


@app.command()
def ask(
    query: str,
    as_user: str = typer.Option("employee@company.com", "--as", help="Email of the user asking the question"),
    limit: int = typer.Option(5, "--limit", "-k", help="Maximum context chunks to retrieve"),
):
    """Generate a role-aware grounded RAG answer with citations and audit logging."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == as_user).first()
        if not user:
            console.print(f"[red]User '{as_user}' not found in database. Run 'python -m app.cli seed' first.[/red]")
            raise typer.Exit(code=1)

        memberships_desc = ", ".join([f"{m.department.code}:L{m.role_level}" for m in user.memberships]) or "None"
        console.print(f"[cyan]Asking as:[/cyan] [bold]{user.email}[/bold] (Admin: {user.is_admin}, Roles: [{memberships_desc}])")
        console.print(f"[cyan]Question:[/cyan] \"{query}\"\n")

        answer_service = AnswerService(db=db)
        rag_answer = answer_service.generate_answer(question=query, user=user, top_k=limit)

        console.print(f"[bold green]Answer ({rag_answer.model_used}):[/bold green]")
        console.print(f"{rag_answer.answer}\n")

        if rag_answer.citations:
            table = Table(title="Citations")
            table.add_column("Ref", style="bold cyan", width=6)
            table.add_column("Document", style="white")
            table.add_column("Section", style="green")
            table.add_column("Page", style="magenta")

            for c in rag_answer.citations:
                p_start = c.get("page_start")
                p_end = c.get("page_end")
                page_str = f"{p_start}" if p_start == p_end or not p_end else f"{p_start}-{p_end}"
                table.add_row(
                    f"[{c.get('citation_number')}]",
                    c.get("document_title", "-"),
                    c.get("section", "-") or "-",
                    page_str or "-",
                )
            console.print(table)
        else:
            console.print(f"[dim]Outcome: {rag_answer.outcome}[/dim]")

    finally:
        db.close()


if __name__ == "__main__":
    app()
