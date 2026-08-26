"""Query Service State - Builds retriever from ChromaDB on demand."""
import os
import time

retriever = None
_last_build_time = 0
_BUILD_COOLDOWN = 5  # seconds


def _build_retriever_from_chroma():
    """Build a retriever from ChromaDB vector store.

    Hydrates the full document corpus (text + precomputed embeddings) back
    into LlamaIndex nodes so the HybridRetriever can power both the BM25
    keyword half and the MMR diversity half of retrieval.
    """
    global retriever, _last_build_time

    from app.core.config import VECTOR_DB_PATH, EMBED_MODEL
    from llama_index.core import Settings
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.core import VectorStoreIndex
    from llama_index.core.schema import TextNode
    import chromadb

    # Check if ChromaDB has any data
    chroma_path = VECTOR_DB_PATH
    if not os.path.exists(chroma_path):
        print("⚠️ ChromaDB path does not exist yet")
        return None

    try:
        print("🔍 Building retriever from ChromaDB...")
        start = time.time()

        # Set embedding model
        Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

        # Connect to ChromaDB
        chroma_client = chromadb.PersistentClient(path=chroma_path)
        collection = chroma_client.get_collection("docs")

        # Check if collection has any items
        if collection.count() == 0:
            print("⚠️ ChromaDB collection is empty")
            return None

        vector_store = ChromaVectorStore(chroma_collection=collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        vector_retriever = index.as_retriever(similarity_top_k=10)

        # Pull the full corpus back out of Chroma so BM25 + MMR operate on
        # the same nodes that the ingestion service wrote.
        data = collection.get(include=["documents", "metadatas", "embeddings"])
        texts = data.get("documents") or []
        metadatas = data.get("metadatas") or []
        ids = data.get("ids") or []
        # Note: chromadb returns embeddings as a numpy ndarray — do NOT use
        # `or []` on it (ambiguous truth value), and normalize rows to lists.
        embeddings = data.get("embeddings")
        if embeddings is None:
            embeddings = []
        else:
            embeddings = [list(e) for e in embeddings]

        nodes = []
        for i, text in enumerate(texts):
            node = TextNode(
                text=text,
                metadata=metadatas[i] if i < len(metadatas) else {},
                node_id=ids[i] if i < len(ids) else f"node_{i}",
            )
            if i < len(embeddings) and embeddings[i] is not None:
                node.embedding = embeddings[i]
            nodes.append(node)

        if not nodes:
            print("⚠️ No document nodes recovered from ChromaDB")
            return None

        from app.utils.hybrid_retriever import HybridRetriever
        retriever = HybridRetriever(
            documents=nodes,
            vector_retriever=vector_retriever,
            embed_model=Settings.embed_model,
        )

        elapsed = time.time() - start
        print(f"✅ Retriever built from ChromaDB in {elapsed:.2f}s ({len(nodes)} nodes)")
        return retriever

    except Exception as e:
        print(f"⚠️ Failed to build retriever from ChromaDB: {e}")
        return None


def ensure_retriever():
    """Ensure a retriever is available, building one if needed."""
    global retriever, _last_build_time

    if retriever is not None:
        return retriever

    # Cooldown check - don't rebuild more often than every N seconds
    now = time.time()
    if now - _last_build_time < _BUILD_COOLDOWN:
        return None

    _last_build_time = now
    retriever = _build_retriever_from_chroma()
    return retriever