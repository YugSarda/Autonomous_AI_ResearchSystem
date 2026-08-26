"""Reranker Service - Cross-encoder re-ranking of retrieval candidates."""
from sentence_transformers import CrossEncoder

RERANKER_MODEL = "BAAI/bge-reranker-base"

_model = None


def _get_model():
    """Get (and lazily load) the singleton cross-encoder model."""
    global _model
    if _model is None:
        print(f"Loading reranker model ({RERANKER_MODEL})...")
        _model = CrossEncoder(RERANKER_MODEL)
    return _model


def rerank(query, docs, top_n: int = 3):
    """Re-rank docs by cross-encoder relevance to the query.

    Args:
        query: The query text.
        docs: Candidate documents (LlamaIndex nodes or doc-like objects).
        top_n: How many documents to keep.

    Returns:
        List of the top `top_n` documents, best-first.
    """
    print("Reranking...")
    model = _get_model()

    pairs = []
    for doc in docs:
        text = doc.text if hasattr(doc, "text") else str(doc)
        pairs.append((query, text))

    if not pairs:
        return []

    scores = model.predict(pairs)
    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    final_docs = [doc for doc, _ in ranked[:top_n]]
    print(f"Reranking complete — kept top {len(final_docs)}")
    return final_docs