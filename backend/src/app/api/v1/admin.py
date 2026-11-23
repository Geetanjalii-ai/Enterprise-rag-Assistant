import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import hash_password
from app.db.models import (
    AuditLog,
    Department,
    Document,
    IngestionJob,
    IngestionJobItem,
    Membership,
    User,
)
from app.ingestion.pipeline import IngestionPipeline
from app.providers.storage import get_storage_provider
from app.providers.vectorstore.qdrant import QdrantVectorStore
from app.services.audit import log_rag_query

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".md", ".txt"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


# Pydantic Schemas
class DepartmentItem(BaseModel):
    id: str
    code: str
    name: str


class DocumentListItem(BaseModel):
    id: str
    title: str
    department_id: str
    department_code: str
    department_name: str
    visibility: str
    min_role_level: int
    doc_type: str
    version: str
    status: str
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    created_at: datetime


class UpdateDocumentLabelsRequest(BaseModel):
    title: Optional[str] = None
    department_id: Optional[str] = None
    visibility: Optional[str] = None
    min_role_level: Optional[int] = None
    status: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class UserAdminItem(BaseModel):
    id: str
    email: str
    full_name: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    memberships: List[Dict[str, Any]]


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_admin: bool = False
    memberships: Optional[List[Dict[str, Any]]] = None


class CreateUserResponse(BaseModel):
    user: UserAdminItem
    temporary_password: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    department: Optional[str] = None
    role: Optional[str] = None


class UpdateMembershipsRequest(BaseModel):
    memberships: List[Dict[str, Any]]  # [{"department_id": str, "role_level": int}]


class AuditLogItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    question: Optional[str] = None
    chunk_ids: Optional[List[str]] = None
    sources_count: int
    outcome: str
    created_at: datetime


class AuditLogPage(BaseModel):
    items: List[AuditLogItem]
    total: int
    page: int
    per_page: int


class IngestionRunItem(BaseModel):
    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    summary: Optional[Dict[str, Any]] = None
    triggered_by: Optional[str] = None


