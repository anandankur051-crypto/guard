"""
Splits a document's raw text into clause-sized chunks.

Strategy:
1. First try to split on numbered clause markers (e.g. "1.", "2.1", "(a)")
   since regulatory text is almost always structured this way -> gives
   clean, semantically complete chunks.
2. If that yields too few/too many chunks (i.e. the doc isn't numbered
   the way we expect), fall back to fixed-size sliding-window chunking.
"""

import re
from config import CHUNK_SIZE, CHUNK_OVERLAP


CLAUSE_PATTERN = re.compile(
    r"(?=\n\s*(?:\d+\.\d*\.?\d*\s|\(\w\)\s|[A-Z]\.\s))"
)


def _split_by_clause_markers(text: str) -> list[str]:
    raw_chunks = CLAUSE_PATTERN.split(text)
    chunks = [c.strip() for c in raw_chunks if c.strip() and len(c.strip()) > 20]
    return chunks


def _split_fixed_size(text: str, chunk_size: int = CHUNK_SIZE,
                       overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def chunk_document(text: str) -> list[str]:
    """
    Returns a list of text chunks representing individual clauses/sections.
    """
    clause_chunks = _split_by_clause_markers(text)

    # Heuristic: if clause-marker splitting gave a reasonable number of
    # chunks (not 1 giant blob, not hundreds of tiny fragments), use it.
    if 2 <= len(clause_chunks) <= 200:
        return clause_chunks

    return _split_fixed_size(text)
