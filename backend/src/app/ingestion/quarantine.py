from typing import Optional, Tuple

from app.ingestion.metadata import DocumentManifestItem


def evaluate_quarantine_rules(
    item: Optional[DocumentManifestItem],
    duplicate_active: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Check FR-ING-9 quarantine rules:
    - Missing metadata/owner
    - Missing department, visibility, or min_role
    - Conflicting duplicate active versions
    """
    if item is None:
        return True, "Missing manifest metadata entry for document"

    if not item.owner:
        return True, "Missing owner label in manifest"

    if not item.department:
        return True, "Missing department label in manifest"

    if not item.visibility:
        return True, "Missing visibility label (company/department) in manifest"

    if not item.min_role:
        return True, "Missing min_role label (member/manager/head) in manifest"

    if duplicate_active:
        return True, f"Conflict: Duplicate active version found for document ID {item.doc_id or item.title}"

    return False, None
