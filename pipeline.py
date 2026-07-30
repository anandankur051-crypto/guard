"""
End-to-end RegTrack pipeline:

old_policy.pdf/.txt + new_circular.pdf/.txt
        -> extract text
        -> chunk into clauses
        -> embed both sets
        -> for each new-circular clause, retrieve closest old-policy clause
        -> run gap analysis (LLM or mock)
        -> return a structured report
"""

from pdf_parser import extract_text
from chunker import chunk_document
from embeddings import get_embedder
from vector_store import get_vector_store
from gap_analyzer import get_gap_analyzer


def run_regtrack_pipeline(policy_filepath: str, circular_filepath: str) -> dict:
    # 1. Extract raw text
    policy_text = extract_text(policy_filepath)
    circular_text = extract_text(circular_filepath)

    # 2. Chunk into clauses
    policy_chunks = chunk_document(policy_text)
    circular_chunks = chunk_document(circular_text)

    if not policy_chunks or not circular_chunks:
        raise ValueError("Chunking produced zero chunks -- check input documents.")

    # 3. Embed
    embedder = get_embedder()
    # fit TF-IDF (if in local mode) on the combined vocabulary so both
    # documents share the same vector space
    if hasattr(embedder, "fit"):
        embedder.fit(policy_chunks + circular_chunks)

    policy_vectors = embedder.encode(policy_chunks)

    # 4. Store policy vectors
    store = get_vector_store()
    store.add(policy_chunks, policy_vectors)

    # 5. For each circular clause, retrieve + analyze
    analyzer = get_gap_analyzer()
    results = []

    for clause in circular_chunks:
        clause_vector = embedder.encode([clause])[0]
        matches = store.query(clause_vector, top_k=1)
        best_match = matches[0] if matches else {"text": "", "score": 0.0}

        verdict = analyzer.analyze(
            new_clause=clause,
            old_clause=best_match["text"],
            match_score=best_match["score"],
        )

        results.append({
            "new_clause": clause[:300],
            "matched_policy_clause": best_match["text"][:300],
            "match_score": round(best_match["score"], 3),
            "status": verdict["status"],
            "explanation": verdict["explanation"],
            "suggested_edit": verdict.get("suggested_edit"),
        })

    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    return {
        "total_clauses_analyzed": len(results),
        "status_summary": status_counts,
        "results": results,
    }


if __name__ == "__main__":
    import json
    import sys

    policy_path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_policy.txt"
    circular_path = sys.argv[2] if len(sys.argv) > 2 else "data/sample_circular.txt"

    report = run_regtrack_pipeline(policy_path, circular_path)
    print(json.dumps(report, indent=2))
