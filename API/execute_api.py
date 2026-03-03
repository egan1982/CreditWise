"""
Code Execution API for DeepAnalyze API Server
Handles code execution endpoints for the frontend
"""

import os
import json
import sys
import io
import contextlib
import traceback
import subprocess
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from storage import storage
from utils import get_thread_workspace

# Create router for code execution endpoints
router = APIRouter(prefix="/v1", tags=["execute"])

class CodeExecutionRequest(BaseModel):
    code: str
    session_id: str = None
    timeout: int = 30

class CodeExecutionResponse(BaseModel):
    success: bool
    output: str = ""
    error: str = ""

@router.post("/execute")
async def execute_code(request: CodeExecutionRequest):
    """
    Execute Python code and return the output
    """
    try:
        # Get workspace directory
        workspace_dir = get_thread_workspace(request.session_id) if request.session_id else "workspace"
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Prepare code execution context
        context = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }
        
        # Change to workspace directory
        original_cwd = os.getcwd()
        os.chdir(workspace_dir)
        
        try:
            # Execute the code with captured output
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(request.code, context)
            
            # Get the output
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # Combine stdout and stderr
            output = stdout_output
            if stderr_output:
                output += stderr_output
            
            return CodeExecutionResponse(
                success=True,
                output=output
            )
            
        except Exception as e:
            # Capture the exception with traceback
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)}\n"
            error_msg += traceback.format_exc()
            
            return CodeExecutionResponse(
                success=False,
                error=error_msg
            )
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")