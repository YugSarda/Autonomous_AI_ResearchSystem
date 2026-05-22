# from llama_index.core import VectorStoreIndex, Settings, SimpleDirectoryReader
# from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# from llama_index.vector_stores.chroma import ChromaVectorStore
# import chromadb
# import uuid

# from app.core.config import EMBED_MODEL, VECTOR_DB_PATH


# def ingest_documents(doc_path: str):

#     Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

#     chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
#     collection = chroma_client.get_or_create_collection("docs")

#     vector_store = ChromaVectorStore(chroma_collection=collection)

#     documents = SimpleDirectoryReader(doc_path).load_data()

#     for doc in documents:
#         doc.metadata["doc_id"] = str(uuid.uuid4())

#     index = VectorStoreIndex.from_documents(
#         documents,
#         vector_store=vector_store
#     )

#     return index

import os
from llama_index.core import (
    VectorStoreIndex,
    Settings,
    SimpleDirectoryReader
)
from llama_index.readers.file import PDFReader

from llama_index.core.node_parser import (
    SentenceSplitter
)

from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding
)

from llama_index.vector_stores.chroma import (
    ChromaVectorStore
)

import chromadb
import uuid
import time

from app.core.config import (
    EMBED_MODEL,
    VECTOR_DB_PATH
)


def ingest_documents(doc_path: str):

    print("\n" + "=" * 60)
    print("📥 INGESTION PIPELINE STARTED")
    print("=" * 60)

    total_start = time.time()

    # =====================================================
    # EMBEDDING MODEL
    # =====================================================

    print("🧠 Loading embedding model...")

    Settings.embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL
    )

    print("✅ Embedding model loaded")

    # =====================================================
    # CHROMA DB
    # =====================================================

    print("\n📦 Initializing ChromaDB...")

    chroma_client = chromadb.PersistentClient(
        path=VECTOR_DB_PATH
    )

    collection = chroma_client.get_or_create_collection(
        "docs"
    )

    vector_store = ChromaVectorStore(
        chroma_collection=collection
    )

    print("✅ ChromaDB initialized")

    # =====================================================
    # LOAD DOCUMENTS (single file or entire directory)
    # =====================================================

    print("\n📄 Loading documents...")

    if os.path.isfile(doc_path):
        # Load just the single uploaded file
        documents = SimpleDirectoryReader(
            input_files=[doc_path],
            file_extractor={".pdf": PDFReader()}
        ).load_data()
    else:
        # Load all files in directory
        documents = SimpleDirectoryReader(
            doc_path
        ).load_data()

    print(f"✅ Loaded {len(documents)} documents")

    # =====================================================
    # CHUNKING
    # =====================================================

    print("\n✂️ Chunking documents...")

    splitter = SentenceSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    nodes = splitter.get_nodes_from_documents(
        documents
    )

    print(f"✅ Total chunks created: {len(nodes)}")


    print("\n🏷️ Adding metadata...")

    for node in nodes:

        node.metadata["doc_id"] = str(uuid.uuid4())

    print("✅ Metadata added")

    # =====================================================
    # VECTOR INDEX
    # =====================================================

    print("\n⚙️ Building vector index...")

    index_start = time.time()

    index = VectorStoreIndex(
        nodes,
        vector_store=vector_store
    )

    index_time = round(
        time.time() - index_start,
        2
    )

    print(f"✅ Vector index built in {index_time}s")

    # =====================================================
    # COMPLETE
    # =====================================================

    total_time = round(
        time.time() - total_start,
        2
    )

    print("\n🎉 INGESTION COMPLETE")

    print(f"⏱ Total ingestion time: {total_time}s")

    return index