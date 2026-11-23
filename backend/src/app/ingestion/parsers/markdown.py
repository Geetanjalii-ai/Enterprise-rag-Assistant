import re
from pathlib import Path
from typing import List

from app.ingestion.parsers.interface import BaseParser, SectionContent


class MarkdownParser(BaseParser):
    def parse(self, file_path: Path) -> List[SectionContent]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        results: List[SectionContent] = []
        lines = content.split("\n")

        current_heading = None
        current_lines: List[str] = []

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                if current_lines:
                    text_block = "\n".join(current_lines).strip()
                    if text_block:
                        results.append(
                            SectionContent(
                                text=text_block,
                                heading=current_heading,
                                page_number=1,
                            )
                        )
                    current_lines = []
                current_heading = heading_match.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            text_block = "\n".join(current_lines).strip()
            if text_block:
                results.append(
                    SectionContent(
                        text=text_block,
                        heading=current_heading,
                        page_number=1,
                    )
                )

        return results
