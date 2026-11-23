from typing import List, Optional

from pydantic import BaseModel, Field


class ParsedSection(BaseModel):
    text: str
    section: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class ParsedDocument(BaseModel):
    title: Optional[str] = None
    sections: List[ParsedSection] = Field(default_factory=list)
