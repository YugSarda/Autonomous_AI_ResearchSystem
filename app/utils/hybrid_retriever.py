import numpy as np
from rank_bm25 import BM25Okapi


# =========================================================
# MMR (MAX MARGINAL RELEVANCE)
# =========================================================

def mmr(doc_embeddings, query_embedding, docs, k=10, lambda_param=0.7):

    print("\n⚙️ Running MMR...")

    selected = []
    candidates = list(range(len(docs)))

    while len(selected) < min(k, len(docs)) and candidates:

        mmr_scores = []

        for i in candidates:

            # ---------------- RELEVANCE ----------------
            relevance = np.dot(query_embedding, doc_embeddings[i])

            # ---------------- DIVERSITY ----------------
            diversity = max(
                [np.dot(doc_embeddings[i], doc_embeddings[j]) for j in selected]
                or [0]
            )

            # ---------------- MMR SCORE ----------------
            score = (
                lambda_param * relevance
                - (1 - lambda_param) * diversity
            )

            mmr_scores.append((i, score))

        best = max(mmr_scores, key=lambda x: x[1])[0]

        selected.append(best)
        candidates.remove(best)

    print(f"✅ MMR selected {len(selected)} diverse docs")

    return [docs[i] for i in selected]


# =========================================================
# HYBRID RETRIEVER
# =========================================================

class HybridRetriever:

    def __init__(self, documents, vector_retriever, embed_model):

        print("\n⚙️ Initializing HybridRetriever...")

        self.docs = documents
        self.vector_retriever = vector_retriever
        self.embed_model = embed_model

        # ---------------- BM25 SETUP ----------------
        tokenized_docs = []

        for doc in documents:

            if hasattr(doc, "text"):
                tokenized_docs.append(doc.text.split())
            else:
                tokenized_docs.append(str(doc).split())

        self.bm25 = BM25Okapi(tokenized_docs)

        print(f"✅ BM25 initialized with {len(documents)} docs")

    # =====================================================
    # CREATE RETRIEVER FROM LLAMAINDEX INDEX
    # =====================================================

    @classmethod
    def from_index(cls, index):

        print("\n⚙️ Building HybridRetriever from index...")

        # ---------------- VECTOR RETRIEVER ----------------
        vector_retriever = index.as_retriever(similarity_top_k=10)

        # ---------------- DOCUMENTS ----------------
        documents = []

        for _, node in index.docstore.docs.items():
            documents.append(node)

        print(f"📄 Loaded {len(documents)} documents")

        # ---------------- EMBEDDING MODEL ----------------
        embed_model = index._embed_model

        print("✅ HybridRetriever ready")

        return cls(
            documents=documents,
            vector_retriever=vector_retriever,
            embed_model=embed_model
        )

    # =====================================================
    # HYBRID RETRIEVAL
    # =====================================================

    def retrieve(self, query: str, k=3):

        print("\n" + "=" * 50)
        print("🔍 HYBRID RETRIEVAL STARTED")
        print("❓ Query:", query)
        print("=" * 50)

        # =================================================
        # VECTOR RETRIEVAL
        # =================================================

        print("\n📌 STEP 1: Vector Retrieval")

        vector_results = self.vector_retriever.retrieve(query)

        print(f"✅ Vector retrieval returned {len(vector_results)} docs")

        # =================================================
        # BM25 RETRIEVAL
        # =================================================

        print("\n📌 STEP 2: BM25 Retrieval")

        bm25_scores = self.bm25.get_scores(query.split())

        bm25_results = sorted(
            zip(self.docs, bm25_scores),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        bm25_docs = [doc for doc, _ in bm25_results]

        print(f"✅ BM25 retrieval returned {len(bm25_docs)} docs")

        # =================================================
        # COMBINE RESULTS
        # =================================================

        print("\n📌 STEP 3: Combining Results")

        combined = []

        # Vector docs
        for doc in vector_results:
            combined.append(doc)

        # BM25 docs
        combined.extend(bm25_docs)

        # Remove duplicates
        unique_docs = []
        seen = set()

        for doc in combined:

            text = doc.text if hasattr(doc, "text") else str(doc)

            if text not in seen:
                seen.add(text)
                unique_docs.append(doc)

        combined = unique_docs

        print(f"✅ Combined unique docs: {len(combined)}")

        # =================================================
        # EMBEDDINGS
        # =================================================

        print("\n📌 STEP 4: Generating Embeddings")

        query_emb = self.embed_model.get_text_embedding(query)

        doc_embs = []

        for doc in combined:

            text = doc.text if hasattr(doc, "text") else str(doc)

            emb = self.embed_model.get_text_embedding(text)

            doc_embs.append(emb)

        print(f"✅ Generated embeddings for {len(doc_embs)} docs")

        # =================================================
        # MMR
        # =================================================

        print("\n📌 STEP 5: Running MMR")

        final_docs = mmr(
            doc_embs,
            query_emb,
            combined,
            k=k
        )

        print(f"✅ Final retrieved docs: {len(final_docs)}")

        print("\n🎉 HYBRID RETRIEVAL COMPLETE")

        return final_docs