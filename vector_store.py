"""
Stores policy-clause embeddings and retrieves the closest match(es)
for a given new-circular clause.

- LocalVectorStore: pure numpy cosine similarity, in-memory.
- ChromaVectorStore: persistent ChromaDB collection using cosine distance.
"""

import numpy as np

from config import (
    LOCAL_TEST_MODE,
    TOP_K_MATCHES,
    CHROMA_PERSIST_DIR,
)


class LocalVectorStore:

    def __init__(self):
        self.chunks: list[str] = []
        self.vectors: np.ndarray | None = None

    def add(self, chunks: list[str], vectors: np.ndarray):
        self.chunks = chunks
        self.vectors = vectors

    def query(
        self,
        query_vector: np.ndarray,
        top_k: int = TOP_K_MATCHES
    ) -> list[dict]:

        from sklearn.metrics.pairwise import cosine_similarity

        sims = cosine_similarity(
            query_vector.reshape(1, -1),
            self.vectors
        )[0]

        top_indices = np.argsort(sims)[::-1][:top_k]

        return [
            {
                "text": self.chunks[i],
                "score": float(sims[i])
            }
            for i in top_indices
        ]


class ChromaVectorStore:

    def __init__(self, collection_name: str = "policy_clauses"):

        import chromadb

        self.client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add(
        self,
        chunks: list[str],
        vectors: np.ndarray
    ):

        # Clear previous policy data so each analysis
        # works with the current policy document only.
        existing = self.collection.get()

        if existing["ids"]:
            self.collection.delete(
                ids=existing["ids"]
            )

        ids = [
            f"chunk_{i}"
            for i in range(len(chunks))
        ]

        self.collection.add(
            ids=ids,
            embeddings=vectors.tolist(),
            documents=chunks,
        )

    def query(
        self,
        query_vector: np.ndarray,
        top_k: int = TOP_K_MATCHES
    ) -> list[dict]:

        results = self.collection.query(
            query_embeddings=[
                query_vector.tolist()
            ],
            n_results=top_k,
        )

        docs = results["documents"][0]
        distances = results["distances"][0]

        return [
            {
                "text": doc,
                "score": max(0.0, 1.0 - float(dist))
            }
            for doc, dist in zip(docs, distances)
        ]


def get_vector_store():

    if LOCAL_TEST_MODE:
        return LocalVectorStore()

    return ChromaVectorStore()