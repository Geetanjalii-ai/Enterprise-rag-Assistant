import hashlib
from pathlib import Path


def compute_file_hash(file_path: Path) -> str:
    """Compute sha256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()
