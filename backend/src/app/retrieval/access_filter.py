from datetime import datetime, timezone
from typing import List, Tuple
from uuid import UUID

from qdrant_client.http import models as qmodels

from app.db.models import User


def build_qdrant_access_filter(user: User, current_time: datetime | None = None) -> qmodels.Filter:
    """Build authoritative Qdrant security and temporal filter.

    Enforces SEC-1:
    - Filters by document status == 'active'.
    - Temporal validity: effective_ts <= now <= expiry_ts.
    - If user is admin: full access across all active company/department documents.
    - If user is regular user:
        * Branch A (Company-wide): visibility == 'company' AND min_role_level <= max(user_roles, default 1).
        * Branch B (Departmental): For each user membership (dept_id, role_level),
          visibility == 'department' AND department_id == dept_id AND min_role_level <= role_level.
    """
    now = current_time or datetime.now(timezone.utc)
    now_ts = int(now.timestamp())

    # Mandatory baseline filters for all documents
    must_conditions: List[qmodels.Condition] = [
        qmodels.FieldCondition(key="status", match=qmodels.MatchValue(value="active")),
        qmodels.FieldCondition(key="effective_ts", range=qmodels.Range(lte=now_ts)),
        qmodels.FieldCondition(key="expiry_ts", range=qmodels.Range(gte=now_ts)),
    ]

    # Global Admin bypasses department/role boundaries
    if user.is_admin:
        return qmodels.Filter(must=must_conditions)

    # Collect user memberships (department_id, role_level)
    memberships: List[Tuple[UUID, int]] = [(m.department_id, m.role_level) for m in user.memberships]
    max_role_level = max([m[1] for m in memberships], default=1)

    should_conditions: List[qmodels.Condition] = []

    # Branch A: Company-wide visible documents accessible at user's max role level
    should_conditions.append(
        qmodels.Filter(
            must=[
                qmodels.FieldCondition(key="visibility", match=qmodels.MatchValue(value="company")),
                qmodels.FieldCondition(key="min_role_level", range=qmodels.Range(lte=max_role_level)),
            ]
        )
    )

    # Branch B: Department-specific documents accessible per active membership
    for dept_id, role_level in memberships:
        should_conditions.append(
            qmodels.Filter(
                must=[
                    qmodels.FieldCondition(key="visibility", match=qmodels.MatchValue(value="department")),
                    qmodels.FieldCondition(key="department_id", match=qmodels.MatchValue(value=str(dept_id))),
                    qmodels.FieldCondition(key="min_role_level", range=qmodels.Range(lte=role_level)),
                ]
            )
        )

    # Must satisfy baseline conditions AND at least one branch condition
    return qmodels.Filter(must=must_conditions, should=should_conditions)
