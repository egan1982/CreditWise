"""
Workspace Management API for DeepAnalyze API Server
Handles workspace management endpoints for the frontend
"""

import os
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

from storage import storage
from utils import get_thread_workspace

# Create router for workspace endpoints
router = APIRouter(prefix="/v1/workspace", tags=["workspace"])

@router.get("/tree")
async def get_workspace_tree(
    session_id: Optional[str] = Query(None)
):
    """
    Get workspace tree structure
    """
    try:
        if not session_id:
            # Return empty tree if no session
            return {"tree": []}
            
        workspace_dir = storage.get_thread_workspace(session_id)
        if not workspace_dir or not os.path.exists(workspace_dir):
            return {"tree": []}
        
        # Simple tree structure
        tree = []
        
        def build_tree(path, rel_path=""):
            items = []
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    rel_item_path = os.path.join(rel_path, item)
                    
                    if os.path.isfile(item_path):
                        items.append({
                            "name": item,
                            "path": rel_item_path,
                            "type": "file",
                            "size": os.path.getsize(item_path)
                        })
                    elif os.path.isdir(item_path) and not item.startswith('.'):
                        items.append({
                            "name": item,
                            "path": rel_item_path,
                            "type": "directory",
                            "children": build_tree(item_path, rel_item_path)
                        })
            except Exception as e:
                pass
            
            return items
        
        tree = build_tree(workspace_dir)
        return {"tree": tree}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_workspace(
    session_id: Optional[str] = Query(None)
):
    """
    Clear workspace
    """
    try:
        if not session_id:
            return {"success": True, "message": "No session to clear"}
            
        workspace_dir = storage.get_thread_workspace(session_id)
        if workspace_dir and os.path.exists(workspace_dir):
            # Remove all files except keep some structure
            import shutil
            for item in os.listdir(workspace_dir):
                item_path = os.path.join(workspace_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path) and item not in ['generated']:
                    shutil.rmtree(item_path)
        
        return {"success": True, "message": "Workspace cleared"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/file")
async def delete_file(
    path: str = Query(...),
    session_id: Optional[str] = Query(None)
):
    """
    Delete a file in the workspace
    """
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
            
        workspace_dir = storage.get_thread_workspace(session_id)
        if not workspace_dir:
            raise HTTPException(status_code=404, detail="Workspace not found")
            
        file_path = os.path.join(workspace_dir, path)
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="File not found")
            
        os.remove(file_path)
        return {"success": True, "message": "File deleted"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dir")
async def delete_directory(
    path: str = Query(...),
    recursive: bool = Query(False),
    session_id: Optional[str] = Query(None)
):
    """
    Delete a directory in the workspace
    """
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
            
        workspace_dir = storage.get_thread_workspace(session_id)
        if not workspace_dir:
            raise HTTPException(status_code=404, detail="Workspace not found")
            
        dir_path = os.path.join(workspace_dir, path)
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            raise HTTPException(status_code=404, detail="Directory not found")
            
        if recursive:
            import shutil
            shutil.rmtree(dir_path)
        else:
            os.rmdir(dir_path)
            
        return {"success": True, "message": "Directory deleted"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))