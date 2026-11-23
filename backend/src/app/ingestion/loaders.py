from pathlib import Path
from typing import List

from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader, TextLoader
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document


def get_langchain_loader(file_path: Path) -> BaseLoader:
    """Get the appropriate LangChain document loader based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return PyMuPDFLoader(str(file_path))
    elif suffix in [".docx", ".doc"]:
        # pyrefly: ignore[direct-abstract-base-instantiation]
        return Docx2txtLoader(str(file_path))
    elif suffix in [".md", ".markdown", ".txt", ".text"]:
        return TextLoader(str(file_path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file format for LangChain loader: {suffix}")


def load_documents_with_langchain(file_path: Path) -> List[Document]:
    """Load documents from disk using LangChain document loaders."""
    loader = get_langchain_loader(file_path)
    return loader.load()
