"""
Vectorless RAG POC — FastAPI Application
Simple routes for PDF upload, status polling, and chat.
"""

import hashlib
import json
import logging
import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from services import PageIndexService, LLMService, RAGService

logger = logging.getLogger("vectorless.backend")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────

app = FastAPI(title="Vectorless RAG", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (POC only)
CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache.json")
documents: dict = {}  # doc_id → {filename, file_path, tree, status, file_hash, submission_result}
hash_to_doc_id: dict = {}  # file_hash → doc_id
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def load_cache() -> None:
    if not os.path.exists(CACHE_FILE):
        return
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        documents.update(data.get("documents", {}))
        hash_to_doc_id.update(data.get("hash_to_doc_id", {}))
        logger.info("Loaded %d cached docs from %s", len(documents), CACHE_FILE)
    except Exception as e:
        logger.warning("Failed to load cache from %s: %s", CACHE_FILE, e)


def save_cache() -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"documents": documents, "hash_to_doc_id": hash_to_doc_id}, f, indent=2)
        logger.info("Saved cache with %d docs to %s", len(documents), CACHE_FILE)
    except Exception as e:
        logger.exception("Failed to save cache to %s", CACHE_FILE)


def compute_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

# Initialize services
pi_service = PageIndexService()
llm_service = LLMService()
rag_service = RAGService(llm_service)

load_cache()


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    doc_id: str
    query: str


class SourceNode(BaseModel):
    node_id: str
    title: str
    page_index: int | None = None
    text_preview: str


class ChatResponse(BaseModel):
    answer: str
    reasoning: str
    sources: list[SourceNode]


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF and submit to PageIndex for tree generation."""

    logger.info("Received upload request for file=%s", file.filename)

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save file locally
    safe_name = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    logger.info("Saved uploaded file to %s", file_path)

    file_hash = compute_file_hash(file_path)
    if file_hash in hash_to_doc_id:
        existing_doc_id = hash_to_doc_id[file_hash]
        logger.info(
            "Duplicate document upload detected: file_hash=%s existing_doc_id=%s",
            file_hash,
            existing_doc_id,
        )
        os.remove(file_path)
        existing_doc = documents[existing_doc_id]
        return {
            "doc_id": existing_doc_id,
            "filename": file.filename,
            "status": existing_doc["status"],
        }

    # Submit to PageIndex
    try:
        submission_result = pi_service.submit_document(file_path)
        doc_id = submission_result["doc_id"]
    except Exception as e:
        logger.exception("PageIndex submission failed for file=%s", file_path)
        # Clean up file on failure
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"PageIndex submission failed: {str(e)}")

    # Store in memory and persist cache
    documents[doc_id] = {
        "filename": file.filename,
        "file_path": file_path,
        "tree": None,
        "status": "processing",
        "file_hash": file_hash,
        "submission_result": submission_result,
    }
    hash_to_doc_id[file_hash] = doc_id
    save_cache()

    logger.info("Document submitted successfully: doc_id=%s filename=%s", doc_id, file.filename)
    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}


@app.get("/api/status/{doc_id}")
async def get_status(doc_id: str):
    """Poll processing status. Fetches tree when complete."""

    logger.info("Checking status for doc_id=%s", doc_id)

    if doc_id not in documents:
        logger.warning("Unknown doc_id requested: %s", doc_id)
        # Try checking PageIndex directly (for cases where server restarted)
        documents[doc_id] = {
            "filename": "unknown",
            "file_path": None,
            "tree": None,
            "status": "processing",
        }

    doc = documents[doc_id]

    if doc["status"] == "completed" and doc["tree"] is not None:
        logger.info("Returning cached completed status for doc_id=%s", doc_id)
        return {"doc_id": doc_id, "status": "completed", "filename": doc["filename"]}

    # Check with PageIndex
    try:
        status = pi_service.check_status(doc_id)
        if status == "completed":
            tree = pi_service.get_tree(doc_id)
            doc["tree"] = tree
            doc["status"] = "completed"
            save_cache()
            logger.info("Document processing completed for doc_id=%s", doc_id)
            return {"doc_id": doc_id, "status": "completed", "filename": doc["filename"]}
        else:
            logger.info("Document still processing for doc_id=%s", doc_id)
            return {"doc_id": doc_id, "status": "processing", "filename": doc["filename"]}
    except Exception as e:
        logger.exception("Failed to check status for doc_id=%s", doc_id)
        return {"doc_id": doc_id, "status": "processing", "filename": doc["filename"]}


@app.get("/api/tree/{doc_id}")
async def get_tree(doc_id: str):
    """Get the tree structure for a processed document."""

    logger.info("Fetching tree for doc_id=%s", doc_id)

    if doc_id not in documents or documents[doc_id]["tree"] is None:
        logger.warning("Tree requested for missing or incomplete doc_id=%s", doc_id)
        raise HTTPException(status_code=404, detail="Document not found or still processing")

    return {"doc_id": doc_id, "tree": documents[doc_id]["tree"]}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Ask a question about a processed document."""

    logger.info("Chat request for doc_id=%s", request.doc_id)

    doc = documents.get(request.doc_id)

    if not doc:
        logger.warning("Chat request for unknown doc_id=%s", request.doc_id)
        raise HTTPException(status_code=404, detail="Document not found")

    if doc["status"] != "completed" or doc["tree"] is None:
        logger.warning("Chat request for processing document doc_id=%s", request.doc_id)
        raise HTTPException(status_code=400, detail="Document is still processing")

    try:
        result = await rag_service.generate_answer(doc["tree"], request.query)
        logger.info("Chat response generated for doc_id=%s", request.doc_id)
        return ChatResponse(
            answer=result["answer"],
            reasoning=result["reasoning"],
            sources=[SourceNode(**s) for s in result["sources"]],
        )
    except Exception as e:
        logger.exception("RAG pipeline error for doc_id=%s", request.doc_id)
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
