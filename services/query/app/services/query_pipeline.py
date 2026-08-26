"""Query Pipeline - Hybrid retrieval + cross-encoder re-ranking.

Stage 1: Hybrid retrieval — semantic (vector) + BM25 (keyword) -> MMR diversity
Stage 2: Cross-encoder re-ranking (BGE) over the candidates.
"""
from app.services.reranker_service import rerank

# Number of candidates pulled by the hybrid retriever
CANDIDATE_K = 4
# Number kept after cross-encoder reranking
FINAL_K = 2


def run_query_pipeline(query, retriever):
    """Run retrieval + reranking for a query.

    Args:
        query: The sub-query to retrieve for.
        retriever: HybridRetriever instance (vector + BM25 + MMR).

    Returns:
        (context_summary, top_docs) — tuple shape kept for compatibility.
    """
    print("Hybrid retrieval (semantic + BM25 + MMR)...")
    candidates = retriever.retrieve(query, k=CANDIDATE_K)
    print(f"Hybrid candidates: {len(candidates)}")

    print("Cross-encoder reranking...")
    top_docs = rerank(query, candidates, top_n=FINAL_K)
    print(f"Reranked top docs: {len(top_docs)}")

    return "", top_docs