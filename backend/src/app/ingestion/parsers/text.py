from pathlib import Path
from typing import List

from app.ingestion.parsers.interface import BaseParser, SectionContent


class TextParser(BaseParser):
    def parse(self, file_path: Path) -> List[SectionContent]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read().strip()

        if not text:
            return []

        return [
            SectionContent(
                text=text,
                heading=file_path.stem.replace("_", " ").title(),
                page_number=1,
            )
        ]
