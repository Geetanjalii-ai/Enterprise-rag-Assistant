from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, field_validator


class DocumentManifestItem(BaseModel):
    file: str
    title: str
    doc_id: Optional[str] = None
    department: str
    doc_type: str = "general"
    visibility: str  # 'company' or 'department'
    min_role: str = "member"  # 'member', 'manager', 'head'
    version: str = "1.0"
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    owner: Optional[str] = None

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        v_clean = v.lower().strip()
        if v_clean not in ["company", "department"]:
            raise ValueError(f"visibility must be 'company' or 'department', got '{v}'")
        return v_clean

    @field_validator("min_role")
    @classmethod
    def validate_min_role(cls, v: str) -> str:
        v_clean = v.lower().strip()
        if v_clean not in ["member", "manager", "head"]:
            raise ValueError(f"min_role must be 'member', 'manager', or 'head', got '{v}'")
        return v_clean

    @property
    def min_role_level(self) -> int:
        role_map = {"member": 1, "manager": 2, "head": 3}
        return role_map.get(self.min_role.lower(), 1)


def load_manifest(manifest_path: Path) -> Dict[str, DocumentManifestItem]:
    """Load and parse manifest.yaml, indexed by normalized relative file path."""
    if not manifest_path.exists():
        return {}

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        return {}

    manifest_map: Dict[str, DocumentManifestItem] = {}
    for item in data:
        try:
            validated = DocumentManifestItem(**item)
            # Normalize path key e.g. "hr/leave_policy_v3.1.pdf"
            norm_key = str(Path(validated.file)).replace("\\", "/")
            manifest_map[norm_key] = validated
        except Exception:
            # Invalid item will be treated as missing in quarantine check
            continue

    return manifest_map
