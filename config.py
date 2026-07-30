"""
Central config for the RegTrack module.

LOCAL_TEST_MODE = True  -> uses TF-IDF similarity + a rule-based mock "LLM"
                           so the whole pipeline runs with ZERO external
                           dependencies (no HuggingFace download, no API key).
                           Use this while developing / when offline.

LOCAL_TEST_MODE = False -> uses sentence-transformers embeddings + ChromaDB
                           + a real Claude API call for gap analysis.
                           Use this for the actual hackathon demo.
"""

import os

LOCAL_TEST_MODE = os.getenv("REGTRACK_LOCAL_TEST_MODE", "true").lower() == "true"

# Embedding model (only used when LOCAL_TEST_MODE = False)
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Anthropic API (only used when LOCAL_TEST_MODE = False)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-6"

# Chunking
CHUNK_SIZE = 500        # characters
CHUNK_OVERLAP = 50

# Retrieval
TOP_K_MATCHES = 1        # how many old-policy chunks to retrieve per new clause

# Paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_store")
