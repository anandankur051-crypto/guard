"""
Extracts and cleans raw text from a PDF or plain .txt file.
"""

import os
import re


def _clean_text(text: str) -> str:
    """Clean common PDF extraction artifacts."""

    # Remove Unicode replacement characters.
    text = text.replace("\ufffd", "")

    # Normalize non-breaking spaces.
    text = text.replace("\xa0", " ")

    # Normalize line endings.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces before punctuation.
    text = re.sub(r"\s+([,.;:])", r"\1", text)

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_text(filepath: str) -> str:
    """
    Extracts text from a .pdf or .txt file.

    Returns a cleaned string containing the full document text.
    """

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        return _clean_text(text)

    if ext == ".pdf":
        import pdfplumber

        text_parts = []

        with pdfplumber.open(filepath) as pdf:

            for page in pdf.pages:

                page_text = page.extract_text()

                if page_text:
                    text_parts.append(page_text)

        full_text = "\n".join(text_parts)

        return _clean_text(full_text)

    raise ValueError(
        f"Unsupported file type: {ext}. Use .pdf or .txt"
    )