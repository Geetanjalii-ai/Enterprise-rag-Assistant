from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from app.ingestion.parsers.interface import BaseParser, SectionContent


class PDFParser(BaseParser):
    def parse(self, file_path: Path) -> List[SectionContent]:
        results: List[SectionContent] = []
        doc = fitz.open(str(file_path))

        current_heading = None
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Extract text blocks with PyMuPDF
            blocks = page.get_text("blocks")
            page_text_pieces = []

            for b in blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                text = b[4].strip()
                if not text:
                    continue

                lines = text.split("\n")
                first_line = lines[0].strip()

                # Basic heuristic for headings: short single line, title-cased or numbered
                if (
                    len(lines) <= 2
                    and len(first_line) < 80
                    and (
                        first_line.isupper()
                        or first_line.istitle()
                        or (first_line and first_line[0].isdigit() and "." in first_line[:5])
                    )
                ):
                    current_heading = first_line

                page_text_pieces.append(text)

            combined_page_text = "\n\n".join(page_text_pieces)
            if combined_page_text:
                results.append(
                    SectionContent(
                        text=combined_page_text,
                        heading=current_heading,
                        page_number=page_num + 1,
                    )
                )

        doc.close()
        return results
