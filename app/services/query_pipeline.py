# from collections import defaultdict
# from app.services.retrieval_service import multi_query_expansion
# from app.services.reranker_service import rerank
# from app.services.web_search import search_web
# from app.core.ollama_client import generate


# # def rag_fusion(all_results):
# #     scores = defaultdict(float)

# #     for docs in all_results:
# #         for rank, doc in enumerate(docs):
# #             scores[doc.text] += 1 / (rank + 1)

# #     ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

# #     unique_docs = {}
# #     for docs in all_results:
# #         for doc in docs:
# #             unique_docs[doc.text] = doc

# #     return [unique_docs[text] for text, _ in ranked]


# def run_query_pipeline(query, retriever):
#     # print("🔹 Multi-query expansion...")

#     # queries = multi_query_expansion(query)
#     queries = [query]
#     print("🔹 Hybrid retrieval...")
#     results_per_query = []
#     for q in queries:
#         docs = retriever.retrieve(q, k=3)
#         results_per_query.append(docs)
#     # print("🔹 RAG fusion...")
#     # fused_docs = rag_fusion(results_per_query)

#     # 🌐 Web Search Integration
#     web_results = search_web(query)

#     class WebDoc:
#         def __init__(self, text):
#             self.text = text
#             self.metadata = {"source": "web"}

#     web_docs = [WebDoc(w) for w in web_results]
#     fused_docs.extend(web_docs)
#     print("🔹 Reranking...")
#     top_docs = rerank(query, fused_docs[:20])
#     context = "\n\n".join(
#     [
#         doc.text if hasattr(doc, "text")
#         else str(doc)
#         for doc in top_docs
#     ]
# )

#     final_prompt = f"""
# STRICT RULES:
# - Answer ONLY from context
# - If not found, say "Not enough information"
# - Provide citations

# Context:
# {context}

# Question:
# {query}
# """
#     print("🔹 Final answer generation...")
#     answer = generate(final_prompt)

#     return answer, top_docs

from app.services.reranker_service import rerank
from app.services.web_search import search_web
from app.core.ollama_client import generate


def run_query_pipeline(query, retriever):

    # =====================================================
    # RETRIEVAL
    # =====================================================

    print("🔹 Hybrid retrieval...")

    docs = retriever.retrieve(query, k=3)

    fused_docs = docs

    # =====================================================
    # WEB SEARCH
    # =====================================================

    print("🌐 Running web search...")

    web_results = search_web(query)

    class WebDoc:

        def __init__(self, text):

            self.text = text
            self.metadata = {
                "source": "web"
            }

    web_docs = [WebDoc(w) for w in web_results]

    fused_docs.extend(web_docs)

    print(f"✅ Total docs after web merge: {len(fused_docs)}")

    # =====================================================
    # RERANKING
    # =====================================================

    print("🔹 Reranking...")

    top_docs = rerank(
        query,
        fused_docs[:5]
    )

    print(f"✅ Top docs selected: {len(top_docs)}")

    # =====================================================
    # CONTEXT BUILDING
    # =====================================================

    print("📄 Preparing context...")

    context_chunks = []

    for doc in top_docs:

        if hasattr(doc, "text"):

            context_chunks.append(doc.text)

        elif hasattr(doc, "node"):

            context_chunks.append(doc.node.text)

        else:

            context_chunks.append(str(doc))

    context = "\n\n".join(context_chunks)

    print("✅ Context prepared")

    # =====================================================
    # FINAL PROMPT
    # =====================================================

    final_prompt = f"""
STRICT RULES:
- Answer ONLY from context
- If information is missing, say "Not enough information"
- Do NOT hallucinate
- Provide concise grounded answers

Context:
{context}

Question:
{query}
"""

    # =====================================================
    # GENERATION (skipped — synthesizer handles this)
    # =====================================================

    print("⏭️ Skipping per-query generation (synthesizer will handle)")

    return "", top_docs
