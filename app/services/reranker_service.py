from sentence_transformers import CrossEncoder

_model = None

def _get_model():
    global _model
    if _model is None:
        print("Loading reranker model...")
        _model = CrossEncoder("BAAI/bge-reranker-base")
    return _model


def rerank(query, docs):

    print("🔹 Reranking...")

    model = _get_model()

    pairs = []

    for doc in docs:

        text = doc.text if hasattr(doc, "text") else str(doc)

        pairs.append((query, text))

    scores = model.predict(pairs)

    ranked = list(zip(docs, scores))

    ranked.sort(
        key=lambda x: x[1],
        reverse=True
    )

    # ✅ RETURN ONLY TOP 2
    final_docs = [doc for doc, _ in ranked[:2]]

    print("✅ Reranking complete")

    return final_docs
