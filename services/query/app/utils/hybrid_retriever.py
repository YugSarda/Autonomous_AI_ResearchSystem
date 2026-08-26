"""Hybrid Retriever for Query Service - Builds retriever from ChromaDB vector store."""
import numpy as np
from rank_bm25 import BM25Okapi


def mmr(doc_embeddings, query_embedding, docs, k=10, lambda_param=0.7):
    """Max Marginal Relevance for diverse retrieval."""
    selected = []
    candidates = list(range(len(docs)))

    while len(selected) < min(k, len(docs)) and candidates:
        mmr_scores = []
        for i in candidates:
            relevance = np.dot(query_embedding, doc_embeddings[i])
            diversity = max(
                [np.dot(doc_embeddings[i], doc_embeddings[j]) for j in selected]
                or [0]
            )
            score = lambda_param * relevance - (1 - lambda_param) * diversity
            mmr_scores.append((i, score))

        best = max(mmr_scores, key=lambda x: x[1])[0]
        selected.append(best)
        candidates.remove(best)

    return [docs[i] for i in selected]


class HybridRetriever:

    def __init__(self, documents, vector_retriever, embed_model):
        self.docs = documents
        self.vector_retriever = vector_retriever
        self.embed_model = embed_model

        tokenized_docs = []
        for doc in documents:
            if hasattr(doc, "text"):
                tokenized_docs.append(doc.text.split())
            else:
                tokenized_docs.append(str(doc).split())
        self.bm25 = BM25Okapi(tokenized_docs)

    @classmethod
    def from_index(cls, index):
        """Build a HybridRetriever from a LlamaIndex VectorStoreIndex."""
        vector_retriever = index.as_retriever(similarity_top_k=10)
        documents = []
        for _, node in index.docstore.docs.items():
            documents.append(node)
        embed_model = index._embed_model
        return cls(
            documents=documents,
            vector_retriever=vector_retriever,
            embed_model=embed_model
        )

    def retrieve(self, query: str, k=3):
        """Hybrid retrieval using vector + BM25 + MMR."""
        vector_results = self.vector_retriever.retrieve(query)

        bm25_scores = self.bm25.get_scores(query.split())
        bm25_results = sorted(
            zip(self.docs, bm25_scores),
            key=lambda x: x[1],
            reverse=True
        )[:k]
        bm25_docs = [doc for doc, _ in bm25_results]

        combined = list(vector_results)
        combined.extend(bm25_docs)

        unique_docs = []
        seen = set()
        for doc in combined:
            text = doc.text if hasattr(doc, "text") else str(doc)
            if text not in seen:
                seen.add(text)
                unique_docs.append(doc)
        combined = unique_docs

        query_emb = self.embed_model.get_text_embedding(query)
        doc_embs = []
        for doc in combined:
            if hasattr(doc, "embedding") and doc.embedding is not None:
                emb = doc.embedding
            else:
                text = doc.text if hasattr(doc, "text") else str(doc)
                emb = self.embed_model.get_text_embedding(text)
            doc_embs.append(emb)

        final_docs = mmr(doc_embs, query_emb, combined, k=k)
        return final_docs