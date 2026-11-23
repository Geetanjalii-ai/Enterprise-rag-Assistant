import boto3
import httpx
import typer
from qdrant_client import QdrantClient
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Department, Membership, User
from app.db.session import SessionLocal, engine
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

    # 5. Groq LLM API
    try:
        if settings.GROQ_API_KEY:
            res = httpx.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                timeout=5,
            )
            if res.status_code == 200:
                results.append((f"Groq API ({settings.GROQ_MODEL})", "Connected & Authorized", "green"))
            else:
                results.append(("Groq API", f"Status {res.status_code}: {res.text[:100]}", "red"))
        else:
            results.append(("Groq API", "Missing GROQ_API_KEY", "yellow"))
    except Exception as e:
        results.append(("Groq API", f"Failed: {e}", "red"))

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


if __name__ == "__main__":
    app()
