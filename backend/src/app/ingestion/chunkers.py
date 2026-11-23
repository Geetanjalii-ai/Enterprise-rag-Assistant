from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import tiktoken
from langchain_core.documents import Document

from app.ingestion.parsers.interface import SectionContent


@dataclass
class TextChunk:
    chunk_index: int
    text: str
    section: Optional[str]
    page_start: Optional[int]
    page_end: Optional[int]
    token_count: int


class SectionChunker:
    def __init__(
        self,
        target_tokens: int = 400,
        max_tokens: int = 550,
        overlap_tokens: int = 50,
        model_name: str = "cl100k_base",
    ):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        try:
            self.tokenizer = tiktoken.get_encoding(model_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def chunk_sections(self, sections: List[SectionContent]) -> List[TextChunk]:
        chunks: List[TextChunk] = []
        chunk_idx = 0

        for sec in sections:
            sec_text = sec.text.strip()
            if not sec_text:
                continue

            sec_tokens = self.tokenizer.encode(sec_text)
            total_tokens = len(sec_tokens)

            # If section fits within max_tokens, keep as a single chunk
            if total_tokens <= self.max_tokens:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_idx,
                        text=sec_text,
                        section=sec.heading,
                        page_start=sec.page_number,
                        page_end=sec.page_number,
                        token_count=total_tokens,
                    )
                )
                chunk_idx += 1
            else:
                # Split large section into overlapping chunks along paragraphs or sentences
                paragraphs = sec_text.split("\n\n")
                current_batch: List[str] = []
                current_tokens = 0
                page_start = sec.page_number
                page_end = sec.page_number

                for p in paragraphs:
                    p_clean = p.strip()
                    if not p_clean:
                        continue
                    p_tok_count = self.count_tokens(p_clean)

                    if current_tokens + p_tok_count <= self.max_tokens or not current_batch:
                        current_batch.append(p_clean)
                        current_tokens += p_tok_count
                    else:
                        chunk_body = "\n\n".join(current_batch)
                        chunks.append(
                            TextChunk(
                                chunk_index=chunk_idx,
                                text=chunk_body,
                                section=sec.heading,
                                page_start=page_start,
                                page_end=page_end,
                                token_count=self.count_tokens(chunk_body),
                            )
                        )
                        chunk_idx += 1

                        # Keep overlap paragraph if small enough
                        if current_batch and p_tok_count < self.max_tokens:
                            last_p = current_batch[-1]
                            last_p_tok = self.count_tokens(last_p)
                            if last_p_tok <= self.overlap_tokens:
                                current_batch = [last_p, p_clean]
                                current_tokens = last_p_tok + p_tok_count
                            else:
                                current_batch = [p_clean]
                                current_tokens = p_tok_count
                        else:
                            current_batch = [p_clean]
                            current_tokens = p_tok_count

                if current_batch:
                    chunk_body = "\n\n".join(current_batch)
                    chunks.append(
                        TextChunk(
                            chunk_index=chunk_idx,
                            text=chunk_body,
                            section=sec.heading,
                            page_start=page_start,
                            page_end=page_end,
                            token_count=self.count_tokens(chunk_body),
                        )
                    )
                    chunk_idx += 1

        return chunks

    def chunk_langchain_documents(self, docs: List[Document]) -> List[TextChunk]:
        """Convert a list of LangChain Document objects into chunked TextChunk items."""
        sections: List[SectionContent] = []
        for doc in docs:
            page_val = doc.metadata.get("page")
            page_num: Optional[int] = None
            if page_val is not None and isinstance(page_val, int):
                # PyMuPDFLoader uses 0-indexed page numbering; convert to 1-indexed
                page_num = page_val + 1
            elif isinstance(doc.metadata.get("page_number"), int):
                page_num = doc.metadata.get("page_number")

            sections.append(
                SectionContent(
                    text=doc.page_content,
                    heading=doc.metadata.get("title") or doc.metadata.get("section"),
                    page_number=page_num,
                )
            )
        return self.chunk_sections(sections)

    def to_langchain_documents(
        self, chunks: List[TextChunk], base_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Convert chunks to native LangChain Document objects."""
        meta = base_metadata or {}
        return [
            Document(
                page_content=c.text,
                metadata={
                    **meta,
                    "chunk_index": c.chunk_index,
                    "section": c.section,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "token_count": c.token_count,
                },
            )
            for c in chunks
        ]
