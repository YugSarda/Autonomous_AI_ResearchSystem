def verify_citations(answer, docs):

    citation_texts = []

    for i, doc in enumerate(docs):
        text = doc.text if hasattr(doc, "text") else str(doc)
        snippet = text[:100].strip()
        if len(text) > 100:
            snippet += "..."
        citation_texts.append(f"[Source {i+1}]: {snippet}")

    if citation_texts:
        return answer + "\n\n---\n" + "\n".join(citation_texts)

    return answer
