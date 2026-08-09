"""
Central config for the RegTrack module.

LOCAL_TEST_MODE = True  -> uses TF-IDF similarity + rule-based mock LLM.
LOCAL_TEST_MODE = False -> uses sentence-transformers embeddings + ChromaDB
                           + Gemini API for gap analysis.
"""

import os

from dotenv import load_dotenv

load_dotenv(
    os.path.join(
        os.path.dirname(__file__),
        ".env"
    )
)

# ============================================================
# MODE
# ============================================================

LOCAL_TEST_MODE = (
    os.getenv("REGTRACK_LOCAL_TEST_MODE", "false").lower() == "true"
)


# ============================================================
# EMBEDDINGS
# ============================================================

# Used only when LOCAL_TEST_MODE = False

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"


# ============================================================
# GEMINI API
# ============================================================

# Used only when LOCAL_TEST_MODE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)


# ============================================================
# CHUNKING
# ============================================================

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


# ============================================================
# RETRIEVAL
# ============================================================

TOP_K_MATCHES = 1


# ============================================================
# PATHS
# ============================================================

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data"
)

CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(__file__),
    "chroma_store"
)