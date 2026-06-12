from app.services.query_pipeline import run_query_pipeline
import numpy as np


def retrieve(sub_query, retriever, test_mode: bool = True):
    """
    Retrieve documents for a sub-query, with confidence score.
    
    Returns:
        dict with keys: query, answer, docs, confidence
    """
    answer, docs = run_query_pipeline(sub_query, retriever, test_mode=test_mode)

    # Compute confidence score from doc similarity scores
    confidence = _compute_confidence(docs)

    return {
        "query": sub_query,
        "answer": answer,
        "docs": docs,
        "confidence": confidence,
    }


def _compute_confidence(docs) -> float:
    """
    Compute a confidence score (0-1) from retrieved document scores.
    
    Uses average of available scores. Falls back to 0.5 if no scores present.
    """
    if not docs:
        return 0.0

    scores = []
    for doc in docs:
        # LlamaIndex nodes have .score attribute
        if hasattr(doc, "score") and doc.score is not None:
            scores.append(doc.score)
        # Also check nested node
        elif hasattr(doc, "node") and hasattr(doc.node, "score") and doc.node.score is not None:
            scores.append(doc.node.score)

    if not scores:
        return 0.5  # Neutral fallback

    # Clamp to [0, 1]
    avg = float(np.mean(scores))
    return max(0.0, min(1.0, avg))