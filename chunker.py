"""
Splits a document's raw text into meaningful regulatory chunks.

Strategy:
1. Clean whitespace and obvious PDF artifacts.
2. Split on numbered regulatory sections such as:
   1.
   2.
   3.1
   4.2.1
3. If numbered splitting doesn't produce useful chunks,
   fall back to paragraph-based splitting.
4. Finally use fixed-size chunks for unusually large paragraphs.
"""

import re

from config import CHUNK_SIZE, CHUNK_OVERLAP


# Matches:
# 1.
# 2.
# 3.1
# 4.2.1
# 1.1.2.
CLAUSE_PATTERN = re.compile(
    r"(?m)(?=^\s*\d+(?:\.\d+)*\.?\s+)"
)


def _clean_text(text: str) -> str:
    """Clean common PDF extraction artifacts."""

    # Replace Unicode replacement characters.
    text = text.replace("\ufffd", "")

    # Normalize non-breaking spaces.
    text = text.replace("\xa0", " ")

    # Normalize Windows line endings.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces.
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _split_by_clause_markers(text: str) -> list[str]:
    """Split text using numbered section markers."""

    raw_chunks = CLAUSE_PATTERN.split(text)

    chunks = []

    for chunk in raw_chunks:
        chunk = chunk.strip()

        if len(chunk) > 30:
            chunks.append(chunk)

    return chunks


def _split_by_paragraphs(text: str) -> list[str]:
    """Split text into paragraph-sized chunks."""

    paragraphs = re.split(r"\n\s*\n+", text)

    return [
        p.strip()
        for p in paragraphs
        if len(p.strip()) > 30
    ]


def _split_fixed_size(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Fallback sliding-window chunking."""

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
    Returns a list of text chunks representing
    regulatory clauses/sections.
    """

    text = _clean_text(text)

    if not text:
        return []

    # First try numbered clauses.
    clause_chunks = _split_by_clause_markers(text)

    if 2 <= len(clause_chunks) <= 200:
        return clause_chunks

    # If numbered sections aren't detected, try paragraphs.
    paragraph_chunks = _split_by_paragraphs(text)

    if 2 <= len(paragraph_chunks) <= 200:
        return paragraph_chunks

    # Last resort.
    return _split_fixed_size(text)