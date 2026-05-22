# from fastapi import APIRouter, UploadFile
# import shutil
# import os

# from app.services.ingestion_service import ingest_documents
# from app.utils.hybrid_retriever import HybridRetriever
# import app.core.state as state

# router = APIRouter()

# UPLOAD_DIR = "data/docs"


# @router.post("/upload")
# async def upload(file: UploadFile):

#     os.makedirs(UPLOAD_DIR, exist_ok=True)

#     file_path = os.path.join(UPLOAD_DIR, file.filename)

#     with open(file_path, "wb") as f:
#         shutil.copyfileobj(file.file, f)

#     print("📄 File saved:", file.filename)

#     # 🔥 BUILD INDEX + RETRIEVER
#     print("⚙️ Running ingestion...")
#     index = ingest_documents(UPLOAD_DIR)

#     print("⚙️ Creating retriever...")
#     state.retriever = HybridRetriever.from_index(index)

#     print("✅ Retriever ready")

#     return {"message": f"{file.filename} uploaded & indexed"}

from fastapi import APIRouter, UploadFile,File
import shutil
import os
import time

from app.services.ingestion_service import ingest_documents
from app.utils.hybrid_retriever import HybridRetriever
import app.core.state as state

router = APIRouter()

UPLOAD_DIR = "data/docs"


@router.post("/upload")
async def upload(file: UploadFile=File(...)):

    print("\n" + "=" * 60)
    print("📤 UPLOAD ENDPOINT HIT")
    print("=" * 60)

    start_time = time.time()

    # =====================================================
    # CREATE DIRECTORY
    # =====================================================

    print("📁 Creating upload directory...")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    print("✅ Upload directory ready")

    # =====================================================
    # SAVE FILE
    # =====================================================

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    print(f"📄 Saving file: {file.filename}")

    with open(file_path, "wb") as f:

        shutil.copyfileobj(file.file, f)

    print("✅ File saved successfully")

    print(f"📍 Saved at: {file_path}")

    # =====================================================
    # VERIFY FILE EXISTS
    # =====================================================

    if os.path.exists(file_path):

        size = os.path.getsize(file_path)

        print(f"✅ File verified ({size} bytes)")

    else:

        print("❌ File NOT found after saving")

        return {
            "error": "File save failed"
        }

    # =====================================================
    # INGESTION
    # =====================================================

    print("\n" + "-" * 50)
    print("⚙️ STARTING INGESTION")
    print("-" * 50)

    ingestion_start = time.time()

    try:

        index = ingest_documents(file_path)

        ingestion_time = round(
            time.time() - ingestion_start,
            2
        )

        print(f"✅ Ingestion completed in {ingestion_time}s")

    except Exception as e:

        print("❌ INGESTION FAILED")
        print(str(e))

        return {
            "error": str(e)
        }

    # =====================================================
    # RETRIEVER
    # =====================================================

    print("\n" + "-" * 50)
    print("🔍 CREATING RETRIEVER")
    print("-" * 50)

    try:

        state.retriever = HybridRetriever.from_index(index)

        print("✅ Retriever created successfully")

    except Exception as e:

        print("❌ RETRIEVER CREATION FAILED")
        print(str(e))

        return {
            "error": str(e)
        }

    # =====================================================
    # COMPLETE
    # =====================================================

    total_time = round(
        time.time() - start_time,
        2
    )

    print("\n🎉 DOCUMENT PIPELINE COMPLETE")

    print(f"⏱ Total upload time: {total_time}s")

    return {
        "message": f"{file.filename} uploaded & indexed",
        "time": total_time
    }