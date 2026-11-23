from pathlib import Path
from typing import List

from docx import Document

from app.ingestion.parsers.interface import BaseParser, SectionContent


class DocxParser(BaseParser):
    def parse(self, file_path: Path) -> List[SectionContent]:
        doc = Document(str(file_path))
        results: List[SectionContent] = []

        current_heading = None
        current_paragraphs: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            if p.style and p.style.name and p.style.name.startswith("Heading"):
                if current_paragraphs:
                    results.append(
                        SectionContent(
                            text="\n\n".join(current_paragraphs),
                            heading=current_heading,
                            page_number=1,
                        )
                    )
                    current_paragraphs = []
                current_heading = text
            else:
                current_paragraphs.append(text)

        # Process tables
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_rows.append(" | ".join(cells))
            if table_rows:
                formatted_table = "\n".join(table_rows)
                current_paragraphs.append(f"Table:\n{formatted_table}")

        if current_paragraphs:
            results.append(
                SectionContent(
                    text="\n\n".join(current_paragraphs),
                    heading=current_heading,
                    page_number=1,
                )
            )

        return results
