from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class SectionContent(BaseModel):
    text: str
    heading: Optional[str] = None
    page_number: Optional[int] = None


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> List[SectionContent]:
        """Parse file into section/page contents."""
        pass
