"""
Embedding backend.

Two implementations behind one interface:
- RealEmbedder: sentence-transformers (semantic, needs model download)
- LocalTestEmbedder: TF-IDF (offline, no downloads, good enough to prove
  the pipeline logic works end-to-end without internet access)

Both expose the same .encode(list[str]) -> np.ndarray interface so the
rest of the pipeline doesn't care which one is active.
"""

import numpy as np
from config import LOCAL_TEST_MODE, EMBEDDING_MODEL_NAME


class RealEmbedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)


class LocalTestEmbedder:
    """
    TF-IDF based stand-in for a real embedding model. Not semantically
    aware the way sentence-transformers is (won't catch pure synonym
    swaps as well) but is enough to validate retrieval + pipeline logic
    with zero network dependency.
    """
    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self._fitted = False

    def fit(self, corpus: list[str]):
        self.vectorizer.fit(corpus)
        self._fitted = True

    def encode(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            # fit on the fly if caller forgot -- fine for small demo corpora
            self.fit(texts)
        vecs = self.vectorizer.transform(texts)
        return vecs.toarray()


def get_embedder():
    if LOCAL_TEST_MODE:
        return LocalTestEmbedder()
    return RealEmbedder()
