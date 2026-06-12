# =============================================================================
# ORIGINAL FULL PIPELINE (with web search + reranker)
# Uncomment these imports and the full run_query_pipeline below when you want
# the complete production pipeline with web search and reranking.
# =============================================================================
# from app.services.reranker_service import rerank
# from app.services.web_search import search_web
# from app.core.ollama_client import generate
#
#
# def run_query_pipeline(query, retriever):
#
#     # =====================================================
#     # RETRIEVAL
#     # =====================================================
#
#     print("🔹 Hybrid retrieval...")
#
#     docs = retriever.retrieve(query, k=3)
#
#     fused_docs = docs
#
#     # =====================================================
#     # WEB SEARCH
#     # =====================================================
#
#     print("🌐 Running web search...")
#
#     web_results = search_web(query)
#
#     class WebDoc:
#
#         def __init__(self, text):
#
#             self.text = text
#             self.metadata = {
#                 "source": "web"
#             }
#
#     web_docs = [WebDoc(w) for w in web_results]
#
#     fused_docs.extend(web_docs)
#
#     print(f"✅ Total docs after web merge: {len(fused_docs)}")
#
#     # =====================================================
#     # RERANKING
#     # =====================================================
#
#     print("🔹 Reranking...")
#
#     top_docs = rerank(
#         query,
#         fused_docs[:5]
#     )
#
#     print(f"✅ Top docs selected: {len(top_docs)}")
#
#     # =====================================================
#     # CONTEXT BUILDING
#     # =====================================================
#
#     print("📄 Preparing context...")
#
#     context_chunks = []
#
#     for doc in top_docs:
#
#         if hasattr(doc, "text"):
#
#             context_chunks.append(doc.text)
#
#         elif hasattr(doc, "node"):
#
#             context_chunks.append(doc.node.text)
#
#         else:
#
#             context_chunks.append(str(doc))
#
#     context = "\n\n".join(context_chunks)
#
#     print("✅ Context prepared")
#
#     # =====================================================
#     # FINAL PROMPT
#     # =====================================================
#
#     final_prompt = f"""
# STRICT RULES:
# - Answer ONLY from context
# - If information is missing, say "Not enough information"
# - Do NOT hallucinate
# - Provide concise grounded answers
#
# Context:
# {context}
#
# Question:
# {query}
# """
#
#     # =====================================================
#     # GENERATION (skipped — synthesizer handles this)
#     # =====================================================
#
#     print("⏭️ Skipping per-query generation (synthesizer will handle)")
#
#     return "", top_docs


# =============================================================================
# TEST MODE PIPELINE (fast, skips web search + reranker)
# =============================================================================

def run_query_pipeline(query, retriever, test_mode: bool = True):
    """
    Run the retrieval pipeline.

    In test_mode=True:
        - Only does hybrid retrieval (vector + BM25 + MMR)
        - Skips web search and reranker for speed
        - Returns top k=2 docs

    In test_mode=False:
        - Full pipeline with web search + reranker
        - (Uncomment the original code above and use that instead)
    """

    # =====================================================
    # HYBRID RETRIEVAL
    # =====================================================

    print("🔹 Hybrid retrieval...")

    # Use k=2 in test mode for speed, k=3 in full mode
    k = 2 if test_mode else 3
    docs = retriever.retrieve(query, k=k)

    fused_docs = docs

    # =====================================================
    # WEB SEARCH (skipped in test mode)
    # =====================================================

    # 🌐 Web Search Integration
    # Uncomment this block when running in full production mode:
    #
    # if not test_mode:
    #     print("🌐 Running web search...")
    #     from app.services.web_search import search_web
    #     web_results = search_web(query)
    #
    #     class WebDoc:
    #         def __init__(self, text):
    #             self.text = text
    #             self.metadata = {"source": "web"}
    #
    #     web_docs = [WebDoc(w) for w in web_results]
    #     fused_docs.extend(web_docs)
    #     print(f"✅ Total docs after web merge: {len(fused_docs)}")

    if not test_mode:
        print("🌐 Running web search...")
        from app.services.web_search import search_web
        web_results = search_web(query)

        class WebDoc:
            def __init__(self, text):
                self.text = text
                self.metadata = {"source": "web"}

        web_docs = [WebDoc(w) for w in web_results]
        fused_docs.extend(web_docs)
        print(f"✅ Total docs after web merge: {len(fused_docs)}")

    # =====================================================
    # RERANKING (skipped in test mode)
    # =====================================================

    # 🔹 Reranking
    # Uncomment this block when running in full production mode:
    #
    # if not test_mode:
    #     print("🔹 Reranking...")
    #     from app.services.reranker_service import rerank
    #     top_docs = rerank(query, fused_docs[:5])
    #     print(f"✅ Top docs selected: {len(top_docs)}")
    # else:
    #     top_docs = fused_docs

    if not test_mode:
        print("🔹 Reranking...")
        from app.services.reranker_service import rerank
        top_docs = rerank(query, fused_docs[:5])
        print(f"✅ Top docs selected: {len(top_docs)}")
    else:
        top_docs = fused_docs

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
    # GENERATION (skipped — synthesizer handles this)
    # =====================================================

    print("⏭️ Skipping per-query generation (synthesizer will handle)")

    return "", top_docs