# 1. Departments List
@router.get("/departments", response_model=List[DepartmentItem])
def list_departments(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    depts = db.query(Department).order_by(Department.code.asc()).all()
    return [DepartmentItem(id=str(d.id), code=d.code, name=d.name) for d in depts]


# 2. Documents Management
@router.get("/documents", response_model=List[DocumentListItem])
def list_documents(
    department_id: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    target_dept = department_id or department
    if target_dept and target_dept.lower() != "all":
        if target_dept.lower() in ["company", "company-wide", "company_wide"]:
            query = query.filter(Document.visibility == "company")
        else:
            try:
                query = query.filter(Document.department_id == UUID(target_dept))
            except (ValueError, TypeError):
                query = query.join(Department).filter(
                    func.lower(Department.code) == target_dept.lower().strip()
                )
    if status and status.lower() != "all":
        query = query.filter(Document.status == status)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(Document.title.ilike(s))

    docs = query.order_by(Document.created_at.desc()).all()
    return [
        DocumentListItem(
            id=str(d.id),
            title=d.title,
            department_id=str(d.department_id),
            department_code=d.department.code,
            department_name=d.department.name,
            visibility=d.visibility,
            min_role_level=d.min_role_level,
            doc_type=d.doc_type,
            version=d.version,
            status=d.status,
            effective_date=d.effective_date,
            expiration_date=d.expiration_date,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.post("/documents", response_model=DocumentListItem)
@router.post("/documents/upload", response_model=DocumentListItem)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    department_id: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    visibility: str = Form("company"),
    min_role_level: int = Form(1),
    doc_type: str = Form("policy"),
    version: str = Form("1.0"),
    effective_date: Optional[str] = Form(None),
    expiration_date: Optional[str] = Form(None),
    ingest_now: bool = Form(True),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target_dept = department_id or department or "HR"
    dept = None
    try:
        dept = db.query(Department).filter(Department.id == UUID(target_dept)).first()
    except (ValueError, TypeError):
        dept = db.query(Department).filter(Department.code == target_dept.upper().strip()).first()

    if not dept:
        dept = Department(code=target_dept.upper().strip(), name=f"{target_dept.upper().strip()} Department")
        db.add(dept)
        db.flush()
    # Extension and MIME checks
    filename = file.filename or "uploaded_file"
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' not allowed. Must be one of: {ALLOWED_EXTENSIONS}",
        )

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds 20 MB size limit ({len(content)} bytes)",
        )

    # Safe random storage key
    safe_token = secrets.token_hex(8)
    storage_key = f"documents/uploads/{safe_token}_{filename}"
    storage = get_storage_provider()
    import io
    storage.upload_file(io.BytesIO(content), storage_key)

    eff_dt = datetime.fromisoformat(effective_date) if effective_date else None
    exp_dt = datetime.fromisoformat(expiration_date) if expiration_date else None

    import hashlib
    file_hash = hashlib.sha256(content).hexdigest()

    doc = Document(
        title=title.strip(),
        department_id=dept.id,
        visibility=visibility,
        min_role_level=min_role_level,
        doc_type=doc_type,
        version=version,
        effective_date=eff_dt,
        expiration_date=exp_dt,
        status="active",
        storage_key=storage_key,
        content_hash=file_hash,
        owner_id=current_admin.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_rag_query(
        db=db,
        user_id=UUID(str(current_admin.id)),
        question=f"Uploaded document '{doc.title}' ({doc.id})",
        chunk_ids=[],
        outcome="admin_upload",
        action="admin_document_upload",
    )

    return DocumentListItem(
        id=str(doc.id),
        title=doc.title,
        department_id=str(doc.department_id),
        department_code=doc.department.code,
        department_name=doc.department.name,
        visibility=doc.visibility,
        min_role_level=doc.min_role_level,
        doc_type=doc.doc_type,
        version=doc.version,
        status=doc.status,
        effective_date=doc.effective_date,
        expiration_date=doc.expiration_date,
        created_at=doc.created_at,
    )


@router.patch("/documents/{document_id}", response_model=DocumentListItem)
def update_document_labels(
    document_id: UUID,
    body: UpdateDocumentLabelsRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if body.title is not None:
        doc.title = body.title.strip()  # type: ignore[assignment]
    if body.department_id is not None:
        doc.department_id = UUID(body.department_id)  # type: ignore[assignment]
    if body.visibility is not None:
        doc.visibility = body.visibility  # type: ignore[assignment]
    if body.min_role_level is not None:
        doc.min_role_level = body.min_role_level  # type: ignore[assignment]
    if body.status is not None:
        doc.status = body.status  # type: ignore[assignment]
    if body.effective_date is not None:
        doc.effective_date = body.effective_date  # type: ignore[assignment]
    if body.expiration_date is not None:
        doc.expiration_date = body.expiration_date  # type: ignore[assignment]

    db.commit()

    log_rag_query(
        db=db,
        user_id=UUID(str(current_admin.id)),
        question=f"Updated labels for document '{doc.title}' ({doc.id})",
        chunk_ids=[],
        outcome="admin_update",
        action="admin_document_update",
    )

    return DocumentListItem(
        id=str(doc.id),
        title=doc.title,
        department_id=str(doc.department_id),
        department_code=doc.department.code,
        department_name=doc.department.name,
        visibility=doc.visibility,
        min_role_level=doc.min_role_level,
        doc_type=doc.doc_type,
        version=doc.version,
        status=doc.status,
        effective_date=doc.effective_date,
        expiration_date=doc.expiration_date,
        created_at=doc.created_at,
    )


@router.post("/documents/{document_id}/archive")
def archive_document(
    document_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.status = "archived"  # type: ignore[assignment]
    db.commit()

    # Flush vectors from Qdrant
    vs = QdrantVectorStore()
    vs.delete_by_document_id(str(doc.id))

    log_rag_query(
        db=db,
        user_id=UUID(str(current_admin.id)),
        question=f"Archived document '{doc.title}' ({doc.id})",
        chunk_ids=[],
        outcome="admin_archive",
        action="admin_document_archive",
    )

    return {"message": "Document archived successfully"}


# 3. Ingestion Runs & Quarantine
@router.get("/ingestion/runs", response_model=List[IngestionRunItem])
def list_ingestion_runs(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    runs = db.query(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(20).all()
    return [
        IngestionRunItem(
            id=str(r.id),
            status=r.status,
            started_at=r.started_at,
            finished_at=r.finished_at,
            summary=r.summary,
            triggered_by=str(r.triggered_by) if r.triggered_by else None,
        )
        for r in runs
    ]


@router.post("/ingestion/runs", response_model=IngestionRunItem)
def start_ingestion_run(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from pathlib import Path
    sample_dir = Path("../data/sample_docs").resolve()
    if not sample_dir.exists():
        sample_dir = Path("data/sample_docs").resolve()

    pipeline = IngestionPipeline(db)
    job = pipeline.run_folder_ingestion(sample_dir)

    return IngestionRunItem(
        id=str(job.id),
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        summary=job.summary,
        triggered_by=str(job.triggered_by) if job.triggered_by else None,
    )


@router.get("/ingestion/runs/{run_id}")
def get_ingestion_run_detail(
    run_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    job = db.query(IngestionJob).filter(IngestionJob.id == run_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion run not found")

    items = (
        db.query(IngestionJobItem)
        .filter(IngestionJobItem.job_id == job.id)
        .order_by(IngestionJobItem.file_path.asc())
        .all()
    )

    return {
        "id": str(job.id),
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "summary": job.summary,
        "items": [
            {
                "id": str(item.id),
                "file_path": item.file_path,
                "result": item.result,
                "reason": item.reason,
            }
            for item in items
        ],
    }


@router.get("/quarantine")
def list_quarantine(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    items = (
        db.query(IngestionJobItem)
        .filter(IngestionJobItem.result == "quarantined")
        .order_by(IngestionJobItem.id.desc())
        .all()
    )
    return [
        {
            "id": str(item.id),
            "file_path": item.file_path,
            "reason": item.reason,
            "detected_at": item.job.started_at if item.job else None,
        }
        for item in items
    ]


@router.post("/quarantine/{item_id}/release")
def release_quarantine_item(
    item_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(IngestionJobItem).filter(IngestionJobItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarantine item not found")

    item.result = "processed"  # type: ignore[assignment]
    item.reason = "Released by administrator"  # type: ignore[assignment]
    db.commit()
    return {"message": "Item released from quarantine"}


@router.post("/quarantine/{item_id}/reject")
def reject_quarantine_item(
    item_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(IngestionJobItem).filter(IngestionJobItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarantine item not found")

    item.result = "rejected"  # type: ignore[assignment]
    item.reason = "Rejected by administrator"  # type: ignore[assignment]
    db.commit()
    return {"message": "Item rejected from quarantine"}


# 4. Users & Memberships
@router.get("/users", response_model=List[UserAdminItem])
def list_users(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.full_name.asc()).all()
    result = []
    for u in users:
        memberships = [
            {
                "department_id": str(m.department_id),
                "department_code": m.department.code,
                "department_name": m.department.name,
                "department": m.department.code,
                "role_level": m.role_level,
                "role": "head" if m.role_level >= 3 else ("manager" if m.role_level == 2 else "member"),
            }
            for m in u.memberships
        ]
        result.append(
            UserAdminItem(
                id=str(u.id),
                email=u.email,
                full_name=u.full_name,
                is_admin=u.is_admin,
                is_active=u.is_active,
                created_at=u.created_at,
                memberships=memberships,
            )
        )
    return result


@router.post("/users", response_model=CreateUserResponse)
def create_user(
    body: CreateUserRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    name_to_use = (body.full_name or body.name or "").strip()
    if not name_to_use:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name is required")

    existing = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Generate temporary password
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    temp_pass = "".join(secrets.choice(chars) for _ in range(12))

    new_user = User(
        email=body.email.lower().strip(),
        full_name=name_to_use,
        password_hash=hash_password(temp_pass),
        is_admin=body.is_admin,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    memberships_out = []
    if body.department:
        dept_str = body.department.strip()
        dept = db.query(Department).filter(func.lower(Department.code) == dept_str.lower()).first()
        if not dept:
            dept = db.query(Department).filter(func.lower(Department.name) == dept_str.lower()).first()
        if not dept:
            dept = Department(code=dept_str.upper(), name=f"{dept_str} Department")
            db.add(dept)
            db.flush()

        role_str = (body.role or "member").lower().strip()
        role_level = 3 if role_str == "head" else (2 if role_str == "manager" else 1)
        mem = Membership(
            user_id=new_user.id,
            department_id=dept.id,
            role_level=role_level,
        )
        db.add(mem)
        memberships_out.append({
            "department_id": str(dept.id),
            "department_code": dept.code,
            "department_name": dept.name,
            "role_level": role_level,
        })
    elif body.memberships:
        for m in body.memberships:
            db.add(
                Membership(
                    user_id=new_user.id,
                    department_id=UUID(m["department_id"]),
                    role_level=int(m["role_level"]),
                )
            )
            memberships_out.append(m)

    db.commit()
    db.refresh(new_user)

    log_rag_query(
        db=db,
        user_id=UUID(str(current_admin.id)),
        question=f"Created user '{new_user.email}'",
        chunk_ids=[],
        outcome="admin_create_user",
        action="admin_user_create",
    )

    user_item = UserAdminItem(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        is_admin=new_user.is_admin,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        memberships=memberships_out,
    )
    return CreateUserResponse(user=user_item, temporary_password=temp_pass)


@router.patch("/users/{user_id}", response_model=UserAdminItem)
def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.full_name is not None:
        target.full_name = body.full_name.strip()  # type: ignore[assignment]
    if body.is_admin is not None:
        target.is_admin = body.is_admin  # type: ignore[assignment]
    if body.is_active is not None:
        target.is_active = body.is_active  # type: ignore[assignment]

    if body.department:
        dept_str = body.department.strip()
        dept = db.query(Department).filter(func.lower(Department.code) == dept_str.lower()).first()
        if not dept:
            dept = db.query(Department).filter(func.lower(Department.name) == dept_str.lower()).first()
        if not dept:
            dept = Department(code=dept_str.upper(), name=f"{dept_str} Department")
            db.add(dept)
            db.flush()

        role_str = (body.role or "member").lower().strip()
        role_lvl = 3 if role_str == "head" else (2 if role_str == "manager" else 1)

        existing_mem = db.query(Membership).filter(Membership.user_id == target.id).first()
        if existing_mem:
            existing_mem.department_id = dept.id
            existing_mem.role_level = role_lvl
        else:
            db.add(Membership(user_id=target.id, department_id=dept.id, role_level=role_lvl))
    elif body.role and target.memberships:
        role_str = body.role.lower().strip()
        role_lvl = 3 if role_str == "head" else (2 if role_str == "manager" else 1)
        target.memberships[0].role_level = role_lvl

    db.commit()
    db.refresh(target)

    memberships = [
        {
            "department_id": str(m.department_id),
            "department_code": m.department.code,
            "department_name": m.department.name,
            "role_level": m.role_level,
        }
        for m in target.memberships
    ]
    return UserAdminItem(
        id=str(target.id),
        email=target.email,
        full_name=target.full_name,
        is_admin=target.is_admin,
        is_active=target.is_active,
        created_at=target.created_at,
        memberships=memberships,
    )


@router.put("/users/{user_id}/memberships")
def update_user_memberships(
    user_id: UUID,
    body: UpdateMembershipsRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Clear old memberships and set new ones
    db.query(Membership).filter(Membership.user_id == user_id).delete()
    for m in body.memberships:
        db.add(
            Membership(
                user_id=user_id,
                department_id=UUID(m["department_id"]),
                role_level=int(m["role_level"]),
            )
        )
    db.commit()
    return {"message": "Memberships updated successfully"}


# 5. Audit Log (paginated)
@router.get("/audit", response_model=AuditLogPage)
def list_audit_logs(
    user_id: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == UUID(user_id))
    if outcome:
        query = query.filter(AuditLog.outcome == outcome)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # Pre-fetch user emails
    user_ids = [entry.user_id for entry in logs if entry.user_id]
    users_map = {u.id: u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    items = [
        AuditLogItem(
            id=str(entry.id),
            user_id=str(entry.user_id) if entry.user_id else None,
            user_email=users_map.get(entry.user_id) if entry.user_id else "Anonymous",
            action=entry.action,
            question=entry.question,
            chunk_ids=entry.chunk_ids,
            sources_count=len(entry.chunk_ids) if isinstance(entry.chunk_ids, list) else 0,
            outcome=entry.outcome,
            created_at=entry.created_at,
        )
        for entry in logs
    ]

    return AuditLogPage(items=items, total=total, page=page, per_page=per_page)


# 6. Observability, Logging, Analytics & Guardrails Monitoring
@router.get("/monitoring/logs")
def get_monitoring_logs(
    limit: int = Query(150, ge=1, le=500),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
):
    """Retrieve live structured system logs in the enterprise format with level, search, and date-time filters."""
    from app.core.logging import get_log_buffer
    return get_log_buffer(
        limit=limit,
        level=level,
        search=search,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/monitoring/metrics")
def get_system_monitoring_metrics(
    current_admin: User = Depends(get_current_admin),
):
    """Retrieve live system metrics for LangSmith tracing, models, embeddings, and guardrails."""
    from app.services.monitoring import get_monitoring_metrics
    return get_monitoring_metrics()


@router.get("/monitoring/analytics")
def get_system_monitoring_analytics(
    range_param: str = Query("7d", alias="range"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve interactive telemetry analytics: cost, latency, context usage per user and overall trends."""
    from app.services.monitoring import get_telemetry_analytics
    return get_telemetry_analytics(db=db, range_param=range_param)

