from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import tiktoken

from app.core.config import get_settings


@dataclass
class ContextSource:
    index: int
    chunk_id: str
    doc_id: str
    doc_title: str
    section: str | None
    page_start: int | None
    page_end: int | None
    text: str


class ContextBuilder:
    def __init__(self, token_budget: int = 3000, model_name: str = "cl100k_base"):
        settings = get_settings()
        self.token_budget = token_budget or getattr(settings, "LLM_CONTEXT_TOKEN_BUDGET", 3000)
        try:
            self.tokenizer = tiktoken.get_encoding(model_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def build_context(self, items: List[Dict[str, Any]]) -> Tuple[str, List[ContextSource]]:
        """Format retrieved items into a numbered, breadcrumbed context block

        respecting the LLM_CONTEXT_TOKEN_BUDGET.
        """
        if not items:
            return "", []

        sources: List[ContextSource] = []
        formatted_blocks: List[str] = []
        accumulated_tokens = 0

        for i, item in enumerate(items, start=1):
            payload = item.get("payload", {})
            text = payload.get("text", "").strip()
            doc_title = payload.get("doc_title", "Untitled Document")
            section = payload.get("section")
            page_start = payload.get("page_start")
            page_end = payload.get("page_end")
            chunk_id = str(payload.get("chunk_id", ""))
            doc_id = str(payload.get("document_id", ""))

            # Construct header breadcrumb
            header_parts = [f"[{i}] Document: \"{doc_title}\""]
            if section:
                header_parts.append(f"Section: \"{section}\"")
            if page_start is not None:
                if page_end is not None and page_end != page_start:
                    header_parts.append(f"Pages: {page_start}-{page_end}")
                else:
                    header_parts.append(f"Page: {page_start}")

            header = " | ".join(header_parts)
            block = f"{header}\n{text}\n"
            block_tokens = self.count_tokens(block)

            # Check token budget
            if accumulated_tokens + block_tokens > self.token_budget and formatted_blocks:
                # Exceeded budget; truncate remaining
                break

            formatted_blocks.append(block)
            accumulated_tokens += block_tokens
            sources.append(
                ContextSource(
                    index=i,
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    doc_title=doc_title,
                    section=section,
                    page_start=page_start,
                    page_end=page_end,
                    text=text,
                )
            )

        context_string = "\n---\n".join(formatted_blocks)
        return context_string, sources
