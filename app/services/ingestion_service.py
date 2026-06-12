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
from typing import List
from llama_index.core import (
    VectorStoreIndex,
    Settings,
    SimpleDirectoryReader,
    Document as LlamaDocument,
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
from app.services.table_processor import process_table_file, is_table_file


# =====================================================
# FILE DETECTION
# =====================================================

def load_content(file_path: str) -> List[LlamaDocument]:
    """Load content from any supported file type (PDFs, CSVs, Excel, text)."""
    ext = os.path.splitext(file_path)[1].lower()
    print(f"\n📂 Processing file: {os.path.basename(file_path)} ({ext})")

    # --- Table files (CSV, Excel) ---
    if is_table_file(file_path):
        print("📊 Detected table file")
        text_content = process_table_file(file_path)
        doc = LlamaDocument(
            text=text_content,
            metadata={
                "source": file_path,
                "file_type": "table",
                "doc_id": str(uuid.uuid4()),
            }
        )
        return [doc]

    # --- PDFs (load normally, also extract tables) ---
    if ext == ".pdf":
        documents = SimpleDirectoryReader(
            input_files=[file_path],
            file_extractor={".pdf": PDFReader()}
        ).load_data()

        # Also extract tables from PDF
        try:
            table_text = process_table_file(file_path)
            if table_text and "No tables found" not in table_text:
                table_doc = LlamaDocument(
                    text=table_text,
                    metadata={
                        "source": file_path,
                        "file_type": "table_from_pdf",
                        "doc_id": str(uuid.uuid4()),
                    }
                )
                documents.append(table_doc)
                print("✅ Tables extracted from PDF")
        except Exception as e:
            print(f"⚠️ Table extraction from PDF skipped: {e}")

        return documents

    # --- Text files ---
    print("📄 Detected text file")
    documents = SimpleDirectoryReader(
        input_files=[file_path],
    ).load_data()
    return documents


def ingest_documents(doc_path: str):

    print("\n" + "=" * 60)
    print("📥 MULTIMODAL INGESTION PIPELINE STARTED")
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
    # LOAD DOCUMENTS (multimodal-aware)
    # =====================================================

    print("\n📄 Loading documents...")

    documents = []

    if os.path.isfile(doc_path):
        # Single file - route through content loader
        documents = load_content(doc_path)
    else:
        # Directory - load each file with appropriate handler
        for root, _, files in os.walk(doc_path):
            for filename in sorted(files):
                filepath = os.path.join(root, filename)
                try:
                    docs = load_content(filepath)
                    documents.extend(docs)
                except Exception as e:
                    print(f"⚠️ Skipping {filename}: {e}")

    print(f"✅ Loaded {len(documents)} document chunks")

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