"""
End-to-end RegTrack pipeline:

old_policy.pdf/.txt + new_circular.pdf/.txt
-> extract text
-> chunk into clauses
-> embed both sets
-> retrieve closest policy clauses
-> reject weak/irrelevant matches
-> run gap analysis only when a relevant policy exists
-> return a structured report
"""

from pdf_parser import extract_text
from chunker import chunk_document
from embeddings import get_embedder
from vector_store import get_vector_store
from gap_analyzer import get_gap_analyzer


# Initial threshold.
#
# This is deliberately conservative because we do NOT want an unrelated
# policy clause to be sent to Gemini and treated as a possible match.
#
# We will tune this after testing on your actual policy documents.
MIN_POLICY_MATCH_SCORE = 0.70

# Retrieve several candidates instead of blindly trusting TOP-1.
RETRIEVAL_K = 5


def run_regtrack_pipeline(
    policy_filepath: str,
    circular_filepath: str
) -> dict:

    # ============================================================
    # 1. Extract text
    # ============================================================

    policy_text = extract_text(policy_filepath)
    circular_text = extract_text(circular_filepath)

    # ============================================================
    # 2. Chunk documents
    # ============================================================

    policy_chunks = chunk_document(policy_text)
    circular_chunks = chunk_document(circular_text)

    if not policy_chunks or not circular_chunks:
        raise ValueError(
            "Chunking produced zero chunks -- check input documents."
        )

    # ============================================================
    # 3. Create embeddings
    # ============================================================

    embedder = get_embedder()

    # TF-IDF needs to be fitted on both documents so they share
    # the same vocabulary.
    if hasattr(embedder, "fit"):
        embedder.fit(policy_chunks + circular_chunks)

    policy_vectors = embedder.encode(policy_chunks)

    # ============================================================
    # 4. Store policy vectors
    # ============================================================

    store = get_vector_store()
    store.add(policy_chunks, policy_vectors)

    # Create analyzer once.
    analyzer = get_gap_analyzer()

    results = []

    # ============================================================
    # 5. Analyze every circular clause
    # ============================================================

    for clause in circular_chunks:

        clause_vector = embedder.encode([clause])[0]

        # Retrieve several possible policy matches.
        matches = store.query(
            clause_vector,
            top_k=RETRIEVAL_K
        )

        # --------------------------------------------------------
        # No policy matches at all
        # --------------------------------------------------------

        if not matches:

            results.append({
                "new_clause": clause[:500],
                "matched_policy_clause": None,
                "match_score": 0.0,
                "status": "no_existing_policy",
                "explanation": (
                    "No existing company policy clause was found "
                    "for this regulatory requirement."
                ),
                "suggested_edit": (
                    "Add a new policy clause covering this requirement."
                ),
            })

            continue

        # --------------------------------------------------------
        # Best candidate
        # --------------------------------------------------------

        best_match = matches[0]

        score = float(best_match.get("score", 0.0))

        # --------------------------------------------------------
        # Relevance gate
        #
        # IMPORTANT:
        # Do NOT call Gemini if the retrieved policy clause is weak.
        # --------------------------------------------------------

        if score < MIN_POLICY_MATCH_SCORE:

            results.append({
                "new_clause": clause[:500],
                "matched_policy_clause": None,
                "match_score": round(score, 3),
                "status": "no_existing_policy",
                "explanation": (
                    "No sufficiently relevant existing policy clause "
                    "was found for this requirement."
                ),
                "suggested_edit": (
                    "Add a new policy clause covering this requirement."
                ),
            })

            continue

        # --------------------------------------------------------
        # Relevant policy found → call Gemini
        # --------------------------------------------------------

        verdict = analyzer.analyze(
            new_clause=clause,
            old_clause=best_match["text"],
            match_score=score,
        )

        results.append({
            "new_clause": clause[:500],
            "matched_policy_clause": best_match["text"][:500],
            "match_score": round(score, 3),
            "status": verdict["status"],
            "explanation": verdict["explanation"],
            "suggested_edit": verdict.get("suggested_edit"),
        })

    # ============================================================
    # 6. Status summary
    # ============================================================

    status_counts = {}

    for result in results:
        status = result["status"]

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

    # ============================================================
    # 7. Final report
    # ============================================================

    return {
        "total_clauses_analyzed": len(results),
        "status_summary": status_counts,
        "results": results,
    }


if __name__ == "__main__":

    import json
    import sys

    policy_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/sample_policy.txt"
    )

    circular_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "data/sample_circular.txt"
    )

    report = run_regtrack_pipeline(
        policy_path,
        circular_path
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        )
    )