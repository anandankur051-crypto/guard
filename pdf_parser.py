"""
Extracts raw text from a PDF (or plain .txt for local testing).
"""

import os


def extract_text(filepath: str) -> str:
    """
    Extracts text from a .pdf or .txt file.
    Returns a single string with the full document text.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    if ext == ".pdf":
        import pdfplumber  # imported lazily so .txt mode needs no extra deps

        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    raise ValueError(f"Unsupported file type: {ext}. Use .pdf or .txt")
