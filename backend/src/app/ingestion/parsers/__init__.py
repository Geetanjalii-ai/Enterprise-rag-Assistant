from pathlib import Path

from app.ingestion.parsers.docx import DocxParser
from app.ingestion.parsers.interface import BaseParser
from app.ingestion.parsers.markdown import MarkdownParser
from app.ingestion.parsers.pdf import PDFParser
from app.ingestion.parsers.text import TextParser


def get_parser_for_file(file_path: Path) -> BaseParser:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return PDFParser()
    elif suffix in [".docx", ".doc"]:
        return DocxParser()
    elif suffix in [".md", ".markdown"]:
        return MarkdownParser()
    elif suffix in [".txt", ".text"]:
        return TextParser()
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


__all__ = [
    "BaseParser",
    "PDFParser",
    "DocxParser",
    "MarkdownParser",
    "TextParser",
    "get_parser_for_file",
]
