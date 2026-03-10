"""
[ARCHIVED] File Management API for DeepAnalyze API Server
Handles file upload, download, and management endpoints

NOTE: This router is NOT registered in create_app() and has no effect at runtime.
      Workspace file operations are served by inline routes in API/main.py (/workspace/*).
      The OpenAI-compatible /v1/files/* endpoints here were never deployed.
      See docs/routing_architecture_guide.md for the authoritative route map.
      Retained for reference only — do not import or register without review.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from config import VALID_FILE_PURPOSES, FILE_STORAGE_DIR
from models import FileObject, FileDeleteResponse
from storage import storage
from utils import get_thread_workspace, validate_session_id, check_upload_size


# Create router for file endpoints
router = APIRouter(prefix="/v1/files", tags=["files"])


@router.post("", response_model=FileObject)
async def create_file(
    file: UploadFile = File(...),
    purpose: str = Form("file-extract")
):
    """Upload a file (OpenAI compatible)"""
    # Validate purpose
    if purpose not in VALID_FILE_PURPOSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid purpose. Must be one of {VALID_FILE_PURPOSES}"
        )

    # Save file to a persistent location
    os.makedirs(FILE_STORAGE_DIR, exist_ok=True)
    file_id = f"file-{file.filename.replace('.', '-').replace('_', '-')[:8]}-{os.urandom(4).hex()}"
    file_path = os.path.join(FILE_STORAGE_DIR, file_id)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            check_upload_size(content, file.filename or "file")  # P1-D1: 文件大小限制
            f.write(content)

        file_obj = storage.create_file(file.filename, file_path, purpose)
        return file_obj
    except Exception as e:
        # Clean up file if creation failed
        if os.path.exists(file_path):
            os.remove(file_path)
        import logging
        logging.getLogger(__name__).error(f"Failed to create file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create file")


@router.post("/upload-to")
async def upload_file_to_workspace(
    files: list[UploadFile] = File(...),
    dir: str = Form(""),
    session_id: str = Form(...)
):
    """Upload files to a specific workspace"""
    try:
        session_id = validate_session_id(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    try:
        # Get workspace directory
        workspace_dir = get_thread_workspace(session_id)
        abs_workspace = Path(workspace_dir).resolve()
        
        # Create target directory if specified, with path traversal protection (P1-D2)
        if dir:
            target_dir = (abs_workspace / dir).resolve()
            if abs_workspace not in target_dir.parents and target_dir != abs_workspace:
                raise HTTPException(status_code=400, detail="Invalid dir path")
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = abs_workspace
        
        uploaded_files = []
        
        for file in files:
            # Sanitize filename: use only basename to prevent path traversal via filename
            safe_name = Path(file.filename).name if file.filename else "unnamed"
            file_path = os.path.join(str(target_dir), safe_name)
            with open(file_path, "wb") as f:
                content = await file.read()
                check_upload_size(content, safe_name)  # P1-D1: 文件大小限制
                f.write(content)
            
            uploaded_files.append({
                "filename": safe_name,
                "path": os.path.join(dir, safe_name) if dir else safe_name,
                "size": os.path.getsize(file_path)
            })
        
        return {"files": uploaded_files}
    
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to upload file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.get("", response_model=dict)
async def list_files(purpose: Optional[str] = Query(None)):
    """List files (OpenAI compatible)"""
    files = storage.list_files(purpose=purpose)
    return {"object": "list", "data": [f.dict() for f in files]}


@router.get("/{file_id}", response_model=FileObject)
async def retrieve_file(file_id: str):
    """Retrieve file metadata (OpenAI compatible)"""
    file_obj = storage.get_file(file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    return file_obj


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(file_id: str):
    """Delete a file (OpenAI compatible)"""
    success = storage.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return FileDeleteResponse(id=file_id, object="file", deleted=True)


@router.get("/{file_id}/content")
async def download_file(file_id: str):
    """Download file content (OpenAI compatible)"""
    file_obj = storage.get_file(file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    filepath = storage.files[file_id].get("filepath")
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File content not found")

    with open(filepath, "rb") as f:
        content = f.read()

    return Response(content=content, media_type="application/octet-stream")