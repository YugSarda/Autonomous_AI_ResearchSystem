from fastapi import APIRouter, UploadFile, File
import os
import shutil
import time
import uuid

from app.services.async_ingestion import enqueue_ingestion
from app.core.task_store import get_task, get_all_tasks
from app.utils.storage import upload_document

router = APIRouter()

UPLOAD_DIR = "data/docs"

ALLOWED_EXTENSIONS = {
    ".pdf", ".txt", ".csv", ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif",
}


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Save the file locally + to MinIO, enqueue async ingestion, return task_id immediately.

    Every upload now uses the async path (Redis Streams) — no synchronous
    ingest in the request handler.
    """
    start = time.time()

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {
            "error": f"Unsupported file type: {ext or 'none'}",
            "allowed": sorted(ALLOWED_EXTENSIONS),
        }

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Durable copy in object storage (MinIO, S3-compatible)
    object_name = (
        f"{int(time.time())}_{uuid.uuid4().hex[:8]}/"
        f"{os.path.basename(file.filename)}"
    )
    storage_key = upload_document(file_path, object_name)

    # Push to the Redis Stream task queue — worker ingests in background
    task_id = await enqueue_ingestion(file_path)

    print(f"File saved & enqueued: {file.filename} (task_id={task_id})")

    return {
        "message": f"{file.filename} saved, ingestion in progress",
        "task_id": task_id,
        "status": "pending",
        "async": True,
        "storage_key": storage_key,
        "time": round(time.time() - start, 2),
    }


@router.get("/upload/status")
async def upload_status():
    """List uploaded files and recent ingestion tasks."""
    uploaded_files = []
    if os.path.exists(UPLOAD_DIR):
        uploaded_files = [
            f for f in os.listdir(UPLOAD_DIR)
            if os.path.isfile(os.path.join(UPLOAD_DIR, f))
        ]

    recent_tasks = await get_all_tasks(limit=10)

    return {
        "retriever_ready": len(uploaded_files) > 0,
        "uploaded_files": uploaded_files,
        "file_count": len(uploaded_files),
        "recent_tasks": recent_tasks,
    }


@router.get("/upload/status/{task_id}")
async def upload_task_status(task_id: str):
    """Get the status of an async ingestion task."""
    task = await get_task(task_id)
    if task is None:
        return {"error": "Task not found", "task_id": task_id}

    return {
        "task_id": task["task_id"],
        "filename": task["filename"],
        "status": task["status"],
        "message": task["message"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
        "completed_at": task["completed_at"],
    }


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "ingestion"}