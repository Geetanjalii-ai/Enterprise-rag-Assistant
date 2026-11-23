import re
from typing import Any, Dict, List, Set

from app.retrieval.context_builder import ContextSource


def extract_citations(answer_text: str, sources: List[ContextSource]) -> List[Dict[str, Any]]:
    """Scan the generated LLM response for [N] bracketed citations and match

    them against the numbered ContextSource entries.
    """
    matches = re.findall(r"\[(\d+)\]", answer_text)
    cited_indices: Set[int] = {int(m) for m in matches}

    source_map = {s.index: s for s in sources}
    citations: List[Dict[str, Any]] = []

    for idx in sorted(cited_indices):
        src = source_map.get(idx)
        if src:
            citations.append(
                {
                    "citation_number": idx,
                    "chunk_id": src.chunk_id,
                    "document_id": src.doc_id,
                    "document_title": src.doc_title,
                    "section": src.section,
                    "page_start": src.page_start,
                    "page_end": src.page_end,
                }
            )

    return citations
